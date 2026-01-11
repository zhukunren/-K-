# -*- coding: utf-8 -*-
"""
===============================================================================
股价预测系统 - Transformer自编码器核心预测引擎
===============================================================================

【文件说明】
本文件是整个股价预测系统的核心算法实现,基于Transformer自编码器模型,
通过历史相似窗口检索和类比预测的方法,实现对未来股价走势的预测。

【核心算法流程】
1. 数据预处理 → 提取29个技术指标特征
2. Transformer自编码器训练 → 将时间窗口编码为潜在向量
3. 相似度计算 → 使用余弦相似度找到历史相似K线形态
4. 类比预测 → 基于相似窗口的未来走势生成OHLC预测

【关键组件】
- TransformerAutoencoder: Transformer自编码器模型
- train_autoencoder_get_embeddings(): 模型训练和向量提取
- topk_similar_to_last(): TopK相似窗口检索
- analog_forecast_ohlc(): 基于相似窗口的K线预测
- plot_forecast_plotly_ohlc(): Plotly交互式图表生成

【模型架构】
输入: (batch_size, window_length, feature_dim)
  -> 线性投影
(batch_size, window_length, d_model=64)
  -> Transformer编码器 (4头注意力, 2层)
(batch_size, window_length, d_model=64)
  -> 自适应平均池化 (得到窗口级潜在向量用于相似度检索)
(batch_size, d_model=64) + (batch_size, window_length, d_model=64)
  -> 逐时间步线性解码器
(batch_size, window_length, feature_dim) -> 窗口重构输出

【核心参数说明】
WINDOW: 滑动窗口大小(默认5天) - 用于训练和相似性比较的历史数据点数
H_FUTURE: 预测未来天数(默认20天) - 预测的时间范围
TOPK: 相似窗口数量(默认8个) - 用于类比预测的历史相似案例数
EPOCHS: 训练轮数(默认30) - 模型训练的迭代次数
USE_WINDOW_ZSCORE: 是否窗口内标准化(True) - 突出形态相似性而非数值大小

【技术指标特征】(共29个)
趋势类: MA5, MA20, MACD, RSI, EMA等
动量类: ROC, Momentum, CCI, Williams %R等
波动类: Bollinger Bands, ATR, ADX等
成交量类: OBV, VWAP, MFI, Chaikin Oscillator等

【依赖库】
- torch: PyTorch深度学习框架
- pandas, numpy: 数据处理
- scikit-learn: 数据标准化
- plotly: 交互式图表生成

【外部依赖】
- preprocess.py: preprocess_data() - 特征工程
- function.py: read_day_from_tushare() - 数据获取

【使用示例】
独立运行本文件:
    python main.py

作为模块导入:
    from main import TransformerAutoencoder, analog_forecast_ohlc

【作者】基于Transformer的时间序列预测框架
【更新日期】2024-10
===============================================================================
"""

import os
from datetime import datetime
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.nn.functional as F
from sklearn.preprocessing import StandardScaler
import plotly.graph_objects as go

# ===== 你工程中的函数 =====
from preprocess import preprocess_data
from function import *   # 需包含 read_day_from_tushare 和 get_next_trade_dates
from models import (
    LSTMPredictor,
    GRUPredictor,
    CNNTransformer,
    TransformerLSTM as HybridTransformerLSTM,
    TransformerGRU as HybridTransformerGRU,
)
# 导入缓存管理器
try:
    from model_cache import cache_manager
    CACHE_ENABLED = True
except ImportError:
    CACHE_ENABLED = False
    print("Warning: 模型缓存模块未找到，将禁用缓存功能")

# ============ 参数区（可按需修改） ============
SEED = 42
SYMBOL = "000001.SH"
START_DATE = "20220101"
END_DATE   = datetime.now().strftime("%Y%m%d")

