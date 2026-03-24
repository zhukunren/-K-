# Shared prediction pipeline utilities.
from typing import List, Optional, Dict, Any
import numpy as np
import pandas as pd
import torch
import torch.nn.functional as F
from fastapi import HTTPException
from sklearn.preprocessing import StandardScaler

from evaluation_cache import EvaluationCache
from function import read_day_from_tushare
from preprocess import preprocess_data
from main import (
    train_autoencoder_get_embeddings,
    train_autoencoder_get_embeddings_with_cache,
    topk_similar_to_last,
    analog_forecast,
    analog_forecast_ohlc,
    get_close_series,
    create_sequences,
    zscore_windows,
)

DEVICE = "cpu"  # 强制使用 CPU 避免 GPU 兼容性问题

INDEX_CODES = {
    "000001.SH",
    "000016.SH",
    "000300.SH",
    "000905.SH",
    "399001.SZ",
    "399006.SZ",
    "399005.SZ",
}


def determine_symbol_type(symbol: str) -> str:
    symbol = symbol.upper()
    if symbol in INDEX_CODES:
        return "index"
    if symbol.startswith("399") and symbol.endswith(".SZ"):
        return "index"
    if symbol.startswith("000") and symbol.endswith(".SH"):
        return "index"
    return "stock"


# 逐日评估缓存实例（持久化到 logs/evaluation_cache.json）
EVAL_CACHE = EvaluationCache()


def _build_eval_cache_key(request, feature_cols: List[str], overrides: Optional[dict] = None) -> str:
    """
    构造用于逐日评估的缓存键，不包含 end_date，
    这样在增加新行情时仍能复用历史评估结果。
    overrides 用于传入已规范化的参数（如实际使用的 min_gap_days），避免因为不同默认值导致缓存分叉。
    """
    overrides = overrides or {}

    def _val(name: str, default=None):
        return overrides.get(name, getattr(request, name, default))

    params = {
        "symbol": _val("symbol", ""),
        "start_date": _val("start_date", ""),
        "engine": _val("engine", "ml"),
        "model_type": _val("model_type", "transformer"),
        "window": _val("window", 0),
        "stride": _val("stride", 1),
        "h_future": _val("h_future", 1),
        "topk": _val("topk", 0),
        "re_rank_top": _val("re_rank_top", 30),
        "agg": _val("agg", "median"),
        "sim_method": _val("sim_method", "hybrid"),
        "use_corr": _val("use_corr", True),
        "use_dtw": _val("use_dtw", True),
        "alpha_cos": _val("alpha_cos", 0.5),
        "beta_corr": _val("beta_corr", 0.3),
        "gamma_dtw": _val("gamma_dtw", 0.2),
        "min_gap_days": _val("min_gap_days", 30),
        "dedup_radius": _val("dedup_radius", 5),
        "prefilter": _val("prefilter", True),
        "prefilter_tolerance": _val("prefilter_tolerance", 0.6),
        "prefilter_multiplier": _val("prefilter_multiplier", 5),
        "use_window_zscore": _val("use_window_zscore", True),
        "strictness": float(_val("strictness", 0.0)),
        "selected_features": sorted(_val("selected_features", []) or []),
        "feature_cols": sorted(feature_cols),
        "evaluation_start_date": _val("evaluation_start_date", None),
    }
    return EVAL_CACHE.make_key(params)


def _apply_return_bias(pred_return: float) -> float:
    """调整预测收益：上涨加0.45%，下跌减0.45%，持平不变。"""
    if pred_return > 0:
        return pred_return + 0.0045
    if pred_return < 0:
        return pred_return - 0.0045
    return pred_return


def _apply_bias_to_path(closes: List[float], last_known_close: float) -> List[float]:
    """对一条预测收盘路径应用涨跌偏移，基于上一收盘递推。"""
    adjusted: List[float] = []
    prev = float(last_known_close)
    for close_val in closes:
        close_f = float(close_val)
        if prev == 0:
            adjusted.append(close_f)
            prev = close_f
            continue
        ret = (close_f - prev) / prev
        ret = _apply_return_bias(ret)
        new_close = prev * (1.0 + ret)
        adjusted.append(float(new_close))
        prev = new_close
    return adjusted


def _apply_bias_to_ohlc(
    opens: List[float],
    highs: List[float],
    lows: List[float],
    closes: List[float],
    last_known_close: float,
) -> tuple:
    """按收盘涨跌偏移调整一条 OHLC 预测路径，其余价位按同一倍率缩放。"""
    adj_o, adj_h, adj_l, adj_c = [], [], [], []
    prev = float(last_known_close)
    for o, h, l, c in zip(opens, highs, lows, closes):
        c_f = float(c)
        if prev == 0:
            multiplier = 1.0
            new_close = c_f
        else:
            ret = (c_f - prev) / prev
            ret = _apply_return_bias(ret)
            new_close = prev * (1.0 + ret)
            if c_f != 0:
                multiplier = new_close / c_f
            else:
                multiplier = 1.0
        adj_c.append(float(new_close))
        adj_o.append(float(o) * multiplier)
        adj_h.append(float(h) * multiplier)
        adj_l.append(float(l) * multiplier)
        prev = new_close
    return adj_o, adj_h, adj_l, adj_c


def _apply_bias_to_eval_record(record: Dict[str, Any]) -> Dict[str, Any]:
    """对逐日评估记录应用涨跌偏移，避免旧缓存未偏移导致前端不一致。"""
    if record.get("_bias_applied"):
        return record
    rec = dict(record)
    base_close = float(rec.get("base_close", 0.0))
    predicted_return = float(rec.get("predicted_return", 0.0))
    actual_return = float(rec.get("actual_return", 0.0))
    biased_return = _apply_return_bias(predicted_return)
    rec["predicted_return"] = biased_return
    if base_close:
        rec["predicted_close"] = base_close * (1.0 + biased_return)
    rec["error"] = biased_return - actual_return
    rec["_bias_applied"] = True
    return rec


def _is_finite_number(value: Any) -> bool:
    try:
        return isinstance(value, (int, float)) and np.isfinite(float(value))
    except Exception:
        return False


