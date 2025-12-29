# -*- coding: utf-8 -*-
"""
===============================================================================
模型缓存管理器 - 用于缓存训练好的模型以提升性能
===============================================================================

【功能说明】
本模块提供模型缓存功能，避免重复训练相同配置的模型，大幅提升预测速度。

【缓存策略】
1. 缓存键：基于股票代码、日期范围、模型参数等生成唯一标识
2. 缓存内容：模型权重、Scaler参数、Embeddings、元数据
3. 存储方式：本地文件系统（pickle序列化）
4. 过期策略：基于文件修改时间，默认7天过期

【性能优化】
- 首次训练：正常训练并缓存
- 后续请求：直接加载缓存，跳过训练过程
- 预期提升：CPU环境下可提升5-10倍速度

===============================================================================
"""

import os
import pickle
import hashlib
import json
import time
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import numpy as np
import torch
import torch.nn as nn
from pathlib import Path
import logging

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class ModelCacheManager:
    """模型缓存管理器"""

    def __init__(self, cache_dir: str = "model_cache", max_cache_age_days: int = 7):
        """
        初始化缓存管理器

        Args:
            cache_dir: 缓存目录路径
            max_cache_age_days: 缓存最大有效期（天）
        """
        self.cache_dir = Path(cache_dir)
        self.max_cache_age_days = max_cache_age_days

        # 创建缓存目录
        self.cache_dir.mkdir(exist_ok=True)

        # 清理过期缓存
        self._cleanup_expired_cache()

    def _generate_cache_key(self, params: Dict[str, Any]) -> str:
        """
        生成缓存键

        Args:
            params: 模型训练参数字典

        Returns:
            唯一的缓存键字符串
        """
        # 提取关键参数
        key_params = {
            'symbol': params.get('symbol', ''),
            'start_date': params.get('start_date', ''),
            'end_date': params.get('end_date', ''),
            'window': params.get('window', 10),
            'stride': params.get('stride', 1),
            'model_type': params.get('model_type', 'transformer'),
            'selected_features': sorted(params.get('selected_features', [])),
            'epochs': params.get('epochs', 20),
            'use_window_zscore': params.get('use_window_zscore', True),
            'd_model': params.get('d_model', 64),
            'nhead': params.get('nhead', 4),
            'num_layers': params.get('num_layers', 2),
        }

        # 将参数转换为JSON字符串并计算哈希
        param_str = json.dumps(key_params, sort_keys=True)
        hash_obj = hashlib.sha256(param_str.encode())
        cache_key = hash_obj.hexdigest()[:16]  # 使用前16位作为键

        # 添加可读前缀
        prefix = f"{key_params['symbol']}_{key_params['model_type']}"
        return f"{prefix}_{cache_key}"

    def _get_cache_path(self, cache_key: str) -> Path:
        """获取缓存文件路径"""
        return self.cache_dir / f"{cache_key}.pkl"

    def _get_metadata_path(self, cache_key: str) -> Path:
        """获取元数据文件路径"""
        return self.cache_dir / f"{cache_key}_meta.json"

    def save_cache(self,
                   params: Dict[str, Any],
                   model: nn.Module,
                   embeddings: torch.Tensor,
                   dates_seq_end: Any,
                   window_sequences: np.ndarray,
                   scaler_params: Optional[Dict] = None) -> str:
        """
        保存模型缓存

        Args:
            params: 训练参数
            model: 训练好的模型
            embeddings: 提取的嵌入向量
            dates_seq_end: 窗口结束日期序列
            window_sequences: 窗口序列数据
            scaler_params: 标准化器参数

        Returns:
            缓存键
        """
        cache_key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        try:
            # 准备缓存数据
            cache_data = {
                'model_state_dict': model.state_dict(),
                'model_type': params.get('model_type', 'transformer'),
                'embeddings': embeddings.cpu(),
                'dates_seq_end': dates_seq_end,
                'window_sequences': window_sequences,
                'scaler_params': scaler_params,
                'timestamp': datetime.now().isoformat(),
            }

            # 保存缓存数据
            with open(cache_path, 'wb') as f:
                pickle.dump(cache_data, f)

            # 保存元数据（用于快���查询）
            metadata = {
                'cache_key': cache_key,
                'params': params,
                'timestamp': datetime.now().isoformat(),
                'file_size': os.path.getsize(cache_path),
            }

            with open(meta_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, indent=2, ensure_ascii=False)

            logger.info(f"模型缓存已保存: {cache_key}")
            return cache_key

        except Exception as e:
            logger.error(f"保存缓存失败: {str(e)}")
            # 清理可能的部分文件
            if cache_path.exists():
                cache_path.unlink()
            if meta_path.exists():
                meta_path.unlink()
            raise

    def load_cache(self, params: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """
        加载模型缓存

        Args:
            params: 训练参数

        Returns:
            缓存数据字典，如果不存在或过期则返回None
        """
        cache_key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        # 检查缓存文件是否存在
        if not cache_path.exists() or not meta_path.exists():
            logger.info(f"缓存未找到: {cache_key}")
            return None

        # 检查缓存是否过期
        file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        if file_age > timedelta(days=self.max_cache_age_days):
            logger.info(f"缓存已过期: {cache_key}")
            self._remove_cache(cache_key)
            return None

        try:
            # 加载缓存数据
            with open(cache_path, 'rb') as f:
                cache_data = pickle.load(f)

            logger.info(f"缓存命中: {cache_key}")
            return cache_data

        except Exception as e:
            logger.error(f"加载缓存失败: {str(e)}")
            # 删除损坏的缓存
            self._remove_cache(cache_key)
            return None

    def _remove_cache(self, cache_key: str):
        """删除指定缓存"""
        cache_path = self._get_cache_path(cache_key)
        meta_path = self._get_metadata_path(cache_key)

        if cache_path.exists():
            cache_path.unlink()
        if meta_path.exists():
            meta_path.unlink()

        logger.info(f"已删除缓存: {cache_key}")

    def _cleanup_expired_cache(self):
        """清理过期的缓存文件"""
        now = datetime.now()
        expired_count = 0

        for cache_file in self.cache_dir.glob("*.pkl"):
            file_age = now - datetime.fromtimestamp(cache_file.stat().st_mtime)
            if file_age > timedelta(days=self.max_cache_age_days):
                # 删除缓存文件和对应的元数据
                cache_key = cache_file.stem
                self._remove_cache(cache_key)
                expired_count += 1

        if expired_count > 0:
            logger.info(f"清理了 {expired_count} 个过期缓存")

    def clear_all_cache(self):
        """清空所有缓存"""
        count = 0
        for cache_file in self.cache_dir.glob("*.pkl"):
            cache_key = cache_file.stem
            self._remove_cache(cache_key)
            count += 1

        logger.info(f"已清空 {count} 个缓存文件")

    def get_cache_stats(self) -> Dict[str, Any]:
        """
        获取缓存统计信息

        Returns:
            包含缓存统计的字典
        """
        cache_files = list(self.cache_dir.glob("*.pkl"))
        total_size = sum(f.stat().st_size for f in cache_files)

        # 获取最新和最旧的缓存
        if cache_files:
            cache_files.sort(key=lambda x: x.stat().st_mtime)
            oldest = datetime.fromtimestamp(cache_files[0].stat().st_mtime)
            newest = datetime.fromtimestamp(cache_files[-1].stat().st_mtime)
        else:
            oldest = newest = None

        return {
            'cache_count': len(cache_files),
            'total_size_mb': total_size / (1024 * 1024),
            'oldest_cache': oldest.isoformat() if oldest else None,
            'newest_cache': newest.isoformat() if newest else None,
            'cache_dir': str(self.cache_dir),
            'max_age_days': self.max_cache_age_days,
        }

    def list_caches(self) -> list:
        """List cached models' metadata for UI display."""
        entries = []
        for meta_file in self.cache_dir.glob("*_meta.json"):
            try:
                with open(meta_file, 'r', encoding='utf-8') as f:
                    meta = json.load(f)
                # Attach basic file stats
                cache_key = meta.get('cache_key') or meta_file.stem.replace('_meta', '')
                data_path = self._get_cache_path(cache_key)
                file_size = data_path.stat().st_size if data_path.exists() else meta.get('file_size', 0)
                entries.append({
                    'cache_key': cache_key,
                    'timestamp': meta.get('timestamp'),
                    'params': meta.get('params', {}),
                    'file_size': file_size,
                })
            except Exception:
                continue
        # Sort by timestamp desc if available
        try:
            entries.sort(key=lambda x: x.get('timestamp') or '', reverse=True)
        except Exception:
            pass
        return entries

    def check_cache_exists(self, params: Dict[str, Any]) -> bool:
        """
        检查缓存是否存在且有效

        Args:
            params: 训练参数

        Returns:
            True if 缓存存在且有效，否则 False
        """
        cache_key = self._generate_cache_key(params)
        cache_path = self._get_cache_path(cache_key)

        if not cache_path.exists():
            return False

        # 检查是否过期
        file_age = datetime.now() - datetime.fromtimestamp(cache_path.stat().st_mtime)
        return file_age <= timedelta(days=self.max_cache_age_days)


# 全局缓存管理器实例
cache_manager = ModelCacheManager()