# 窗口 & 模型
# 窗口 & 模型参数
WINDOW = 5              # 滑动窗口大小，表示用于训练和相似性比较的历史数据点数量
STRIDE = 1              # 滑动步长，控制窗口移动的间隔天数
DMODEL = 64             # Transformer 模型的特征维度，即嵌入向量的大小
NHEAD  = 4              # Transformer 多头注意力机制中的头数
NLAYERS= 2              # Transformer 编码器层的数量
EPOCHS = 30             # 模型训练的轮数
LR     = 1e-3           # 学习率，控制模型参数更新的步长
USE_WINDOW_ZSCORE = True  # 是否对每个窗口内的数据进行标准化处理，以突出形态相似性而非绝对数值差异

# 相似检索
TOPK = 8                  # 取多少相似窗口来做类比
MIN_GAP_DAYS = 30         # 屏蔽与最后窗口过近的历史
DEDUP_RADIUS = 5          # 去重半径（按窗口索引）

# 预测与绘图
H_FUTURE = 20             # 预测未来天数
LOOKBACK = 100            # 历史回看K线根数
SAVE_HTML = "forecast_candlestick.html"  # 保存交互图为 HTML（可设为 "" 关闭）
SHOW_EACH_PATH = True     # 是否叠加每条相似 close 路径（淡线）
# ============================================

np.random.seed(SEED)
torch.manual_seed(SEED)
device = "cpu"  # 强制使用 CPU 避免 GPU 兼容性问题
print(f"[INFO] Using device: {device}")

# ---------- 工具函数 ----------
def create_sequences(data, window=10, stride=1):
    X = []
    for i in range(0, len(data) - window + 1, stride):
        X.append(data[i:i+window])
    return np.array(X)

def zscore_windows(X_seq, eps=1e-6):
    # 对每个窗口沿时间维做逐特征去均值/除标准差（强调形态相似）
    mean = X_seq.mean(axis=1, keepdims=True)
    std  = X_seq.std(axis=1, keepdims=True)
    return (X_seq - mean) / (std + eps)

class TransformerEncoder(nn.Module):
    def __init__(self, input_dim, d_model=64, nhead=4, num_layers=2, dropout=0.1):
        super().__init__()
        self.input_proj = nn.Linear(input_dim, d_model)
        layer = nn.TransformerEncoderLayer(
            d_model=d_model, nhead=nhead, batch_first=True, dropout=dropout
        )
        self.encoder = nn.TransformerEncoder(layer, num_layers=num_layers)
        self.pool = nn.AdaptiveAvgPool1d(1)

    def forward(self, x):               # (B,T,F)
        x = self.input_proj(x)          # (B,T,D)
        h = self.encoder(x)             # (B,T,D)
        z = self.pool(h.transpose(1, 2)).squeeze(-1)  # (B,D)
        return h, z

class TransformerAutoencoder(nn.Module):
    def __init__(self, input_dim, d_model=64, nhead=4, num_layers=2, dropout=0.1):
        super().__init__()
        self.encoder = TransformerEncoder(input_dim, d_model, nhead, num_layers, dropout)
        self.decoder = nn.Sequential(
            nn.Linear(d_model, d_model),
            nn.ReLU(),
            nn.Linear(d_model, input_dim)
        )

    def forward(self, x):
        h, z = self.encoder(x)          # h: (B,T,D), z: (B,D)
        recon = self.decoder(h)         # (B,T,F)
        return recon, z

def build_sequence_model(model_type: str, input_dim: int, d_model: int, nhead: int, num_layers: int, model_kwargs=None):
    model_kwargs = model_kwargs or {}
    model_type = (model_type or "transformer").lower()
    if model_type == "transformer":
        return TransformerAutoencoder(input_dim, d_model=d_model, nhead=nhead, num_layers=num_layers, dropout=0.1)
    if model_type == "lstm":
        hidden = model_kwargs.get('hidden_size', max(d_model, 32))
        layers = model_kwargs.get('num_layers', max(1, num_layers))
        return LSTMPredictor(input_dim, hidden_size=hidden, num_layers=layers)
    if model_type == "gru":
        hidden = model_kwargs.get('hidden_size', max(d_model, 32))
        layers = model_kwargs.get('num_layers', max(1, num_layers))
        return GRUPredictor(input_dim, hidden_size=hidden, num_layers=layers)
    if model_type == "cnn_transformer":
        return CNNTransformer(input_dim, d_model=model_kwargs.get('d_model', d_model), nhead=model_kwargs.get('nhead', nhead))
    if model_type == "transformer_lstm":
        hidden = model_kwargs.get('hidden_size', max(d_model, 64))
        return HybridTransformerLSTM(input_dim, d_model=d_model, nhead=nhead, hidden_size=hidden)
    if model_type == "transformer_gru":
        hidden = model_kwargs.get('hidden_size', max(d_model, 64))
        return HybridTransformerGRU(input_dim, d_model=d_model, nhead=nhead, hidden_size=hidden)
    raise ValueError(f"Unsupported model_type: {model_type}")

