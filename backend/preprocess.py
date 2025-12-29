# -*- coding: utf-8 -*-
"""
===============================================================================
数据预处理和特征工程模块 - 技术指标计算与特征构建
===============================================================================

【文件说明】
本文件是股价预测系统的数据预处理核心模块,负责将原始OHLCV数据转换为
包含丰富技术指标的特征矩阵,为机器学习模型提供输入。

【主要功能】
1. preprocess_data(): 完整的数据预处理流程
   - 计算29+个技术指标
   - 生成衍生特征
   - 特征过滤(方差过滤、相关性过滤)
   - 可选的混合因子生成和PCA降维

2. correlation_filtering(): 相关性特征过滤
3. pca_reduction(): PCA降维

【技术指标分类】(共29+个核心指标)

一、趋势指标
- MA_5, MA_20, MA_50, MA_200: 简单移动平均线
- EMA_5, EMA_20: 指数移动平均线
- MACD, MACD_signal: MACD指标及信号线
- Slope_MA5: MA5斜率

二、动量指标
- RSI_14: 相对强弱指数
- Momentum_10: 动量指标
- ROC_10: 变化率
- K, D: KD随机指标
- CCI_20: 商品通道指标
- Williams_%R_14: 威廉指标
- Ultimate_Osc: 终极振荡器
- PPO: 价格振荡百分比

三、波动率指标
- UpperBand, MiddleBand, LowerBand: 布林带
- Bollinger_Width: 布林带宽度
- ATR_14: 平均真实波幅
- Volatility_10: 历史波动率
- ADX_14: 平均趋向指数
- Plus_DI, Minus_DI: 方向性指标

四、成交量指标
- OBV: 能量潮指标
- VWAP: 成交量加权均价
- volume_Change: 成交量变化率
- MFI_14: 资金流量指标
- CMF_20: 蔡金资金流
- Chaikin_Osc: 蔡金振荡器
- volume_Spike_Count: 成交量异动计数

五、形态特征
- Cross_MA5_Count: MA5交叉次数
- ConsecutiveUp/Down: 连续上涨/下跌天数
- MA5_MA20_Cross: 均线交叉信号

六、衍生特征
- close_MA5_Diff: 价格与MA5差值
- MA5_MA20_Diff: 短期与长期均线差
- RSI_Signal: RSI偏离50的程度
- MACD_Diff: MACD与信号线差值
- Bollinger_Position: 价格在布林带中的位置
- K_D_Diff: KD指标差值

【数据流程】
原始数据(OHLCV)
  ↓ 排序和索引设置
基础特征计算(MA, RSI, MACD等)
  ↓ 成交量相关指标
扩展指标(Ichimoku, Coppock等)
  ↓ 打标签(可选,训练时使用)
计数指标和衍生因子
  ↓ 特征过滤(方差+相关性)
  ↓ 混合因子生成(可选)
  ↓ PCA降维(可选)
最终特征矩阵

【参数说明】
- N: 打标签的窗口大小
- mixture_depth: 混合因子深度(1=不混合, >1=多层组合)
- mark_labels: 是否标注局部高低点(训练时True,预测时False)
- selected_features: 用户选择的特征列表(None=使用全部)

【过滤策略】
1. 方差过滤: 移除方差<0.0001的低变异特征
2. 相关性过滤: 移除相关性>0.95的高相关特征
3. PCA降维: 将混合因子降维至100维

【依赖模块】
- function.py: 所有技术指标计算函数
- sklearn: 特征选择和降维工具

【使用示例】
data, features = preprocess_data(
    data=df_raw,
    N=5,
    mixture_depth=1,
    mark_labels=False,
    selected_features=['RSI_Signal', 'MACD_Diff']
)

【注意事项】
1. 数据至少需要200+天才能计算所有指标(MA_200需要)
2. 混合因子生成会显著增加特征数量和计算时间
3. 用户选择特征时,特征名不区分大小写

【作者】特征工程模块
【更新日期】2024-10
===============================================================================
"""
# preprocess.py
import os
import numpy as np
import pandas as pd
from itertools import combinations
from sklearn.decomposition import PCA
from sklearn.feature_selection import VarianceThreshold
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import RandomForestClassifier
from function import *
# 从外部 function.py 导入技术指标计算函数
# 请确保你的 function.py 文件中包含 compute_RSI, compute_MACD, compute_KD, compute_momentum, compute_ROC, compute_Bollinger_Bands,
# compute_ATR, compute_volatility, compute_OBV, compute_VWAP, compute_MFI, compute_CMF, compute_chaikin_oscillator,
# compute_CCI, compute_williams_r, compute_zscore, compute_ADX, compute_TRIX, compute_ultimate_oscillator, compute_PPO,
# compute_DPO, compute_KST, compute_KAMA, compute_EMA, compute_MoneyFlowIndex, identify_low_troughs, identify_high_peaks,
# compute_SMA, compute_PercentageB, compute_AccumulationDistribution, compute_highlow_Spread, compute_PriceChannel, compute_RenkoSlope
from function import *
import torch