def _merge_cached_eval_record(
    cached: Dict[str, Any],
    forecast_date_str: str,
    base_close: float,
    actual_close: float,
    match_count: Optional[int] = None,
) -> tuple:
    """
    Merge cached evaluation record with fresh actuals while keeping cached prediction frozen.
    Returns (record, cache_updated, usable).
    """
    record = dict(cached) if isinstance(cached, dict) else {}
    cache_updated = False

    if record.get("date") is None:
        record["date"] = forecast_date_str
        cache_updated = True

    if not _is_finite_number(record.get("base_close")) and _is_finite_number(base_close):
        record["base_close"] = float(base_close)
        cache_updated = True

    if not _is_finite_number(record.get("predicted_return")):
        pred_close = record.get("predicted_close")
        if _is_finite_number(pred_close) and _is_finite_number(record.get("base_close")) and record["base_close"] != 0:
            record["predicted_return"] = (float(pred_close) - float(record["base_close"])) / float(record["base_close"])
            cache_updated = True

    if not _is_finite_number(record.get("predicted_close")):
        if _is_finite_number(record.get("predicted_return")) and _is_finite_number(record.get("base_close")):
            record["predicted_close"] = float(record["base_close"]) * (1.0 + float(record["predicted_return"]))
            cache_updated = True

    if _is_finite_number(actual_close) and _is_finite_number(record.get("base_close")) and record["base_close"] != 0:
        actual_return = (float(actual_close) - float(record["base_close"])) / float(record["base_close"])
        if not _is_finite_number(record.get("actual_close")):
            record["actual_close"] = float(actual_close)
            cache_updated = True
        if not _is_finite_number(record.get("actual_return")):
            record["actual_return"] = float(actual_return)
            cache_updated = True

    if _is_finite_number(record.get("predicted_return")) and _is_finite_number(record.get("actual_return")):
        if not _is_finite_number(record.get("error")):
            record["error"] = float(record["predicted_return"]) - float(record["actual_return"])
            cache_updated = True

    if match_count is not None and not _is_finite_number(record.get("match_count")):
        record["match_count"] = int(match_count)
        cache_updated = True

    if record.get("_from_forecast") and not record.get("_bias_applied"):
        record["_bias_applied"] = True
        cache_updated = True

    if not _is_finite_number(record.get("predicted_return")) and not record.get("_bias_applied"):
        return record, cache_updated, False

    before_bias = bool(record.get("_bias_applied"))
    record = _apply_bias_to_eval_record(record)
    if not before_bias and record.get("_bias_applied"):
        cache_updated = True

    if not _is_finite_number(record.get("predicted_return")):
        return record, cache_updated, False

    return record, cache_updated, True


def _cache_forecast_eval_record(
    eval_cache: EvaluationCache,
    eval_cache_key: str,
    forecast_date_str: str,
    base_close: float,
    predicted_close: float,
    match_count: Optional[int] = None,
) -> None:
    if not forecast_date_str or not _is_finite_number(base_close) or base_close == 0:
        return
    if not _is_finite_number(predicted_close):
        return
    existing = eval_cache.get(eval_cache_key, forecast_date_str)
    if existing:
        return
    predicted_return = (float(predicted_close) - float(base_close)) / float(base_close)
    record = {
        "date": forecast_date_str,
        "base_close": float(base_close),
        "predicted_close": float(predicted_close),
        "predicted_return": float(predicted_return),
        "actual_close": None,
        "actual_return": None,
        "error": None,
        "match_count": int(match_count) if match_count is not None else None,
        "_bias_applied": True,
        "_from_forecast": True,
    }
    eval_cache.set_many(eval_cache_key, {forecast_date_str: record})