def train_autoencoder_get_embeddings(
    features_mat, df_index, window=10, stride=1,
    d_model=64, nhead=4, num_layers=2, epochs=30, lr=1e-3,
    use_window_zscore=True, device="cpu",
    model_type="transformer", model_kwargs=None
):
    # 1) 构造窗口序列
    X_seq = create_sequences(features_mat.astype(np.float32), window=window, stride=stride)
    if len(X_seq) == 0:
        raise ValueError("X_seq 为空，请检查 WINDOW/STRIDE 与样本长度是否足够。")
    if use_window_zscore:
        X_seq = zscore_windows(X_seq)

    # 每个窗口对应的“窗口末日”日期
    dates_seq_end = pd.to_datetime(df_index[window-1::stride])
    assert len(dates_seq_end) == len(X_seq), "日期与序列数量不匹配，请检查索引。"

    # 2) 模型
    model = build_sequence_model(
        model_type=model_type,
        input_dim=X_seq.shape[-1],
        d_model=d_model,
        nhead=nhead,
        num_layers=num_layers,
        model_kwargs=model_kwargs,
    ).to(device)

    optimizer = torch.optim.Adam(model.parameters(), lr=lr)
    criterion = nn.MSELoss()

    X_tensor = torch.from_numpy(X_seq).to(device)               # (N,T,F) float32

    # 3) 训练
    model.train()
    for ep in range(1, epochs+1):
        optimizer.zero_grad()
        recon, _ = model(X_tensor)
        loss = criterion(recon, X_tensor)
        loss.backward()
        optimizer.step()
        if ep % 5 == 0:
            print(f"[AE] epoch {ep:02d}/{epochs} loss={loss.item():.6f}")

    # 4) 取 embedding
    model.eval()
    with torch.no_grad():
        _, Z = model(X_tensor)  # (N, d_model)
    return model, Z, dates_seq_end, X_seq