USER_ID = "user_123" 
# 封装相关性过滤函数
def correlation_filtering(data, features, threshold=0.95):
    """
    根据相关性阈值过滤特征，移除高相关性特征。
    
    参数:
        data: 包含特征数据的DataFrame
        features: 待过滤的特征列表
        threshold: 相关性阈值（默认0.95）
        
    返回:
        过滤后的特征列表
    """
    corr_matrix = data[features].corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [column for column in upper.columns if any(upper[column] > threshold)]
    filtered_features = [f for f in features if f not in to_drop]
    print(f"相关性过滤后剩余特征数：{len(filtered_features)}")
    return filtered_features

# 封装 PCA 降维函数
def pca_reduction(data, features, max_components=100):
    """
    对给定特征进行 PCA 降维，并将降维后的特征添加到 data 中。
    
    参数:
        data: 包含特征数据的 DataFrame
        features: 待降维的特征列表
        max_components: 最大降维维度（默认100）
        
    返回:
        PCA 后生成的特征名称列表
    """
    X = data[features].fillna(0).values
    n_components = min(max_components, len(features))
    pca = PCA(n_components=n_components)
    X_pca = pca.fit_transform(X)
    pca_feature_names = [f'PCA_{i}' for i in range(n_components)]
    for i, name in enumerate(pca_feature_names):
        data[name] = X_pca[:, i]
    print(f"PCA降维后生成 {n_components} 个特征。")
    return pca_feature_names