def _compute_window_signatures(close_array: np.ndarray, volume_array: Optional[np.ndarray], window: int, stride: int) -> np.ndarray:
    total = len(close_array)
    if total < window:
        return np.empty((0, 4), dtype=np.float32)

    steps = (total - window) // stride + 1
    signatures = np.zeros((steps, 4), dtype=np.float32)
    volume_array = volume_array if volume_array is not None and len(volume_array) == total else None
    global_mean_volume = float(np.mean(volume_array)) if volume_array is not None and np.any(volume_array) else 1.0

    for idx in range(steps):
        start = idx * stride
        segment = close_array[start:start + window]
        if len(segment) < window:
            break
        first = segment[0]
        last = segment[-1]
        pct_return = float((last - first) / (abs(first) + 1e-9))
        diff = np.diff(segment)
        volatility = float(np.std(diff) / (abs(np.mean(segment)) + 1e-9))
        reference = segment[max(0, len(segment) - 3)]
        momentum = float((last - reference) / (abs(reference) + 1e-9)) if len(segment) >= 3 else 0.0

        if volume_array is not None:
            vol_segment = volume_array[start:start + window]
            split = max(1, window // 2)
            head = np.mean(vol_segment[:split]) + 1e-9
            tail = np.mean(vol_segment[-split:]) + 1e-9
            volume_ratio = float((tail / head) * (head / (global_mean_volume + 1e-9)))
        else:
            volume_ratio = 1.0

        signatures[idx] = [pct_return, volatility, momentum, volume_ratio]

    return signatures


def _prefilter_candidate_indices(signatures: np.ndarray, tolerance: float, max_candidates: int) -> List[int]:
    if signatures.size == 0:
        return []

    last = signatures[-1]
    denom = np.abs(last) + 1e-6
    diffs = np.abs(signatures[:-1] - last) / denom
    scores = diffs.mean(axis=1)
    order = np.argsort(scores)
    selected: List[int] = []
    for idx in order:
        if scores[idx] <= tolerance or not selected:
            selected.append(int(idx))
        if len(selected) >= max_candidates:
            break
    if not selected:
        selected = order[:max_candidates].astype(int).tolist()
    return selected



def _prefilter_for_target(signatures: np.ndarray, target_idx: int, tolerance: float, max_candidates: int) -> List[int]:
    if signatures.size == 0 or target_idx <= 0:
        return []
    last = signatures[target_idx]
    prev = signatures[:target_idx]
    denom = np.abs(last) + 1e-6
    diffs = np.abs(prev - last) / denom
    scores = diffs.mean(axis=1)
    order = np.argsort(scores)
    selected: List[int] = []
    for idx in order:
        if scores[idx] <= tolerance or not selected:
            selected.append(int(idx))
        if len(selected) >= max_candidates:
            break
    if not selected:
        selected = order[:max_candidates].astype(int).tolist()
    return selected


def _topk_similar_to_index(
    Z: torch.Tensor,
    target_idx: int,
    dates_seq_end: pd.Series,
    df_index: pd.Index,
    window: int,
    stride: int,
    k: int,
    min_gap_days: int,
    dedup_radius: int,
    candidate_indices: Optional[List[int]] = None,
) -> List[tuple]:
    target = Z[target_idx:target_idx + 1]
    sims = F.cosine_similarity(target, Z).squeeze()

    mask = torch.ones_like(sims, dtype=torch.bool)
    mask[target_idx:] = False

    if min_gap_days > 0:
        target_end = pd.to_datetime(dates_seq_end[target_idx])
        for idx in range(target_idx):
            if mask[idx]:
                delta_days = (target_end - pd.to_datetime(dates_seq_end[idx])).days
                if delta_days < min_gap_days:
                    mask[idx] = False

    if candidate_indices is not None:
        candidate_mask = torch.zeros_like(mask)
        for cid in candidate_indices:
            if 0 <= cid < target_idx:
                candidate_mask[cid] = True
        if candidate_mask.any():
            mask &= candidate_mask
        else:
            mask &= mask

    sims_masked = sims.masked_fill(~mask, float('-inf'))
    if k <= 0 or target_idx == 0:
        return []

    prelim_count = max(1, min(k * 5, target_idx))
    prelim = torch.topk(sims_masked, k=prelim_count)
    cand_idx = prelim.indices.cpu().numpy().tolist()
    cand_sim = prelim.values.cpu().numpy().tolist()

    target_start = target_idx * stride
    target_end_pos = target_start + window - 1
    picked: List[int] = []
    picked_sims: List[float] = []
    picked_ranges: List[tuple] = []

    def has_overlap(start1: int, end1: int, ranges: List[tuple]) -> bool:
        for start2, end2 in ranges:
            if start1 <= end2 and start2 <= end1:
                return True
        return False

    for idx, sim_val in zip(cand_idx, cand_sim):
        if idx >= target_idx or sim_val == float('-inf'):
            continue
        start_pos = idx * stride
        end_pos = start_pos + window - 1
        if end_pos >= target_start:
            continue
        if has_overlap(start_pos, end_pos, picked_ranges):
            continue
        picked.append(int(idx))
        picked_sims.append(float(sim_val))
        picked_ranges.append((start_pos, end_pos))
        if len(picked) >= k:
            break

    results: List[tuple] = []
    for idx, sim_val in zip(picked, picked_sims):
        start_pos = idx * stride
        end_pos = start_pos + window - 1
        date_start = pd.to_datetime(df_index[start_pos])
        date_end = pd.to_datetime(df_index[end_pos])
        date_end_label = pd.to_datetime(dates_seq_end[idx])
        results.append((int(idx), date_start, date_end, date_end_label, float(sim_val)))
    return results


def _aggregate_ratio(values: List[float], agg: str) -> float:
    arr = np.asarray(values, dtype=float)
    if arr.size == 0:
        return float('nan')
    if agg == "median":
        return float(np.median(arr))
    if agg == "mean":
        return float(np.mean(arr))
    if agg == "max":
        return float(np.max(arr))
    if agg == "min":
        return float(np.min(arr))
    raise ValueError("Unsupported agg method")


def _direction_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float:
    mask = ~np.isnan(actual) & ~np.isnan(predicted)
    if not mask.any():
        return float('nan')
    actual_sign = np.sign(actual[mask])
    pred_sign = np.sign(predicted[mask])
    return float(np.mean(actual_sign == pred_sign))


def _to_float_list(array: np.ndarray) -> List[float]:
    arr = array
    if hasattr(arr, "tolist"):
        try:
            return [float(x) for x in arr.tolist()]
        except Exception:
            pass
    return [float(x) for x in arr]


def _zscore(series: np.ndarray) -> np.ndarray:
    s = np.asarray(series, dtype=float)
    m = np.mean(s)
    std = np.std(s)
    if std < 1e-9:
        return np.zeros_like(s)
    return (s - m) / std


def _corr_sim(a: np.ndarray, b: np.ndarray) -> float:
    if len(a) != len(b) or len(a) == 0:
        return 0.0
    az = _zscore(a)
    bz = _zscore(b)
    c = np.corrcoef(az, bz)[0, 1]
    if np.isnan(c):
        return 0.0
    # map [-1,1] -> [0,1]
    return float((c + 1.0) / 2.0)


def _dtw_distance(a: np.ndarray, b: np.ndarray) -> float:
    """Simple DTW distance for short sequences."""
    n = len(a)
    m = len(b)
    if n == 0 or m == 0:
        return float("inf")
    A = _zscore(a)
    B = _zscore(b)
    dp = np.full((n + 1, m + 1), np.inf, dtype=float)
    dp[0, 0] = 0.0
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            cost = abs(A[i - 1] - B[j - 1])
            dp[i, j] = cost + min(dp[i - 1, j], dp[i, j - 1], dp[i - 1, j - 1])
    return float(dp[n, m] / (n + m))


def _dtw_sim(a: np.ndarray, b: np.ndarray) -> float:
    d = _dtw_distance(a, b)
    return float(1.0 / (1.0 + d))





def _run_daily_evaluation(
    request,
    embeddings: torch.Tensor,
    dates_seq_end: pd.Series,
    df: pd.DataFrame,
    window_sequences: np.ndarray,
    signatures: np.ndarray,
    close_np: np.ndarray,
    stride: int,
    min_gap_days: int,
    dedup_radius: int,
    prefilter_enabled: bool,
    prefilter_tolerance: float,
    prefilter_multiplier: int,
    re_rank_top: int,
    use_corr: bool,
    use_dtw: bool,
    a_cos: float,
    b_corr: float,
    g_dtw: float,
    sim_method: str,
    eval_cache: Optional[EvaluationCache] = None,
    eval_cache_key: Optional[str] = None,
    freeze_eval_history: bool = True,
    force_eval_refresh: bool = False,
) -> Optional[dict]:
    eval_start_str = getattr(request, "evaluation_start_date", "20220101") or "20220101"
    try:
        eval_start_date = pd.to_datetime(eval_start_str)
    except Exception:
        eval_start_date = pd.to_datetime("20220101")
    eval_h_future = 1
    total_windows = len(window_sequences)
    if total_windows == 0:
        return None

    embeddings = embeddings.detach().cpu().float()
    max_candidates = max(request.topk * max(prefilter_multiplier, 1), max(request.topk, 1))
    records = []
    new_cache_records: dict = {}

    for target_idx in range(total_windows):
        base_end_pos = target_idx * stride + request.window - 1
        next_pos = base_end_pos + eval_h_future
        if next_pos >= len(close_np):
            continue
        forecast_date = pd.to_datetime(df.index[next_pos])
        if forecast_date < eval_start_date:
            continue
        if forecast_date > pd.to_datetime(getattr(request, "end_date", forecast_date.strftime("%Y%m%d"))):
            continue
        forecast_date_str = forecast_date.strftime("%Y-%m-%d")

        if (
            eval_cache is not None
            and eval_cache_key
            and freeze_eval_history
            and not force_eval_refresh
        ):
            cached = eval_cache.get(eval_cache_key, forecast_date_str)
            if cached:
                base_close_val = float(close_np[base_end_pos])
                actual_close_val = float(close_np[next_pos])
                merged, cache_updated, usable = _merge_cached_eval_record(
                    cached,
                    forecast_date_str,
                    base_close_val,
                    actual_close_val,
                )
                if usable:
                    records.append(merged)
                    if cache_updated:
                        new_cache_records[forecast_date_str] = merged
                    continue

        candidate_indices = None
        if prefilter_enabled:
            candidate_indices = _prefilter_for_target(signatures, target_idx, prefilter_tolerance, max_candidates)

        initial_matches = _topk_similar_to_index(
            embeddings,
            target_idx,
            dates_seq_end,
            df.index,
            request.window,
            stride,
            re_rank_top,
            min_gap_days,
            dedup_radius,
            candidate_indices=candidate_indices,
        )
        if not initial_matches:
            continue

        ranked: List[tuple] = []
        target_start_pos = target_idx * stride
        target_end_pos = target_start_pos + request.window - 1
        base_close_series = close_np[target_start_pos:target_end_pos + 1]
        base_close = float(base_close_series[-1]) if len(base_close_series) else float('nan')
        base_vol = float(np.std(np.diff(base_close_series))) if len(base_close_series) > 1 else 0.0
        base_ret = float((base_close_series[-1] - base_close_series[0]) / (abs(base_close_series[0]) + 1e-9)) if len(base_close_series) >= 2 else 0.0

        for (match_idx, start_date, end_date, anchor_date, sim_cos) in initial_matches:
            start_pos = match_idx * stride
            end_pos = start_pos + request.window - 1
            cand_close = close_np[start_pos:end_pos + 1]
            if len(cand_close) != len(base_close_series):
                continue
            cand_ret = float((cand_close[-1] - cand_close[0]) / (abs(cand_close[0]) + 1e-9)) if len(cand_close) >= 2 else 0.0
            if base_ret * cand_ret < 0:
                continue
            cand_vol = float(np.std(np.diff(cand_close))) if len(cand_close) > 1 else 0.0
            vol_ok = (base_vol == 0 and cand_vol == 0) or (0.8 <= (cand_vol / (base_vol + 1e-9)) <= 1.2)
            if not vol_ok:
                continue

            sim_corr = _corr_sim(base_close_series, cand_close) if use_corr else 0.0
            sim_dtw = _dtw_sim(base_close_series, cand_close) if use_dtw else 0.0
            sim_cos_n = float((sim_cos + 1.0) / 2.0)
            final_score = a_cos * sim_cos_n + b_corr * sim_corr + g_dtw * sim_dtw
            ranked.append((final_score, match_idx, start_date, end_date, anchor_date, float(sim_cos), sim_corr, sim_dtw))

        if not ranked:
            continue
        ranked.sort(key=lambda x: x[0], reverse=True)
        top_matches = ranked[:max(1, request.topk)]

        ratios = []
        match_counts = 0
        for _, match_idx, *_rest in top_matches:
            match_start = match_idx * stride
            match_end = match_start + request.window - 1
            match_next = match_end + eval_h_future
            if match_next >= len(close_np):
                continue
            base_match_close = close_np[match_end]
            if base_match_close == 0:
                continue
            next_match_close = close_np[match_next]
            ratios.append(next_match_close / base_match_close)
            match_counts += 1

        if not ratios:
            continue
        pred_ratio = _aggregate_ratio(ratios, request.agg)
        if np.isnan(pred_ratio):
            continue

        actual_close = float(close_np[next_pos])
        base_close = float(close_np[target_end_pos])
        if base_close == 0:
            continue

        predicted_close = base_close * pred_ratio
        actual_return = (actual_close - base_close) / base_close
        predicted_return = (predicted_close - base_close) / base_close
        predicted_return = _apply_return_bias(predicted_return)
        predicted_close = base_close * (1.0 + predicted_return)
        error = predicted_return - actual_return

        record = {
            "date": forecast_date.strftime("%Y-%m-%d"),
            "base_close": float(base_close),
            "predicted_close": float(predicted_close),
            "actual_close": float(actual_close),
            "predicted_return": float(predicted_return),
            "actual_return": float(actual_return),
            "error": float(error),
            "match_count": match_counts,
            "_bias_applied": True,
        }

        records.append(record)
        if eval_cache is not None and eval_cache_key and freeze_eval_history:
            new_cache_records[forecast_date_str] = record

    if not records:
        return {
            "summary": {
                "count": 0,
                "direction_accuracy": None,
                "mae": None,
                "rmse": None,
                "mean_actual": None,
                "mean_predicted": None,
            },
            "records": [],
            "horizon": 1,
        }

    pred_returns = np.array([r["predicted_return"] for r in records], dtype=float)
    actual_returns = np.array([r["actual_return"] for r in records], dtype=float)
    errors = pred_returns - actual_returns

    summary = {
        "count": int(len(records)),
        "direction_accuracy": _direction_accuracy(actual_returns, pred_returns),
        "mae": float(np.mean(np.abs(errors))),
        "rmse": float(np.sqrt(np.mean(errors ** 2))),
        "mean_actual": float(np.mean(actual_returns)),
        "mean_predicted": float(np.mean(pred_returns)),
    }

    if eval_cache is not None and eval_cache_key and freeze_eval_history and new_cache_records:
        eval_cache.set_many(eval_cache_key, new_cache_records)

    return {
        "summary": summary,
        "records": records,
        "horizon": 1,
        "start_date": eval_start_date.strftime("%Y-%m-%d"),
    }


def run_transformer_pipeline(request) -> dict:
    if request.use_fixed_seed:
        torch.manual_seed(request.random_seed)
        np.random.seed(request.random_seed)

    symbol_type = determine_symbol_type(request.symbol)

    engine = (getattr(request, "engine", "ml") or "ml").lower()
    if engine not in {"ml", "classic"}:
        raise HTTPException(status_code=400, detail=f"Unsupported engine mode: {engine}")

    allowed_model_types = {"transformer", "lstm", "gru", "cnn_transformer", "transformer_lstm", "transformer_gru"}
    model_type = (getattr(request, "model_type", "transformer") or "transformer").lower()
    if engine == "ml" and model_type not in allowed_model_types:
        raise HTTPException(status_code=400, detail=f"Unsupported model type: {model_type}")
    model_kwargs = {}

    try:
        df_raw = read_day_from_tushare(
            symbol_code=request.symbol,
            symbol_type=symbol_type,
            start_date=request.start_date,
            end_date=request.end_date,
        )
    except Exception as exc:
        raise HTTPException(status_code=502, detail=f"获取数据失败: {exc}") from exc

    if df_raw is None or df_raw.empty:
        raise HTTPException(status_code=400, detail="未获取到可用的行情数据，请检查代码或时间范围")

    df_reset = df_raw.reset_index().copy()
    if "trade_date" not in df_reset.columns:
        df_reset.rename(columns={df_reset.columns[0]: "trade_date"}, inplace=True)
    df_reset["trade_date"] = pd.to_datetime(df_reset["trade_date"]).dt.strftime("%Y%m%d")

    selected_features = request.selected_features or None
    # 将用户选择的特征名转为小写,因为preprocess_data会统一转换为小写
    if selected_features:
        selected_features = [f.lower() for f in selected_features]
    processed, feature_cols = preprocess_data(
        df_reset,
        N=max(request.window, 1),
        mixture_depth=1,
        mark_labels=False,
        selected_features=selected_features,
    )
    processed = processed.sort_index()

    feature_cols = [col for col in feature_cols if col in processed.columns]
    if not feature_cols:
        raise HTTPException(status_code=400, detail="No usable features after preprocessing")

    features_df = processed[feature_cols].apply(pd.to_numeric, errors="coerce").fillna(0.0)
    if len(features_df) < request.window + 1:
        raise HTTPException(status_code=400, detail="Insufficient samples for the configured window size")

    stride = max(1, getattr(request, "stride", 1))
    close_series = get_close_series(processed)
    volume_array = None
    if 'volume' in processed.columns:
        volume_array = processed['volume'].to_numpy(dtype=float, copy=False)

    scaler = StandardScaler()
    features_mat = scaler.fit_transform(features_df.values).astype(np.float32)

    if engine == "classic":
        window_sequences = create_sequences(features_mat.astype(np.float32), window=request.window, stride=stride)
        if len(window_sequences) == 0:
            raise HTTPException(status_code=400, detail="Insufficient window sequences for classic engine")
        if getattr(request, "use_window_zscore", True):
            window_sequences = zscore_windows(window_sequences)
        embeddings_np = window_sequences.reshape(window_sequences.shape[0], -1)
        embeddings = torch.from_numpy(embeddings_np).to(torch.float32)
        dates_seq_end = pd.to_datetime(processed.index[request.window - 1::stride])
    else:
        try:
            # 准备缓存参数
            cache_params = {
                'symbol': request.symbol,
                'start_date': request.start_date,
                'end_date': request.end_date,
                'selected_features': sorted(getattr(request, 'selected_features', []) or []),
                'engine': engine,
            }

            # 使用带缓存的训练函数
            use_cache = getattr(request, 'use_cache', True)  # 默认启用缓存

            # 尝试使用带缓存的版本
            try:
                _, embeddings, dates_seq_end, window_sequences = train_autoencoder_get_embeddings_with_cache(
                    features_mat,
                    processed.index,
                    window=request.window,
                    stride=stride,
                    d_model=64,
                    nhead=4,
                    num_layers=2,
                    epochs=request.epochs,
                    lr=1e-3,
                    use_window_zscore=getattr(request, "use_window_zscore", True),
                    device=DEVICE,
                    model_type=model_type,
                    model_kwargs=model_kwargs,
                    cache_params=cache_params,
                    use_cache=use_cache
                )
            except (ImportError, NameError):
                # 如果缓存版本不可用，回退到原始版本
                _, embeddings, dates_seq_end, window_sequences = train_autoencoder_get_embeddings(
                    features_mat,
                    processed.index,
                    window=request.window,
                    stride=stride,
                    d_model=64,
                    nhead=4,
                    num_layers=2,
                    epochs=request.epochs,
                    lr=1e-3,
                    use_window_zscore=getattr(request, "use_window_zscore", True),
                    device=DEVICE,
                    model_type=model_type,
                    model_kwargs=model_kwargs,
                )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # 屏蔽最近30个交易日内的相似检索（最小为30），默认使用 window*2 以与前端一致
    raw_min_gap = getattr(request, "min_gap_days", None)
    provided_fields = getattr(request, "model_fields_set", set())
    if raw_min_gap is None or ("min_gap_days" not in provided_fields):
        raw_min_gap = max(int(getattr(request, "window", 0)) * 2, 5)
    min_gap_days = max(30, int(raw_min_gap))
    dedup_radius = max(1, getattr(request, "dedup_radius", 5))

    prefilter_enabled = getattr(request, "prefilter", True)
    prefilter_multiplier = max(2, getattr(request, "prefilter_multiplier", 5))
    prefilter_tolerance = max(0.0, float(getattr(request, "prefilter_tolerance", 0.6)))
    max_candidates = max(request.topk * prefilter_multiplier, max(request.topk, 1))

    close_array = close_series.to_numpy(dtype=float, copy=False)
    signatures = _compute_window_signatures(close_array, volume_array, request.window, stride)
    candidate_indices = None
    if prefilter_enabled and signatures.shape[0] > 1:
        candidate_indices = _prefilter_candidate_indices(signatures, prefilter_tolerance, max_candidates)
        if not candidate_indices:
            candidate_indices = None

    # First retrieve a larger candidate pool for re-ranking
    re_rank_top = max(int(getattr(request, "re_rank_top", 30)), request.topk)
    initial_matches = topk_similar_to_last(
        embeddings,
        dates_seq_end,
        processed.index,
        window=request.window,
        stride=stride,
        k=re_rank_top,
        min_gap_days=min_gap_days,
        dedup_radius=dedup_radius,
        candidate_indices=candidate_indices,
    )
    if not initial_matches:
        # 不抛错：允许无相似窗口，后续仅返回历史数据
        initial_matches = []

    # Build baseline window close
    index_list = list(processed.index)
    last_window_idx = len(window_sequences) - 1
    baseline_start = last_window_idx * stride
    baseline_end = baseline_start + request.window - 1
    close_np = pd.to_numeric(get_close_series(processed), errors="coerce").to_numpy(dtype=float)
    base_close = close_np[baseline_start:baseline_end + 1]

    # Structure metrics: volatility and window return
    def window_volatility(seg: np.ndarray) -> float:
        if len(seg) < 2:
            return 0.0
        return float(np.std(np.diff(seg)))

    base_vol = window_volatility(base_close)
    base_ret = float((base_close[-1] - base_close[0]) / (abs(base_close[0]) + 1e-9)) if len(base_close) >= 2 else 0.0

    # Apply sim_method overrides
    sim_method = getattr(request, 'sim_method', 'hybrid')
    use_corr = bool(getattr(request, "use_corr", True))
    use_dtw = bool(getattr(request, "use_dtw", True))
    a_cos = float(getattr(request, "alpha_cos", 0.5))
    b_corr = float(getattr(request, "beta_corr", 0.3))
    g_dtw = float(getattr(request, "gamma_dtw", 0.2))

    if sim_method == 'corr_only':
        use_corr = True
        use_dtw = False
        a_cos, b_corr, g_dtw = 0.0, 1.0, 0.0
    elif sim_method == 'dtw_only':
        use_corr = False
        use_dtw = True
        a_cos, b_corr, g_dtw = 0.0, 0.0, 1.0
    elif sim_method == 'mp_hybrid':
        # keep hybrid but expand candidate pool to mimic MP召回
        re_rank_top = max(int(getattr(request, 're_rank_top', 30)), 50)
        prefilter_multiplier = max(prefilter_multiplier, 10)

    strictness = float(getattr(request, "strictness", 0.0))

    if not use_corr:
        b_corr = 0.0
    if not use_dtw:
        g_dtw = 0.0

    weights = [max(0.0, a_cos), max(0.0, b_corr), max(0.0, g_dtw)]
    weight_sum = sum(weights)
    if weight_sum <= 1e-8:
        # fallback to默认比重避免权重无效
        weights = [0.5, 0.3, 0.2]
        weight_sum = sum(weights)
    a_cos, b_corr, g_dtw = [w / weight_sum for w in weights]

    ranked = []
    for (match_idx, start_date, end_date, anchor_date, sim_cos) in initial_matches:
        start_pos = match_idx * stride
        end_pos = start_pos + request.window - 1
        cand_close = close_np[start_pos:end_pos + 1]
        if len(cand_close) != len(base_close):
            continue
        # Structure filters
        cand_ret = float((cand_close[-1] - cand_close[0]) / (abs(cand_close[0]) + 1e-9)) if len(cand_close) >= 2 else 0.0
        if base_ret * cand_ret < 0:
            continue
        cand_vol = window_volatility(cand_close)
        vol_ok = (base_vol == 0 and cand_vol == 0) or (0.8 <= (cand_vol / (base_vol + 1e-9)) <= 1.2)
        if not vol_ok:
            continue

        sim_corr = _corr_sim(base_close, cand_close) if use_corr else 0.0
        sim_dtw = _dtw_sim(base_close, cand_close) if use_dtw else 0.0
        sim_cos_n = float((sim_cos + 1.0) / 2.0)
        final_score = a_cos * sim_cos_n + b_corr * sim_corr + g_dtw * sim_dtw
        if final_score < strictness:
            continue
        ranked.append((final_score, match_idx, start_date, end_date, anchor_date, float(sim_cos), sim_corr, sim_dtw))

    if not ranked:
        ranked = [(float((s + 1.0) / 2.0), mi, sd, ed, ad, float(s), 0.0, 0.0) for (mi, sd, ed, ad, s) in initial_matches]

    ranked.sort(key=lambda x: x[0], reverse=True)
    matches = [(mi, sd, ed, ad, sc) for (fs, mi, sd, ed, ad, sc, crr, dtw) in ranked[:request.topk]] if ranked else []

    last_known_close = float(processed["close"].iloc[-1]) if "close" in processed.columns else None
    mean_path, q25_path, q75_path, close_paths = [], [], [], []
    if matches:
        try:
            mean_path, q25_path, q75_path, close_paths = analog_forecast(
                close_series,
                matches,
                window=request.window,
                stride=stride,
                h_future=request.h_future,
            )
        except ValueError:
            mean_path, q25_path, q75_path, close_paths = [], [], [], []
        if last_known_close is not None:
            mean_path = _apply_bias_to_path(mean_path, last_known_close)
            q25_path = _apply_bias_to_path(q25_path, last_known_close)
            q75_path = _apply_bias_to_path(q75_path, last_known_close)
            close_paths = [_apply_bias_to_path(path, last_known_close) for path in close_paths]

    predictions = []
    future_dates = []
    if matches:
        try:
            o_pred, h_pred, l_pred, c_pred, future_dates = analog_forecast_ohlc(
                df=processed,
                matches=matches,
                window=request.window,
                stride=stride,
                h_future=request.h_future,
                agg=request.agg,
            )
        except ValueError:
            o_pred, h_pred, l_pred, c_pred, future_dates = [], [], [], [], []
        # 使用交易日序列（来自后端引擎，已是Business Day）作为坐标
        future_dates = [pd.to_datetime(day).strftime("%Y-%m-%d") for day in future_dates]
        if last_known_close is not None and len(c_pred) > 0:
            # 对未来预测应用涨跌偏移
            o_pred, h_pred, l_pred, c_pred = _apply_bias_to_ohlc(o_pred, h_pred, l_pred, c_pred, last_known_close)
        for idx, date_str in enumerate(future_dates):
            predictions.append({
                "date": date_str,
                "open": float(o_pred[idx]),
                "high": float(h_pred[idx]),
                "low": float(l_pred[idx]),
                "close": float(c_pred[idx]),
                "mean_close": float(mean_path[idx]) if idx < len(mean_path) else None,
                "close_q25": float(q25_path[idx]) if idx < len(q25_path) else None,
                "close_q75": float(q75_path[idx]) if idx < len(q75_path) else None,
            })

    show_paths = getattr(request, "show_paths", False)
    close_path_payload: List[List[float]] = []
    if show_paths:
        close_path_payload = [_to_float_list(path) for path in close_paths]

    # 历史行情用于绘图：按用户请求的时间范围全量返回（不再按 lookback 截断）
    hist_cols = [col for col in ["open", "high", "low", "close", "volume"] if col in processed.columns]
    history_slice = processed[hist_cols]
    # Restrict historical data to the most recent 120 trading days for charting
    try:
        if len(history_slice) > 120:
            history_slice = history_slice.iloc[-120:]
    except Exception:
        pass
        pass
    historical_data = []
    for idx, row in history_slice.iterrows():
        # 横坐标使用行情 df 的 trade_date（已是交易日），标准化为 YYYY-MM-DD
        entry = {"date": pd.to_datetime(idx).strftime("%Y-%m-%d")}
        for col in hist_cols:
            entry[col] = float(row[col])
        historical_data.append(entry)

    evaluation_data = None
    similar_windows = []
    hist_cols = [col for col in ["open", "high", "low", "close", "volume"] if col in processed.columns]
    close_col_available = "close" in processed.columns

    # Build a map from match index to extra metrics if ranked
    extra_map = {}
    try:
        for (fs, mi, sd, ed, ad, sc, crr, dtw) in ranked:
            extra_map[int(mi)] = {
                "sim_cos": float(sc),
                "sim_corr": float(crr),
                "sim_dtw": float(dtw),
                "final_score": float(fs),
            }
    except Exception:
        pass

    for match_idx, start_date, end_date, anchor_date, similarity in matches:
        start_pos = match_idx * stride
        end_pos = start_pos + request.window - 1
        window_slice = processed.iloc[start_pos:end_pos + 1]
        future_slice = processed.iloc[end_pos + 1:end_pos + 1 + request.h_future]

        window_dates = [pd.to_datetime(idx).strftime("%Y-%m-%d") for idx in window_slice.index]
        future_dates_preview = [pd.to_datetime(idx).strftime("%Y-%m-%d") for idx in future_slice.index]

        window_preview = {"dates": window_dates}
        future_preview = {"dates": future_dates_preview}

        for col in hist_cols:
            window_preview[col] = [float(x) for x in pd.to_numeric(window_slice[col], errors="coerce").fillna(0.0)]
            future_preview[col] = [float(x) for x in pd.to_numeric(future_slice[col], errors="coerce").fillna(0.0)]

        window_return = None
        future_return = None
        if close_col_available and len(window_preview["close"]) >= 2:
            first_close = window_preview["close"][0]
            last_close = window_preview["close"][ -1 ]
            if abs(first_close) > 1e-9:
                window_return = float((last_close - first_close) / first_close)
        if close_col_available and future_preview.get("close"):
            current_close = window_preview["close"][ -1 ]
            future_close = future_preview["close"][ -1 ] if future_preview["close"] else None
            if future_close is not None and abs(current_close) > 1e-9:
                future_return = float((future_close - current_close) / current_close)

        item = {
            "window_index": int(match_idx),
            "start_date": pd.to_datetime(start_date).strftime("%Y-%m-%d"),
            "end_date": pd.to_datetime(end_date).strftime("%Y-%m-%d"),
            "anchor_date": pd.to_datetime(anchor_date).strftime("%Y-%m-%d"),
            "similarity": float(similarity),
            "window_return": window_return,
            "future_return": future_return,
            "window_preview": window_preview,
            "future_preview": future_preview,
        }
        if int(match_idx) in extra_map:
            item.update(extra_map[int(match_idx)])
        similar_windows.append(item)

    last_window_idx = len(window_sequences) - 1
    start_pos = last_window_idx * stride
    end_pos = start_pos + request.window - 1
    index_list = list(processed.index)
    last_window = {
        "window_index": int(last_window_idx),
        "start_date": pd.to_datetime(index_list[start_pos]).strftime("%Y-%m-%d"),
        "end_date": pd.to_datetime(index_list[end_pos]).strftime("%Y-%m-%d"),
    }

    # 计算最相似交易日
    most_similar_day = None
    if similar_windows and close_col_available:
        try:
            # 获取最新交易日的数据
            latest_day_idx = len(processed) - 1
            latest_close = processed.iloc[latest_day_idx]["close"]
            latest_date = pd.to_datetime(index_list[latest_day_idx]).strftime("%Y-%m-%d")

            # 准备特征列表（使用已有的技术指标特征）
            feature_columns = []

            # 基础价格特征
            if "close" in processed.columns:
                feature_columns.append("close")
            if "volume" in processed.columns:
                feature_columns.append("volume")

            # 技术指标特征（如果存在）
            technical_features = [
                "rsi", "macd", "signal", "k", "d", "j",  # 动量指标
                "ma5", "ma10", "ma20", "ma30",  # 移动均线
                "volatility", "atr",  # 波动性指标
                "obv", "vwap",  # 成交量指标
                "bollinger_upper", "bollinger_lower",  # 布林带
            ]

            for feat in technical_features:
                if feat in processed.columns:
                    feature_columns.append(feat)

            # 如果有技术指标，使用多维特征；否则回退到原始方法
            use_multi_features = len(feature_columns) > 2

            if use_multi_features:
                # 获取最新交易日的所有特征
                latest_features = processed.iloc[latest_day_idx][feature_columns].values

                # 标准化最新交易日特征（Z-score标准化）
                feature_means = processed[feature_columns].mean()
                feature_stds = processed[feature_columns].std()
                latest_features_norm = (latest_features - feature_means) / (feature_stds + 1e-8)

            # 在所有相似窗口中查找最相似的单日
            best_similarity = -1
            best_day_info = None

            for sw in similar_windows:
                # 获取每个相似窗口的所有交易日
                sw_start_idx = sw["window_index"] * stride
                sw_end_idx = sw_start_idx + request.window - 1

                # 检查窗口内每个交易日
                for day_idx in range(sw_start_idx, sw_end_idx + 1):
                    if day_idx >= len(processed):
                        continue

                    day_close = processed.iloc[day_idx]["close"]
                    day_date = pd.to_datetime(index_list[day_idx]).strftime("%Y-%m-%d")

                    # Compute this day's own pct change (relative to previous close)
                    day_pct_change = None
                    try:
                        if "pct_change" in processed.columns:
                            raw_change = processed.iloc[day_idx]["pct_change"]
                            # pandas may return NaN; ensure a proper None for missing
                            if pd.notnull(raw_change):
                                day_pct_change = float(raw_change)
                        # Fallback: compute from close if pct_change not available
                        if day_pct_change is None and day_idx > 0:
                            prev_close = processed.iloc[day_idx - 1]["close"]
                            if prev_close is not None and abs(prev_close) > 1e-12:
                                day_pct_change = float((day_close - prev_close) / prev_close)
                    except Exception:
                        # Leave as None if any issue occurs
                        day_pct_change = None

                    if use_multi_features:
                        # 多维特征相似度计算
                        day_features = processed.iloc[day_idx][feature_columns].values
                        day_features_norm = (day_features - feature_means) / (feature_stds + 1e-8)

                        # 计算余弦相似度
                        dot_product = np.dot(latest_features_norm, day_features_norm)
                        norm_latest = np.linalg.norm(latest_features_norm)
                        norm_day = np.linalg.norm(day_features_norm)

                        if norm_latest > 0 and norm_day > 0:
                            cosine_similarity = dot_product / (norm_latest * norm_day)
                            # 将余弦相似度从[-1,1]映射到[0,1]
                            similarity = (cosine_similarity + 1) / 2
                        else:
                            similarity = 0

                        # 可选：给价格更高权重
                        if "close" in feature_columns:
                            close_idx = feature_columns.index("close")
                            price_diff = abs(day_features[close_idx] - latest_features[close_idx]) / latest_features[close_idx]
                            price_similarity = 1.0 / (1.0 + price_diff * 10)
                            # 混合相似度：70%多维特征 + 30%价格
                            similarity = similarity * 0.7 + price_similarity * 0.3

                    else:
                        # 原始方法：仅使用价格和成交量
                        price_diff = abs(day_close - latest_close) / latest_close
                        similarity = 1.0 / (1.0 + price_diff * 10)

                        if "volume" in processed.columns:
                            latest_volume = processed.iloc[latest_day_idx]["volume"]
                            day_volume = processed.iloc[day_idx]["volume"]
                            if latest_volume > 0 and day_volume > 0:
                                volume_diff = abs(day_volume - latest_volume) / latest_volume
                                volume_similarity = 1.0 / (1.0 + volume_diff * 10)
                                similarity = similarity * 0.7 + volume_similarity * 0.3

                    if similarity > best_similarity:
                        best_similarity = similarity
                        best_day_info = {
                            "date": day_date,
                            "close": float(day_close),
                            "similarity": float(similarity),
                            "from_window": sw["anchor_date"],
                            "window_similarity": sw["similarity"],
                            "features_used": len(feature_columns) if use_multi_features else 2,
                            # Store decimal daily change (e.g., 0.0123 for +1.23%)
                            "day_pct_change": day_pct_change,
                        }

            if best_day_info:
                most_similar_day = {
                    "latest_date": latest_date,
                    "latest_close": float(latest_close),
                    "similar_date": best_day_info["date"],
                    "similar_close": best_day_info["close"],
                    "similarity": best_day_info["similarity"],
                    "from_window": best_day_info["from_window"],
                    "window_similarity": best_day_info["window_similarity"],
                    "price_diff_pct": float((best_day_info["close"] - latest_close) / latest_close * 100),
                    "features_used": best_day_info["features_used"],
                    "calculation_method": "multi_features" if use_multi_features else "price_volume",
                    # Expose the similar day's own daily change in percent
                    "similar_day_change_pct": float(best_day_info["day_pct_change"] * 100) if best_day_info.get("day_pct_change") is not None else None,
                }
        except Exception as e:
            print(f"Error calculating most similar day: {e}")
            most_similar_day = None

    if getattr(request, "evaluate_daily", False):
        eval_cache = None
        eval_cache_key = None
        freeze_eval_history = bool(getattr(request, "freeze_eval_history", True))
        force_eval_refresh = bool(getattr(request, "force_eval_refresh", False))
        if freeze_eval_history:
            try:
                eval_cache_key = _build_eval_cache_key(
                    request,
                    feature_cols,
                    overrides={
                        "stride": stride,
                        "min_gap_days": min_gap_days,
                        "dedup_radius": dedup_radius,
                        "prefilter_tolerance": prefilter_tolerance,
                        "prefilter_multiplier": prefilter_multiplier,
                        "re_rank_top": re_rank_top,
                        "use_corr": use_corr,
                        "use_dtw": use_dtw,
                        "alpha_cos": a_cos,
                        "beta_corr": b_corr,
                        "gamma_dtw": g_dtw,
                    },
                )
                eval_cache = EVAL_CACHE
            except Exception:
                eval_cache = None
                eval_cache_key = None
        if eval_cache is not None and eval_cache_key and freeze_eval_history:
            try:
                if predictions and _is_finite_number(last_known_close):
                    first_pred = predictions[0] if predictions else None
                    forecast_date_str = first_pred.get("date") if isinstance(first_pred, dict) else None
                    pred_close_val = None
                    if isinstance(first_pred, dict):
                        pred_close_val = first_pred.get("close")
                        if not _is_finite_number(pred_close_val):
                            pred_close_val = first_pred.get("open")
                    _cache_forecast_eval_record(
                        eval_cache,
                        eval_cache_key,
                        forecast_date_str,
                        float(last_known_close),
                        pred_close_val,
                        match_count=len(matches) if matches is not None else None,
                    )
            except Exception:
                pass
        evaluation_data = _run_daily_evaluation(
            request=request,
            embeddings=embeddings,
            dates_seq_end=dates_seq_end,
            df=processed,
            window_sequences=window_sequences,
            signatures=signatures,
            close_np=close_np,
            stride=stride,
            min_gap_days=min_gap_days,
            dedup_radius=dedup_radius,
            prefilter_enabled=prefilter_enabled,
            prefilter_tolerance=prefilter_tolerance,
            prefilter_multiplier=prefilter_multiplier,
            re_rank_top=re_rank_top,
            use_corr=use_corr,
            use_dtw=use_dtw,
            a_cos=a_cos,
            b_corr=b_corr,
            g_dtw=g_dtw,
            sim_method=sim_method,
            eval_cache=eval_cache,
            eval_cache_key=eval_cache_key,
            freeze_eval_history=freeze_eval_history,
            force_eval_refresh=force_eval_refresh,
        )

    payload = {
        "historical_data": historical_data,
        "predictions": predictions,
        "future_dates": future_dates,
        "mean_path": _to_float_list(mean_path),
        "q25_path": _to_float_list(q25_path),
        "q75_path": _to_float_list(q75_path),
        "close_paths": close_path_payload,
        "similar_windows": similar_windows,
        "last_window": last_window,
        "most_similar_day": most_similar_day,  # 添加最相似交易日信息
        "model_info": {
            "device": DEVICE,
            "window": request.window,
            "stride": stride,
            "epochs": request.epochs,
            "topk_requested": request.topk,
            "topk_matched": len(similar_windows),
            "feature_count": len(feature_cols),
            "model_type": model_type,
            "prefilter": bool(prefilter_enabled),
            "prefilter_tolerance": prefilter_tolerance,
            "prefilter_candidates": len(candidate_indices) if candidate_indices else 0,
            "use_window_zscore": getattr(request, "use_window_zscore", True),
        },
    }
    if evaluation_data is not None:
        payload["evaluation"] = evaluation_data
    return payload