def train_autoencoder_get_embeddings_with_cache(
    features_mat, df_index, window=10, stride=1,
    d_model=64, nhead=4, num_layers=2, epochs=30, lr=1e-3,
    use_window_zscore=True, device="cpu",
    model_type="transformer", model_kwargs=None,
    cache_params=None, use_cache=True
):
    """
    带缓存功能的训练函数

    Args:
        features_mat: 特征矩阵
        df_index: 数据索引
        window: 窗口大小
        stride: 步长
        d_model: 模型维度
        nhead: 注意力头数
        num_layers: 层数
        epochs: 训练轮数
        lr: 学习率
        use_window_zscore: 是否使用窗口标准化
        device: 设备
        model_type: 模型类型
        model_kwargs: 模型额外参数
        cache_params: 缓存相关参数（包含symbol, start_date, end_date等）
        use_cache: 是否使用缓存

    Returns:
        model, embeddings, dates_seq_end, window_sequences
    """

    # 如果缓存未启用或不使用缓存，直接调用原始函数
    if not CACHE_ENABLED or not use_cache or cache_params is None:
        return train_autoencoder_get_embeddings(
            features_mat, df_index, window, stride,
            d_model, nhead, num_layers, epochs, lr,
            use_window_zscore, device, model_type, model_kwargs
        )

    # 准备缓存参数
    full_cache_params = {
        **cache_params,
        'window': window,
        'stride': stride,
        'd_model': d_model,
        'nhead': nhead,
        'num_layers': num_layers,
        'epochs': epochs,
        'use_window_zscore': use_window_zscore,
        'model_type': model_type,
        'feature_dim': features_mat.shape[1],  # 特征维度也影响模型结构
    }

    # 尝试从缓存加载
    cache_data = cache_manager.load_cache(full_cache_params)

    if cache_data is not None:
        # 缓存命中，重建模型并加载权重
        print(f"[Cache] 使用缓存的模型，跳过训练")

        # 重建窗口序列（需要与训练时一致）
        X_seq = create_sequences(features_mat.astype(np.float32), window=window, stride=stride)
        if len(X_seq) == 0:
            raise ValueError("X_seq 为空，请检查 WINDOW/STRIDE 与样本长度是否足够。")
        if use_window_zscore:
            X_seq = zscore_windows(X_seq)

        # 重建日期序列
        dates_seq_end = pd.to_datetime(df_index[window-1::stride])

        # 重建模型
        model = build_sequence_model(
            model_type=model_type,
            input_dim=X_seq.shape[-1],
            d_model=d_model,
            nhead=nhead,
            num_layers=num_layers,
            model_kwargs=model_kwargs,
        ).to(device)

        # 加载模型权重
        model.load_state_dict(cache_data['model_state_dict'])
        model.eval()

        # 获取embeddings
        embeddings = cache_data['embeddings'].to(device)

        # 验证数据一致性
        if len(embeddings) != len(X_seq):
            print(f"[Cache] 缓存数据长度不匹配，重新训练")
            # 数据不一致，需要重新训练
            return _train_and_cache(
                features_mat, df_index, window, stride,
                d_model, nhead, num_layers, epochs, lr,
                use_window_zscore, device, model_type, model_kwargs,
                full_cache_params
            )

        return model, embeddings, dates_seq_end, X_seq

    else:
        # 缓存未命中，训练并缓存
        print(f"[Cache] 缓存未命中，开始训练")
        return _train_and_cache(
            features_mat, df_index, window, stride,
            d_model, nhead, num_layers, epochs, lr,
            use_window_zscore, device, model_type, model_kwargs,
            full_cache_params
        )

def _train_and_cache(
    features_mat, df_index, window, stride,
    d_model, nhead, num_layers, epochs, lr,
    use_window_zscore, device, model_type, model_kwargs,
    cache_params
):
    """内部函数：训练模型并缓存结果"""

    # 调用原始训练函数
    model, embeddings, dates_seq_end, X_seq = train_autoencoder_get_embeddings(
        features_mat, df_index, window, stride,
        d_model, nhead, num_layers, epochs, lr,
        use_window_zscore, device, model_type, model_kwargs
    )

    # 保存到缓存
    if CACHE_ENABLED:
        try:
            cache_manager.save_cache(
                params=cache_params,
                model=model,
                embeddings=embeddings,
                dates_seq_end=dates_seq_end,
                window_sequences=X_seq,
                scaler_params=None  # 如果需要，可以添加scaler参数
            )
            print(f"[Cache] 模型已缓存")
        except Exception as e:
            print(f"[Cache] 缓存保存失败: {str(e)}")

    return model, embeddings, dates_seq_end, X_seq