def preprocess_data(
    data: pd.DataFrame,
    N: int,
    mixture_depth: int,
    mark_labels: bool = True,
    selected_features: list = None,
):
    import torch
    """
    完整的特征工程示例:
      1) 数据排序 & 设置索引
      2) 原有手动计算的一些基础特征
      3) 调用 generate_features(data) 扩充更多特征
      4) (可选) 打标签 Peak/Trough
      5) 添加计数指标、衍生因子
      6) 整理 base_features, 并做方差过滤 & 相关性过滤
      7) mixture_depth>1 时生成混合因子, 并用 PCA 压缩
      8) 删除 NaN, 返回 data 与最终 all_features

    参数:
      data: 原始数据，至少包含 'trade_date','Open','high','low','close' 等
      N: 用于打标签的窗口大小
      mixture_depth: 混合因子深度 (1 表示不做混合，>1 则做多层组合)
      mark_labels: 是否标注局部高/低点
      selected_features: 用户选择的特征列表，如果为None则使用所有特征
      min_features_to_select, max_features_for_mixture: 预留的可选参数，目前未用

    返回:
      data, all_features
      - data: 处理后的 DataFrame（含新特征、滤除缺失值后）
      - all_features: 最终可用于建模的特征列名
    """
    print("开始预处理数据...")
    # (A) 对数据做排序、索引
    print("开始预处理数据...")

    data = data.sort_values('trade_date').copy()
    data.index = pd.to_datetime(data['trade_date'], format='%Y%m%d')
    
    # ----------------- 原有基本特征计算 -----------------
    data['MA_5'] = data['close'].rolling(window=5).mean()
    data['MA_20'] = data['close'].rolling(window=20).mean()
    data['MA_50'] = data['close'].rolling(window=50).mean()
    data['MA_200'] = data['close'].rolling(window=200).mean()
    data['EMA_5'] = data['close'].ewm(span=5, adjust=False).mean()
    data['EMA_20'] = data['close'].ewm(span=20, adjust=False).mean()
    data['Price_MA20_Diff'] = (data['close'] - data['MA_20']) / data['MA_20']
    data['MA5_MA20_Cross'] = np.where(data['MA_5'] > data['MA_20'], 1, 0)
    data['MA5_MA20_Cross_Diff'] = data['MA5_MA20_Cross'].diff()
    data['Slope_MA5'] = data['MA_5'].diff()
    data['RSI_14'] = compute_RSI(data['close'], period=14)
    data['MACD'], data['MACD_signal'] = compute_MACD(data['close'])
    data['MACD_Cross'] = np.where(data['MACD'] > data['MACD_signal'], 1, 0)
    data['MACD_Cross_Diff'] = data['MACD_Cross'].diff()
    data['K'], data['D'] = compute_KD(data['high'], data['low'], data['close'], period=14)
    data['Momentum_10'] = compute_momentum(data['close'], period=10)
    data['ROC_10'] = compute_ROC(data['close'], period=10)
    data['RSI_Reversal'] = (data['RSI_14'] > 70).astype(int) - (data['RSI_14'] < 30).astype(int)
    data['Reversal_Signal'] = (data['close'] > data['high'].rolling(window=10).max()).astype(int) - (data['close'] < data['low'].rolling(window=10).min()).astype(int)
    data['UpperBand'], data['MiddleBand'], data['lowerBand'] = compute_Bollinger_Bands(data['close'], period=20)
    data['ATR_14'] = compute_ATR(data['high'], data['low'], data['close'], period=14)
    data['Volatility_10'] = compute_volatility(data['close'], period=10)
    data['Bollinger_Width'] = (data['UpperBand'] - data['lowerBand']) / data['MiddleBand']
    
    if 'volume' in data.columns:
        data['OBV'] = compute_OBV(data['close'], data['volume'])
        data['volume_Change'] = data['volume'].pct_change()
        data['VWAP'] = compute_VWAP(data['high'], data['low'], data['close'], data['volume'])
        data['MFI_14'] = compute_MFI(data['high'], data['low'], data['close'], data['volume'], period=14)
        data['CMF_20'] = compute_CMF(data['high'], data['low'], data['close'], data['volume'], period=20)
        data['Chaikin_Osc'] = compute_chaikin_oscillator(data['high'], data['low'], data['close'], data['volume'], short_period=3, long_period=10)
    else:
        data['OBV'] = np.nan
        data['volume_Change'] = np.nan
        data['VWAP'] = np.nan
        data['MFI_14'] = np.nan
        data['CMF_20'] = np.nan
        data['Chaikin_Osc'] = np.nan
        
    data['CCI_20'] = compute_CCI(data['high'], data['low'], data['close'], period=20)
    data['Williams_%R_14'] = compute_williams_r(data['high'], data['low'], data['close'], period=14)
    data['ZScore_20'] = compute_zscore(data['close'], period=20)
    data['Price_Mean_Diff'] = (data['close'] - data['close'].rolling(window=10).mean()) / data['close'].rolling(window=10).mean()
    data['high_Mean_Diff'] = (data['high'] - data['high'].rolling(window=10).mean()) / data['high'].rolling(window=10).mean()
    data['low_Mean_Diff'] = (data['low'] - data['low'].rolling(window=10).mean()) / data['low'].rolling(window=10).mean()
    data['Plus_DI'], data['Minus_DI'], data['ADX_14'] = compute_ADX(data['high'], data['low'], data['close'], period=14)
    data['TRIX_15'] = compute_TRIX(data['close'], period=15)
    data['Ultimate_Osc'] = compute_ultimate_oscillator(data['high'], data['low'], data['close'], short_period=7, medium_period=14, long_period=28)
    data['PPO'] = compute_PPO(data['close'], fast_period=12, slow_period=26)
    data['DPO_20'] = compute_DPO(data['close'], period=20)
    data['KST'], data['KST_signal'] = compute_KST(data['close'], r1=10, r2=15, r3=20, r4=30, sma1=10, sma2=10, sma3=10, sma4=15)
    data['KAMA_10'] = compute_KAMA(data['close'], n=10, pow1=2, pow2=30)
    data['Seasonality'] = np.sin(2 * np.pi * data.index.dayofyear / 365)
    data['one'] = 1

    # ----------------- 新增更多样化特征 -----------------
    data['SMA_10'] = compute_SMA(data['close'], window=10)
    data['SMA_30'] = compute_SMA(data['close'], window=30)
    data['EMA_10'] = compute_EMA(data['close'], span=10)
    data['EMA_30'] = compute_EMA(data['close'], span=30)
    data['PercentB'] = compute_PercentageB(data['close'], data['UpperBand'], data['lowerBand'])
    if 'volume' in data.columns:
        data['AccumDist'] = compute_AccumulationDistribution(data['high'], data['low'], data['close'], data['volume'])
    else:
        data['AccumDist'] = np.nan
    if 'volume' in data.columns:
        data['MFI_New'] = compute_MoneyFlowIndex(data['high'], data['low'], data['close'], data['volume'], period=14)
    else:
        data['MFI_New'] = np.nan
    data['HL_Spread'] = compute_HighLow_Spread(data['high'], data['low'])
    price_channel = compute_PriceChannel(data['high'], data['low'], data['close'], window=20)
    data['PriceChannel_Mid'] = price_channel['middle_channel']
    data['RenkoSlope'] = compute_RenkoSlope(data['close'], bricks=3)


    # ------------------ 4) 打标签 (可选) ------------------
    if mark_labels:
        print("寻找局部高点和低点(仅训练阶段)...")
        N = int(N)
        data = identify_low_troughs(data, N)
        data = identify_high_peaks(data, N)
    else:
        # 若不需要，则保证 Peak/Trough 不存在或置为0
        if 'Peak' in data.columns:
            data.drop(columns=['Peak'], inplace=True)
        if 'Trough' in data.columns:
            data.drop(columns=['Trough'], inplace=True)
        data['Peak'] = 0
        data['Trough'] = 0

    # ------------------ 5) 添加计数指标 ------------------
    print("添加计数指标...")
    data['PriceChange'] = data['close'].diff()
    data['Up'] = np.where(data['PriceChange'] > 0, 1, 0)
    data['Down'] = np.where(data['PriceChange'] < 0, 1, 0)
    data['ConsecutiveUp'] = data['Up'] * (data['Up'].groupby((data['Up'] != data['Up'].shift()).cumsum()).cumcount() + 1)
    data['ConsecutiveDown'] = data['Down'] * (data['Down'].groupby((data['Down'] != data['Down'].shift()).cumsum()).cumcount() + 1)
    window_size = 10
    data['Cross_MA5'] = np.where(data['close'] > data['MA_5'], 1, 0)
    data['Cross_MA5_Count'] = data['Cross_MA5'].rolling(window=window_size).sum()
    if 'volume' in data.columns:
        data['volume_MA_5'] = data['volume'].rolling(window=5).mean()
        data['volume_Spike'] = np.where(data['volume'] > data['volume_MA_5'] * 1.5, 1, 0)
        data['volume_Spike_Count'] = data['volume_Spike'].rolling(window=10).sum()
    else:
        data['volume_Spike_Count'] = np.nan
    
    print("构建基础因子...")
    data['close_MA5_Diff'] = data['close'] - data['MA_5']
    data['Pch'] = data['close'] / data['close'].shift(1) - 1
    # 涨跌幅（与 Pch 等价，命名更直观供前端选择）
    data['pct_change'] = data['Pch']
    data['MA5_MA20_Diff'] = data['MA_5'] - data['MA_20']
    data['RSI_Signal'] = data['RSI_14'] - 50
    data['MACD_Diff'] = data['MACD'] - data['MACD_signal']
    band_range = (data['UpperBand'] - data['lowerBand']).replace(0, np.nan)
    data['Bollinger_Position'] = (data['close'] - data['MiddleBand']) / band_range
    data['Bollinger_Position'] = data['Bollinger_Position'].fillna(0)
    data['K_D_Diff'] = data['K'] - data['D']

    # ------------- 新增扩展指标（新增的指标函数调用） -------------
    data['MACD_Hist'] = compute_MACD_histogram(data['close'])
    ichimoku = compute_ichimoku(data['high'], data['low'], data['close'])
    data['Ichimoku_Tenkan'] = ichimoku['tenkan_sen']
    data['Ichimoku_Kijun'] = ichimoku['kijun_sen']
    data['Ichimoku_SpanA'] = ichimoku['senkou_span_a']
    data['Ichimoku_SpanB'] = ichimoku['senkou_span_b']
    data['Ichimoku_Chikou'] = ichimoku['chikou_span']
    data['Coppock'] = compute_coppock_curve(data['close'])
    data['Chaikin_Vol'] = compute_chaikin_volatility(data['high'], data['low'], period=10, ma_period=10)
    if 'volume' in data.columns:
        data['EOM'] = compute_ease_of_movement(data['high'], data['low'], data['volume'], period=14)
    else:
        data['EOM'] = np.nan
    data['Vortex_Pos'], data['Vortex_Neg'] = compute_vortex_indicator(data['high'], data['low'], data['close'], period=14)
    data['Annualized_Vol'] = compute_annualized_volatility(data['close'], period=10, trading_days=252)
    data['Fisher'] = compute_fisher_transform(data['close'], period=10)
    data['CMO_14'] = compute_CMO(data['close'], period=14)
    data['RSI_14'] = compute_RSI(data['close'], period=14)
    # ------------------ 6) 检查关键列 ------------------
    required_cols = [
        'close_MA5_Diff', 'MA5_MA20_Diff', 'RSI_Signal', 'MACD_Diff',
        'Bollinger_Position', 'K_D_Diff'
    ]
    for col in required_cols:
        if col not in data.columns:
            raise ValueError(f"列 {col} 未被创建，请检查数据和计算步骤。")
    # ------------------ 6) 构建基础因子 base_features 列表 ------------------
    print("构建基础因子列表 base_features...")
    base_features = [
        'close_MA5_Diff', 'MA5_MA20_Diff', 'RSI_Signal', 'MACD_Diff',
        'K_D_Diff', 'Cross_MA5_Count', 'volume_Spike_Count', 'CCI_20',
        'Williams_%R_14',  'OBV','VWAP', 'ZScore_20', 'Plus_DI', 'Minus_DI',
        'ADX_14','Bollinger_Width', 'Slope_MA5', 'volume_Change',
        'Price_Mean_Diff','high_Mean_Diff','low_Mean_Diff','Ultimate_Osc','Chaikin_Osc','PPO',
        'KST','KST_signal','KAMA_10','RSI_14',
        # 新增基础特征：5日/20日均线、成交量、涨跌幅
        'MA_5', 'MA_20', 'pct_change',
        # 新增基础特征：原始OHLC
        'open', 'high', 'low', 'close'
    ]


    if 'volume' in data.columns:
        base_features.append('volume')

    # 如果用户指定了特征,则只保留用户选择的特征
    # 注意: selected_features 为 None 或空列表时,使用全部特征
    if selected_features and len(selected_features) > 0:
        # 转换为小写进行匹配
        selected_features_lower = [f.lower() for f in selected_features]
        filtered_features = [f for f in base_features if f.lower() in selected_features_lower]
        if filtered_features:
            base_features = filtered_features
            print(f"用户选择了 {len(base_features)} 个特征")
        else:
            print(f"警告: 用户选择的特征不在base_features中,使用全部 {len(base_features)} 个特征")
    
    # ★ 将 generate_features 里新增的列也并入 base_features
    #   这样后面方差过滤 & 相关性过滤也会考虑它们
    #base_features = list(set(base_features).union(new_cols))

    print(f"初始 base_features 数量: {len(base_features)}")
  
    # ------------------ 9) 方差过滤 ------------------
    print("对基础特征进行方差过滤...")
    try:
        if not base_features:
            raise ValueError("base_features 是空的，无法进行方差过滤")

        X_base = data[base_features].replace([np.inf, -np.inf], np.nan).fillna(0)

        if X_base.empty:
            raise ValueError("X_base 是空的，data 可能没有行数据")

        selector = VarianceThreshold(threshold=0.0001)
        selector.fit(X_base)

        filtered_features = [f for f, s in zip(base_features, selector.get_support()) if s]
        print(f"方差过滤后剩余特征数：{len(filtered_features)}（从{len(base_features)}减少）")
        base_features = filtered_features
    except Exception as e:
        print(f"方差过滤出错：{e}")


  
    # ------------------ 10) 相关性过滤 ------------------
    print("对基础特征进行相关性过滤...")
    corr_matrix = data[base_features].corr().abs()
    upper = corr_matrix.where(np.triu(np.ones(corr_matrix.shape), k=1).astype(bool))
    to_drop = [column for column in upper.columns if any(upper[column] > 0.95)]
    base_features = [f for f in base_features if f not in to_drop]
    print(f"相关性过滤后剩余特征数：{len(base_features)}")
    
    # ------------------ 11) 若 mixture_depth > 1, 生成混合因子 ------------------
    print(f"生成混合因子, mixture_depth = {mixture_depth}")
    if mixture_depth > 1:
        operators = ['+', '-', '*', '/']
        mixed_features = base_features.copy()
        current_depth_features = base_features.copy()

        for depth in range(2, mixture_depth + 1):
            print(f"生成深度 {depth} 的混合因子...")
            new_features = []
            feature_pairs = combinations(current_depth_features, 2)
            for f1, f2 in feature_pairs:
                for op in operators:
                    new_feature_name = f'({f1}){op}({f2})_d{depth}'
                    try:
                        if op == '+':
                            data[new_feature_name] = data[f1] + data[f2]
                        elif op == '-':
                            data[new_feature_name] = data[f1] - data[f2]
                        elif op == '*':
                            data[new_feature_name] = data[f1] * data[f2]
                        elif op == '/':
                            denom = data[f2].replace(0, np.nan)
                            data[new_feature_name] = data[f1] / denom
                        data[new_feature_name] = data[new_feature_name].replace([np.inf, -np.inf], np.nan).fillna(0)
                        new_features.append(new_feature_name)
                    except Exception as e:
                        print(f"无法计算特征 {new_feature_name}，错误：{e}")

            # 对新因子先做一次方差过滤 & 高相关过滤
            if new_features:
                X_new = data[new_features].fillna(0)
                sel_new = VarianceThreshold(threshold=0.0001)
                sel_new.fit(X_new)
                new_features = [nf for nf, s in zip(new_features, sel_new.get_support()) if s]
                if len(new_features) > 1:
                    corr_matrix_new = data[new_features].corr().abs()
                    upper_new = corr_matrix_new.where(np.triu(np.ones(corr_matrix_new.shape), k=1).astype(bool))
                    to_drop_new = [col for col in upper_new.columns if any(upper_new[col] > 0.95)]
                    new_features = [f for f in new_features if f not in to_drop_new]

            mixed_features.extend(new_features)
            current_depth_features = new_features.copy()

        # 现在 all_features = 基础 + 混合
        all_features = mixed_features.copy()

        # 最后做 PCA 降维
        print("进行 PCA 降维...")
        pca_components = min(100, len(all_features))
        pca = PCA(n_components=pca_components)
        X_mixed = data[all_features].fillna(0).values
        X_mixed_pca = pca.fit_transform(X_mixed)

        pca_feature_names = [f'PCA_{i}' for i in range(pca_components)]
        for i in range(pca_components):
            data[pca_feature_names[i]] = X_mixed_pca[:, i]

        all_features = pca_feature_names
    else:
        all_features = base_features.copy()

    # ------------------ 12) 检查关键列 ------------------
    
    #  提取指定时间范围内的数据子集
    
    data_updata = data.loc[data.index >= '2021-01-01', ['close', 'volume', 'high', 'low']].copy()

    # 计算新特征
    data_updata['OBV'] = compute_OBV(data_updata['close'], data_updata['volume'])
    data_updata['VWAP'] = compute_VWAP(data_updata['high'], data_updata['low'], data_updata['close'], data_updata['volume'])
    data_updata['MA_200'] = data_updata['close'].rolling(window=200).mean()
    data_updata['Chaikin_Osc'] = compute_chaikin_oscillator(data['high'], data['low'], data['close'], data['volume'], short_period=3, long_period=10)
    #替换原始 data 中对应位置的列
    data.loc[data_updata.index, ['OBV', 'VWAP','MA_200','Chaikin_Osc']] = data_updata[['OBV', 'VWAP','MA_200','Chaikin_Osc']]
    
    # ------------------ 11) 删除缺失值 & 返回 ------------------
    data.index.name = 'date_index'
    #print(f"数据预处理前长度: {initial_length}, 数据预处理后长度: {final_length}")
    #all_features = selected_func_names+selected_system
    print(f"最终特征数量：{len(all_features)}")
    #统一小写
    all_features = [f.lower() for f in all_features]
    data.columns = data.columns.str.lower()
    return data, all_features



