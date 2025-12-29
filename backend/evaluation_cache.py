import json
import hashlib
from pathlib import Path
from threading import Lock
from datetime import datetime
from typing import Any, Dict, Optional


class EvaluationCache:
    """
    持久化存储逐日评估记录，避免随着新行情或重复训练导致历史结果漂移。
    通过参数集合生成的 cache_key + forecast_date 两级索引来读取/写入。
    """

    def __init__(self, cache_path: str = "logs/evaluation_cache.json") -> None:
        # Anchor to the backend directory so cache location is stable regardless of cwd
        base_dir = Path(__file__).resolve().parent
        configured_path = Path(cache_path)
        self.path = (
            configured_path
            if configured_path.is_absolute()
            else base_dir / configured_path
        )
        self.path.parent.mkdir(parents=True, exist_ok=True)
        # Daily archive: keep each day's newly written evaluation records in an independent file.
        # This helps auditing and prevents "today's run" from being mixed with other days.
        self.daily_dir = self.path.parent / "evaluation_cache_daily"
        self.daily_dir.mkdir(parents=True, exist_ok=True)
        self.lock = Lock()
        self.data: Dict[str, Any] = self._load()

    def _load(self) -> Dict[str, Dict[str, Any]]:
        if not self.path.exists():
            return {}
        try:
            with open(self.path, "r", encoding="utf-8") as f:
                payload = json.load(f)
                if isinstance(payload, dict):
                    return payload
        except Exception:
            # 遇到损坏文件则丢弃，避免阻塞预测流程
            return {}
        return {}

    def _persist(self) -> None:
        now = datetime.now()
        meta = self.data.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
            self.data["_meta"] = meta
        meta.update(
            {
                "updated_at": now.isoformat(),
                "updated_date": now.strftime("%Y-%m-%d"),
                "version": 1,
            }
        )
        tmp = self.path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
        tmp.replace(self.path)

    def _persist_daily(self, cache_key: str, records: Dict[str, Dict[str, Any]]) -> None:
        """Append today's newly computed records into a per-day archive file."""
        if not records:
            return
        today = datetime.now().strftime("%Y-%m-%d")
        daily_path = self.daily_dir / f"evaluation_cache_{today}.json"

        payload: Dict[str, Any] = {}
        if daily_path.exists():
            try:
                with open(daily_path, "r", encoding="utf-8") as f:
                    loaded = json.load(f)
                    if isinstance(loaded, dict):
                        payload = loaded
            except Exception:
                payload = {}

        meta = payload.get("_meta")
        if not isinstance(meta, dict):
            meta = {}
            payload["_meta"] = meta
        meta.update(
            {
                "date": today,
                "updated_at": datetime.now().isoformat(),
                "version": 1,
            }
        )

        bucket = payload.setdefault(cache_key, {})
        if not isinstance(bucket, dict):
            bucket = {}
            payload[cache_key] = bucket
        bucket.update(records)

        tmp = daily_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
        tmp.replace(daily_path)

    def make_key(self, params: Dict[str, Any]) -> str:
        """
        生成评估缓存键，使用参数字典的哈希前16位。
        不要包含 end_date，让新行情加入时仍可复用历史评估。
        """
        param_str = json.dumps(params, sort_keys=True, ensure_ascii=False)
        return hashlib.sha256(param_str.encode()).hexdigest()[:16]

    def get(self, cache_key: str, forecast_date: str) -> Optional[Dict[str, Any]]:
        """
        读取单日评估记录。
        forecast_date 使用 YYYY-MM-DD 字符串。
        """
        with self.lock:
            bucket = self.data.get(cache_key, {})
            record = bucket.get(forecast_date)
            return record

    def set_many(self, cache_key: str, records: Dict[str, Dict[str, Any]]) -> None:
        """批量写入多天评估记录后一次持久化，减少磁盘写入次数。"""
        if not records:
            return
        with self.lock:
            bucket = self.data.setdefault(cache_key, {})
            bucket.update(records)
            self._persist()
            # Also archive today's delta into an independent daily file.
            self._persist_daily(cache_key, records)

    def clear(self) -> None:
        with self.lock:
            self.data = {}
            if self.path.exists():
                self.path.unlink()