def topk_similar_to_last(
    Z, dates_seq_end, df_index, window=10, stride=1,
    k=5, min_gap_days=30, dedup_radius=5, candidate_indices=None
):
    """
    返回：[(win_idx, date_start, date_end, date_end_label, sim), ...]
    """
    Z = Z.float()
    last = Z[-1:]                                 # (1,D)
    sims = F.cosine_similarity(last, Z).squeeze() # (N,)

    # 屏蔽近邻：与最后窗口重叠的 + 最小 min_gap_days
    recent_overlaps = int(np.ceil(window / max(1, stride)))
    recent_gap_steps = int(np.ceil(min_gap_days / max(1, stride)))
    gap = max(recent_overlaps, recent_gap_steps)

    mask_base = torch.ones_like(sims, dtype=torch.bool)
    mask_base[-gap:] = False
    mask = mask_base.clone()

    if candidate_indices:
        candidate_mask = torch.zeros_like(mask_base)
        for cid in candidate_indices:
            if 0 <= cid < len(candidate_mask):
                candidate_mask[cid] = True
        if candidate_mask.any():
            mask &= candidate_mask
        else:
            mask = mask_base

    sims_masked = sims.masked_fill(~mask, float('-inf'))
    prelim_count = max(1, min(k * 5, len(sims_masked)))
    prelim = torch.topk(sims_masked, k=prelim_count)
    cand_idx = prelim.indices.cpu().numpy().tolist()
    cand_sim = prelim.values.cpu().numpy().tolist()

    picked = []
    picked_sims = []
    picked_ranges = []  # 存储已选窗口的时间范围 [(start_pos, end_pos), ...]

    def has_overlap(start1, end1, ranges_list):
        """检查新窗口是否与已选窗口有重叠"""
        for start2, end2 in ranges_list:
            # 两个区间重叠的条件：start1 <= end2 and start2 <= end1
            if start1 <= end2 and start2 <= end1:
                return True
        return False

    for idx, s in zip(cand_idx, cand_sim):
        if s == float('-inf'):
            continue
        if len(picked) >= k:
            break

        # 计算当前窗口的实际时间范围
        start_pos = idx * stride
        end_pos = start_pos + window - 1

        # 检查是否与已选窗口有时间重叠
        if not has_overlap(start_pos, end_pos, picked_ranges):
            picked.append(idx)
            picked_sims.append(s)
            picked_ranges.append((start_pos, end_pos))

    if not picked:
        sims_masked = sims.masked_fill(~mask_base, float('-inf'))
        prelim = torch.topk(sims_masked, k=prelim_count)
        cand_idx = prelim.indices.cpu().numpy().tolist()
        cand_sim = prelim.values.cpu().numpy().tolist()
        picked_ranges = []  # 重新初始化
        for idx, s in zip(cand_idx, cand_sim):
            if s == float('-inf'):
                continue
            if len(picked) >= k:
                break

            # 计算当前窗口的实际时间范围
            start_pos = idx * stride
            end_pos = start_pos + window - 1

            # 检查是否与已选窗口有时间重叠
            if not has_overlap(start_pos, end_pos, picked_ranges):
                picked.append(idx)
                picked_sims.append(s)
                picked_ranges.append((start_pos, end_pos))

    results = []
    for idx, s in zip(picked, picked_sims):
        start_pos = idx * stride
        end_pos = start_pos + window - 1
        date_start = pd.to_datetime(df_index[start_pos])
        date_end = pd.to_datetime(df_index[end_pos])
        date_end_label = pd.to_datetime(dates_seq_end[idx])
        results.append((int(idx), date_start, date_end, date_end_label, float(s)))
    return results

# ---------- close 序列（用于路径带/IQR） ----------
def get_close_series(df: pd.DataFrame) -> pd.Series:
    if 'close' in df.columns:
        return pd.to_numeric(df['close'], errors='coerce').ffill().bfill()
    elif 'pct_chg' in df.columns:
        r = 1 + pd.to_numeric(df['pct_chg'], errors='coerce').fillna(0) / 100.0
        price = r.cumprod()
        price /= price.iloc[0]
        return price
    else:
        raise ValueError("数据缺少 'close' 或 'pct_chg'，无法绘制价格走势。")