#时间序列强化采样
#@st.cache_data
def create_pos_neg_sequences_by_consecutive_labels(X, y, negative_ratio=1.0, adjacent_steps=5):
    pos_idx = np.where(y == 1)[0]
    pos_segments = []
    if len(pos_idx) > 0:
        start = pos_idx[0]
        for i in range(1, len(pos_idx)):
            if pos_idx[i] != pos_idx[i-1] + 1:
                pos_segments.append(np.arange(start, pos_idx[i-1]+1))
                start = pos_idx[i]
        pos_segments.append(np.arange(start, pos_idx[-1]+1))
    pos_features = np.array([X[seg].mean(axis=0) for seg in pos_segments])
    pos_labels = np.ones(len(pos_features), dtype=np.int64)
    
    neg_features = []
    neg_count = int(len(pos_features) * negative_ratio)
    for seg in pos_segments:
        start_neg = seg[-1] + 1
        end_neg = seg[-1] + adjacent_steps
        if end_neg < X.shape[0] and np.all(y[start_neg:end_neg+1] == 0):
            neg_features.append(X[start_neg:end_neg+1].mean(axis=0))
        if len(neg_features) >= neg_count:
            break

    if len(neg_features) < neg_count:
        neg_idx = np.where(y == 0)[0]
        neg_segments = []
        if len(neg_idx) > 0:
            start = neg_idx[0]
            for i in range(1, len(neg_idx)):
                if neg_idx[i] != neg_idx[i-1] + 1:
                    neg_segments.append(np.arange(start, neg_idx[i-1]+1))
                    start = neg_idx[i]
            neg_segments.append(np.arange(start, neg_idx[-1]+1))
            for seg in neg_segments:
                if len(seg) >= adjacent_steps:
                    neg_features.append(X[seg[:adjacent_steps]].mean(axis=0))
                if len(neg_features) >= neg_count:
                    break
    neg_features = np.array(neg_features[:neg_count])
    neg_labels = np.zeros(len(neg_features), dtype=np.int64)
    features = np.concatenate([pos_features, neg_features], axis=0)
    labels = np.concatenate([pos_labels, neg_labels], axis=0)

    return features, labels

#L正则化进行特征选择
def feature_selection(X, y, method="lasso", threshold=0.01):
    if method == "lasso":
        # 使用Lasso进行特征选择
        lasso = LogisticRegression(penalty='l1', solver='saga')
        lasso.fit(X, y)
        selected_features = [f for i, f in enumerate(X.columns) if abs(lasso.coef_[0][i]) > threshold]
    elif method == "random_forest":
        # 使用随机森林计算特征重要性
        rf = RandomForestClassifier(n_estimators=100)
        rf.fit(X, y)
        feature_importances = rf.feature_importances_
        selected_features = [X.columns[i] for i in range(len(feature_importances)) if feature_importances[i] > threshold]
    else:
        raise ValueError("Unsupported feature selection method: Choose 'lasso' or 'random_forest'.")
    
    return selected_features