# ---------- 基于相似窗口的类比预测（close 路径带/IQR） ----------
def analog_forecast(close: pd.Series, matches, window: int, stride: int, h_future: int):
    close = close.reset_index(drop=True)
    n = len(close)
    last_end_pos = n - 1
    last_close = float(close.iloc[last_end_pos])

    paths = []
    usable = 0
    for (win_idx, _, _, _, _) in matches:
        start_pos = win_idx * stride
        end_pos = start_pos + window - 1
        after_start = end_pos + 1
        after_end   = after_start + h_future
        if after_end <= n:
            base = float(close.iloc[end_pos])
            future_slice = close.iloc[after_start:after_end].to_numpy(dtype=float)
            ratios = future_slice / base
            migrated = last_close * ratios
            paths.append(migrated)
            usable += 1

    if len(paths) == 0:
        raise ValueError("没有足够长的相似窗口用于类比预测，请减少 H_FUTURE 或放宽筛选。")

    all_paths = np.vstack(paths)
    mean_path = np.mean(all_paths, axis=0)
    q25_path  = np.quantile(all_paths, 0.25, axis=0)
    q75_path  = np.quantile(all_paths, 0.75, axis=0)
    print(f"[INFO] 可用相似窗口数（用于 close 路径带）：{usable}/{len(matches)}")
    return mean_path, q25_path, q75_path, all_paths

# ---------- 基于相似窗口生成“预测K线” ----------
def analog_forecast_ohlc(df: pd.DataFrame, matches, window: int, stride: int, h_future: int,
                         agg="median"):
    """
    用相似窗口的未来真实 OHLC 片段来构造预测 K 线：
    - 以每个相似窗口末日 close 为基准做比例化，再迁移到“今天 close”的尺度
    - 跨相似窗口对 OHLC 分别逐日聚合（median/mean）
    """
    required = ['open','high','low','close']
    if not all(col in df.columns for col in required):
        raise ValueError("需要 df 包含列：open/high/low/close 才能做 K 线预测。")

    df_ohlc = df[required].copy()
    df_ohlc = df_ohlc.apply(pd.to_numeric, errors='coerce').ffill().bfill()

    n = len(df_ohlc)
    last_end_pos = n - 1
    last_close_today = float(df_ohlc['close'].iloc[last_end_pos])

    O_paths, H_paths, L_paths, C_paths = [], [], [], []
    usable = 0
    for (win_idx, _, _, _, _) in matches:
        start_pos = win_idx * stride
        end_pos   = start_pos + window - 1
        after_start = end_pos + 1
        after_end   = after_start + h_future
        if after_end <= n:
            seg = df_ohlc.iloc[after_start:after_end]
            base_close = float(df_ohlc['close'].iloc[end_pos])
            if base_close == 0:
                continue
            O_paths.append((seg['open' ].to_numpy(dtype=float)/base_close) * last_close_today)
            H_paths.append((seg['high' ].to_numpy(dtype=float)/base_close) * last_close_today)
            L_paths.append((seg['low'  ].to_numpy(dtype=float)/base_close) * last_close_today)
            C_paths.append((seg['close'].to_numpy(dtype=float)/base_close) * last_close_today)
            usable += 1

    if usable == 0:
        raise ValueError("没有足够长的相似窗口用于 K 线预测，请缩短 H_FUTURE 或放宽筛选。")

    O_paths = np.vstack(O_paths)
    H_paths = np.vstack(H_paths)
    L_paths = np.vstack(L_paths)
    C_paths = np.vstack(C_paths)

    if   agg == "median":
        o_pred = np.median(O_paths, axis=0)
        h_pred = np.median(H_paths, axis=0)
        l_pred = np.median(L_paths, axis=0)
        c_pred = np.median(C_paths, axis=0)
    elif agg == "mean":
        o_pred = np.mean(O_paths, axis=0)
        h_pred = np.mean(H_paths, axis=0)
        l_pred = np.mean(L_paths, axis=0)
        c_pred = np.mean(C_paths, axis=0)
    elif agg == "max":
        # 最优路径 - 选择最高的预测值
        o_pred = np.max(O_paths, axis=0)
        h_pred = np.max(H_paths, axis=0)
        l_pred = np.max(L_paths, axis=0)
        c_pred = np.max(C_paths, axis=0)
    elif agg == "min":
        # 保守预测 - 选择最低的预测值
        o_pred = np.min(O_paths, axis=0)
        h_pred = np.min(H_paths, axis=0)
        l_pred = np.min(L_paths, axis=0)
        c_pred = np.min(C_paths, axis=0)
    else:
        raise ValueError("agg 仅支持 'median', 'mean', 'max' 或 'min'")

    # 第一根预测K线的 open 与“今天 close”对齐，保证视觉连续
    o_pred[0] = last_close_today

    # 保证 high/low 合理范围
    hi = np.maximum.reduce([h_pred, o_pred, c_pred])
    lo = np.minimum.reduce([l_pred, o_pred, c_pred])
    h_pred, l_pred = hi, lo

    last_date = pd.to_datetime(df_ohlc.index[-1])
    # 使用交易日历API获取真实交易日（自动跳过周末和节假日）
    try:
        # 调用 Baostock API 获取未来的真实交易日
        from function import get_next_trade_dates
        next_trade_date = last_date + pd.Timedelta(days=1)
        future_dates = get_next_trade_dates(next_trade_date, periods=h_future)
    except Exception as e:
        # 如果获取交易日历失败，降级使用工作日（仅跳过周末）
        print(f"[WARNING] 获取交易日历失败: {e}，降级使用工作日（pd.bdate_range）")
        future_dates = pd.bdate_range(last_date + pd.Timedelta(days=1), periods=h_future)

    print(f"[INFO] 可用相似窗口数（用于 K 线）：{usable}/{len(matches)}")
    return o_pred, h_pred, l_pred, c_pred, future_dates

# ---------- Plotly：历史K线 + 预测K线 ----------
def plot_forecast_plotly_ohlc(df, lookback, mean_path, q25_path, q75_path, future_dates,
                              o_pred, h_pred, l_pred, c_pred,
                              show_each_paths=None, save_html=None):
    idx = pd.to_datetime(df.index)
    hist_slice = df.iloc[-min(lookback, len(df)):]
    hist_idx = idx[-min(lookback, len(df)):]

    if not all(c in df.columns for c in ['open','high','low','close']):
        raise ValueError("绘制 K 线需要 df 包含 open/high/low/close 列。")

    fig = go.Figure()

    # 历史 K 线
    fig.add_trace(go.Candlestick(
        x=hist_idx,
        open=hist_slice['open'],
        high=hist_slice['high'],
        low=hist_slice['low'],
        close=hist_slice['close'],
        name="历史K线",
        increasing_line_color="#26a69a",
        decreasing_line_color="#ef5350",
        increasing_fillcolor="#26a69a",
        decreasing_fillcolor="#ef5350",
        showlegend=True
    ))

    # 预测 K 线
    fig.add_trace(go.Candlestick(
        x=future_dates,
        open=o_pred, high=h_pred, low=l_pred, close=c_pred,
        name="预测K线",
        increasing_line_color="rgba(33,150,243,1.0)",
        decreasing_line_color="rgba(25,118,210,1.0)",
        increasing_fillcolor="rgba(33,150,243,0.7)",
        decreasing_fillcolor="rgba(25,118,210,0.7)",
        opacity=0.85,
        showlegend=True
    ))

    # 可选：close 的 IQR 参考带
    if q25_path is not None and q75_path is not None:
        fig.add_trace(go.Scatter(
            x=future_dates, y=q75_path,
            mode='lines', line=dict(width=0),
            hoverinfo='skip',
            showlegend=False
        ))
        fig.add_trace(go.Scatter(
            x=future_dates, y=q25_path,
            mode='lines',
            fill='tonexty', fillcolor='rgba(33, 150, 243, 0.15)',
            line=dict(width=0),
            name='预测区间（Close IQR）'
        ))

    # 可选：每条 close 路径（淡线）
    if show_each_paths is not None and len(show_each_paths) > 0:
        for path in show_each_paths:
            fig.add_trace(go.Scatter(
                x=future_dates, y=path,
                mode='lines',
                line=dict(width=1),
                opacity=0.25,
                showlegend=False,
                hoverinfo='skip'
            ))

    # 布局
    fig.update_layout(
        title="相似历史窗口类比预测（历史K线 + 预测K线，Plotly）",
        xaxis_title="日期",
        yaxis_title="价格",
        xaxis_rangeslider_visible=False,
        template="plotly_white",
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0)
    )

    # 横轴范围覆盖历史 + 未来，并在交界处加竖线
    full_x = list(hist_idx) + list(future_dates)
    fig.update_xaxes(range=[full_x[0], full_x[-1]])
    if len(hist_idx) > 0:
        fig.add_vline(x=hist_idx[-1], line_width=1, line_dash="dot", line_color="gray")

    if save_html:
        fig.write_html(save_html, include_plotlyjs="cdn")
        print(f"[INFO] 交互图已保存为 HTML：{save_html}")
    fig.show()

# ---------- 主流程 ----------
def main():
    # 1) 取数据 & 预处理
    df_raw = read_day_from_tushare(SYMBOL, 'index', START_DATE, END_DATE)
    data = preprocess_data(df_raw, N=1, mixture_depth=1, mark_labels=False)

    df = data[0].copy()
    df = df.sort_values("trade_date")
    df.set_index("trade_date", inplace=True)
    df = df.fillna(0)
    df.index = pd.to_datetime(df.index)

    feature_cols = data[1]
    assert len(feature_cols) > 0, "预处理没有返回特征列，请检查 preprocess_data。"

    # 2) 特征矩阵 & 标准化
    X_df = df[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0)
    scaler = StandardScaler()
    features_mat = scaler.fit_transform(X_df.values).astype(np.float32)

    # 3) 训练自编码器并取 embedding
    model, Z, dates_seq_end, X_seq = train_autoencoder_get_embeddings(
        features_mat, df.index,
        window=WINDOW, stride=STRIDE,
        d_model=DMODEL, nhead=NHEAD, num_layers=NLAYERS,
        epochs=EPOCHS, lr=LR,
        use_window_zscore=USE_WINDOW_ZSCORE,
        device=device
    )

    # 4) 相似检索（TopK）
    results = topk_similar_to_last(
        Z, dates_seq_end, df.index,
        window=WINDOW, stride=STRIDE,
        k=TOPK, min_gap_days=MIN_GAP_DAYS, dedup_radius=DEDUP_RADIUS
    )

    # 打印最后窗口范围
    last_idx = len(X_seq) - 1
    start_pos = last_idx * STRIDE
    end_pos   = start_pos + WINDOW - 1
    print(f"\n===== 最后一个窗口 =====")
    print(f"窗口索引={last_idx}, 范围={df.index[start_pos].date()} ~ {df.index[end_pos].date()}")

    # 打印相似窗口
    print("\n===== 与最终样本最相似的历史窗口 =====")
    for (idx, d_start, d_end, d_end_label, sim) in results:
        print(f"[win {idx:4d}] {d_start.date()} ~ {d_end.date()} | 末日={d_end_label.date()} | 相似度={sim:.4f}")

    # 5) close 路径带（用于 IQR 参考）
    mean_path, q25_path, q75_path, all_paths = analog_forecast(
        close=get_close_series(df),
        matches=results, window=WINDOW, stride=STRIDE, h_future=H_FUTURE
    )

    # 6) 预测 K 线（OHLC 聚合）
    o_pred, h_pred, l_pred, c_pred, future_dates = analog_forecast_ohlc(
        df=df, matches=results,
        window=WINDOW, stride=STRIDE, h_future=H_FUTURE,
        agg="median"   # or "mean"
    )

    # 7) 绘图（Plotly 历史K线 + 预测K线）
    plot_forecast_plotly_ohlc(
        df=df, lookback=LOOKBACK,
        mean_path=mean_path, q25_path=q25_path, q75_path=q75_path, future_dates=future_dates,
        o_pred=o_pred, h_pred=h_pred, l_pred=l_pred, c_pred=c_pred,
        show_each_paths=all_paths if SHOW_EACH_PATH else None,
        save_html=SAVE_HTML if SAVE_HTML else None
    )

    # 8) （可选）保存模型与标准化器
    os.makedirs("models", exist_ok=True)
    torch.save(model.state_dict(), "models/transformer_autoencoder.pt")
    import joblib
    joblib.dump(scaler, "models/feature_scaler.pkl")
    print("[INFO] 模型与标准化器已保存到 models/ 目录。")

if __name__ == "__main__":
    main()
