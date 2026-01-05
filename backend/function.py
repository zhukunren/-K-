"""
===============================================================================
技术指标计算函数库 & 数据获取模块
===============================================================================

【文件说明】
本文件包含两大部分功能:
1. 技术指标计算函数(70+个函数)
2. 股票/指数数据获取函数(Tushare API & MySQL)

【技术指标函数列表】

一、趋势类指标 (Trend Indicators)
- compute_RSI(): 相对强弱指数 - 判断超买超卖
- compute_MACD(): MACD指标 - 趋势判断和买卖信号
- compute_SMA(): 简单移动平均线
- compute_EMA(): 指数移动平均线
- compute_KAMA(): 自适应移动平均线

二、动量类指标 (Momentum Indicators)
- compute_momentum(): 动量指标 - 价格变化速度
- compute_ROC(): 变化率指标 - 价格变化百分比
- compute_CCI(): 商品通道指标
- compute_williams_r(): 威廉指标 - 超买超卖判断
- compute_KD/KDJ(): 随机指标
- compute_Ultimate_Osc(): 终极振荡器
- compute_CMO(): 钱德动量摆动指标

三、波动率类指标 (Volatility Indicators)
- compute_Bollinger_Bands(): 布林带 - 价格波动区间
- compute_ATR(): 平均真实波幅 - 波动性度量
- compute_volatility(): 历史波动率
- compute_chaikin_volatility(): 蔡金波动率

四、趋势强度指标 (Trend Strength)
- compute_ADX(): 平均趋向指数 - 趋势强度
- compute_DMI(): 方向性运动指数
- compute_vortex_indicator(): 涡流指标

五、成交量类指标 (Volume Indicators)
- compute_OBV(): 能量潮 - 资金流向
- compute_VWAP(): 成交量加权均价 - 机构成本
- compute_MFI(): 资金流量指标 - 带量RSI
- compute_CMF(): 蔡金资金流
- compute_chaikin_oscillator(): 蔡金振荡器
- compute_AccumulationDistribution(): 累积派发线
- compute_ease_of_movement(): 简易波动指标

六、其他技术指标
- compute_zscore(): Z分数标准化
- compute_TRIX(): 三重指数平滑均线
- compute_PPO(): 价格振荡百分比
- compute_DPO(): 去趋势价格振荡器
- compute_KST(): Know Sure Thing动量指标
- compute_ichimoku(): 一目均衡云图
- compute_coppock_curve(): 库博克曲线
- compute_fisher_transform(): 费舍尔变换
- compute_parabolic_sar(): 抛物线SAR

七、形态识别函数
- identify_high_peaks(): 识别局部高点
- identify_low_troughs(): 识别局部低点

【数据获取函数】

1. read_day_from_tushare()
   功能: 从Tushare Pro API获取股票/指数日线数据
   参数:
   - symbol_code: 股票代码(如"000001.SZ")
   - symbol_type: 'stock'或'index'
   - start_date: 起始日期(YYYYMMDD格式)
   - end_date: 结束日期(YYYYMMDD格式)
   返回: DataFrame包含OHLCV数据和基本面指标

2. read_day_from_mysql()
   功能: 从MySQL数据库读取本地缓存数据
   参数: 同上
   返回: DataFrame

3. read_day_fromtdx()
   功能: 从通达信DAY文件读取数据
   参数:
   - file_path: 通达信数据目录
   - stock_code_tdx: 通达信格式代码
   返回: DataFrame

4. select_time()
   功能: 按时间范围筛选数据
   参数:
   - df: 数据DataFrame
   - start_time: 起始时间(YYYYMMDD)
   - end_time: 结束时间(YYYYMMDD)
   返回: 筛选后的DataFrame

【使用示例】

# 计算RSI指标
rsi = compute_RSI(df['close'], period=14)

# 计算MACD指标
macd, signal = compute_MACD(df['close'])

# 获取股票数据
df = read_day_from_tushare(
    symbol_code="000001.SZ",
    symbol_type="stock",
    start_date="20220101",
    end_date="20241231"
)

# 计算布林带
upper, middle, lower = compute_Bollinger_Bands(df['close'])

【技术指标原理说明】

RSI (Relative Strength Index):
- 计算涨跌幅度的相对强度
- 范围0-100,>70超买,<30超卖
- 常用周期14天

MACD (Moving Average Convergence Divergence):
- 快慢EMA的差值
- 金叉死叉判断买卖点
- 柱状图反映动量变化

OBV (On-Balance Volume):
- 上涨日成交量为正,下跌日为负
- 累积成交量反映资金流向
- OBV上升通常预示价格上涨

【依赖库】
- pandas, numpy: 数据处理
- tushare: Tushare Pro API
- pymysql, sqlalchemy: MySQL数据库连接

【配置要求】
需要配置Tushare Token:

【作者】技术指标函数库
【更新日期】2024-10
===============================================================================
"""
import numpy as np
import pandas as pd
import os
import warnings
from pathlib import Path
from typing import Dict, Tuple
import tushare as ts
from concurrent.futures import ThreadPoolExecutor, as_completed
from pymysql.err import OperationalError, ProgrammingError
from pymysql import connect
from sqlalchemy import create_engine
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, time as dt_time
#pro = ts.pro_api()

# --- Tushare credential handling and caching ---
# 优先环境变量 -> 本地文件 backend/.tushare_token -> 无则警告
_TUSHARE_TOKEN = os.getenv("TUSHARE_TOKEN")
if not _TUSHARE_TOKEN:
    token_file = Path(__file__).resolve().parent / ".tushare_token"
    if token_file.exists():
        _TUSHARE_TOKEN = token_file.read_text(encoding="utf-8").strip()

if _TUSHARE_TOKEN:
    ts.set_token(_TUSHARE_TOKEN)
else:
    warnings.warn(
        "未配置 Tushare token。请设置环境变量 TUSHARE_TOKEN 或在 backend/.tushare_token 写入 token 以启用在线数据下载。",
        RuntimeWarning,
    )

_TUSHARE_CACHE: Dict[Tuple[str, str, str, str], pd.DataFrame] = {}
_TUSHARE_CACHE_TS: Dict[Tuple[str, str, str, str], datetime] = {}

# When the requested end_date is "open ended" (>= today), cached market data should be refreshed
# after market close so next-day predictions are not stuck on yesterday.
_TUSHARE_CACHE_MIN_REFRESH_SECONDS = int(os.getenv("TUSHARE_CACHE_MIN_REFRESH_SECONDS", "600"))  # 10 min
_TUSHARE_CACHE_REFRESH_AFTER = dt_time(16, 30)


def clear_tushare_cache() -> None:
    """Clear the in-memory cache used by read_day_from_tushare."""
    _TUSHARE_CACHE.clear()
    _TUSHARE_CACHE_TS.clear()


def _parse_yyyymmdd(value: object) -> object:
    """Parse YYYYMMDD to date; return None if not parseable."""
    if value is None:
        return None
    s = str(value).strip()
    if not (len(s) == 8 and s.isdigit()):
        return None
    try:
        return datetime.strptime(s, "%Y%m%d").date()
    except Exception:
        return None


def _should_refresh_tushare_cache(
    *,
    df: pd.DataFrame,
    end_date: object,
    fetched_at: datetime | None,
    now: datetime,
) -> bool:
    """
    Decide whether a cached Tushare response should be refreshed.

    Heuristic:
    - Only refresh when caller asks for "up to today" (end_date >= today).
    - Refresh if cache is >=2 days behind (covers weekends/holidays/long-running processes).
    - Refresh after 16:30 when cache is 1 day behind (market close update window).
    - Throttle refresh attempts to avoid repeated API calls.
    """
    if df is None or df.empty:
        return False

    requested_end = _parse_yyyymmdd(end_date)
    today = now.date()
    if requested_end is None or requested_end < today:
        return False

    if "trade_date" not in df.columns:
        return False

    try:
        last_trade = pd.to_datetime(df["trade_date"]).max()
        if pd.isna(last_trade):
            return False
        last_trade_date = last_trade.date()
    except Exception:
        return False

    day_diff = (today - last_trade_date).days
    if day_diff < 1:
        return False

    if fetched_at is not None:
        if (now - fetched_at).total_seconds() < _TUSHARE_CACHE_MIN_REFRESH_SECONDS:
            return False

    if day_diff >= 2:
        return True

    # day_diff == 1
    return now.time() >= _TUSHARE_CACHE_REFRESH_AFTER

# ---------- 技术指标计算函数 ----------

def compute_RSI(series, period=14):
    """
    RSI (Relative Strength Index) - 相对强弱指数
    衡量价格上涨和下跌的速度和幅度，用于判断超买或超卖状态。
    参数:
    - series: 序列 (如收盘价)
    - period: 计算周期
    返回:
    - RSI值序列
    
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))
    return rsi

def compute_MACD(series, fast_period=12, slow_period=26, signal_period=9):
    """
    MACD (Moving Average Convergence Divergence) - 指数平滑异同移动平均线
    衡量短期和长期价格趋势之间的差异。
    参数:
    - series: 序列 (如收盘价)
    - fast_period: 快速均线周期
    - slow_period: 慢速均线周期
    - signal_period: 信号线周期
    返回:
    - MACD值, 信号线值
    """
    fast_ema = series.ewm(span=fast_period, adjust=False).mean()
    slow_ema = series.ewm(span=slow_period, adjust=False).mean()
    macd = fast_ema - slow_ema
    signal = macd.ewm(span=signal_period, adjust=False).mean()
    return macd, signal

def calculate_macd(df, short=8, long=17, signal=6):
    """
    计算MACD指标：DIF 和 DEA（使用参数 8,17,6）

    参数：
    df : DataFrame，必须包含 'close' 列。
    short : int，短期EMA周期，默认8。
    long : int，长期EMA周期，默认17。
    signal : int，DEA（信号线）的EMA周期，默认6。

    返回：
    DataFrame，新增 'DIF' 和 'DEA' 列。
    """
    df = df.copy()

    # 计算EMA
    df['EMA_short'] = df['close'].ewm(span=short, adjust=False).mean()
    df['EMA_long'] = df['close'].ewm(span=long, adjust=False).mean()
    
    # DIF = EMA_short - EMA_long
    df['DIF'] = df['EMA_short'] - df['EMA_long']
    
    # DEA = DIF的 signal 日 EMA
    df['DEA'] = df['DIF'].ewm(span=signal, adjust=False).mean()
    
    # 可选：MACD柱线
    # df['MACD'] = 2 * (df['DIF'] - df['DEA'])

    # 删除中间计算列（可选）
    df.drop(columns=['EMA_short', 'EMA_long'], inplace=True)

    return df

def calculate_adx(df, period=14):
    """
    计算ADX指标（Average Directional Index）

    参数：
    df : DataFrame，必须包含 'high', 'low', 'close' 列。
    period : int，ADX的平滑周期，通常为14。

    返回：
    DataFrame，新增 '+DI', '-DI', 'ADX' 列。
    """
    df = df.copy()

    # 前一日的值
    df['prev_high'] = df['high'].shift(1)
    df['prev_low'] = df['low'].shift(1)
    df['prev_close'] = df['close'].shift(1)

    # TR: True Range
    df['tr1'] = df['high'] - df['low']
    df['tr2'] = abs(df['high'] - df['prev_close'])
    df['tr3'] = abs(df['low'] - df['prev_close'])
    df['TR'] = df[['tr1', 'tr2', 'tr3']].max(axis=1)

    # +DM / -DM
    df['+DM'] = df['high'] - df['prev_high']
    df['-DM'] = df['prev_low'] - df['low']
    df['+DM'] = df['+DM'].where((df['+DM'] > df['-DM']) & (df['+DM'] > 0), 0.0)
    df['-DM'] = df['-DM'].where((df['-DM'] > df['+DM']) & (df['-DM'] > 0), 0.0)

    # 平滑 TR, +DM, -DM
    tr_smooth = df['TR'].rolling(window=period).sum()
    plus_dm_smooth = df['+DM'].rolling(window=period).sum()
    minus_dm_smooth = df['-DM'].rolling(window=period).sum()

    # +DI / -DI
    df['+DI'] = 100 * plus_dm_smooth / tr_smooth
    df['-DI'] = 100 * minus_dm_smooth / tr_smooth

    # DX
    df['DX'] = 100 * abs(df['+DI'] - df['-DI']) / (df['+DI'] + df['-DI'])

    # ADX
    df['ADX'] = df['DX'].rolling(window=period).mean()

    # 清理中间列（可选）
    df.drop(columns=['prev_high', 'prev_low', 'prev_close', 'tr1', 'tr2', 'tr3', 'TR', '+DM', '-DM', 'DX'], inplace=True)

    return df

def compute_Bollinger_Bands(series, period=20, num_std=2):
    """
    Bollinger Bands - 布林带
    基于移动平均和标准差构造的价格波动区间。
    参数:
    - series: 序列 (如收盘价)
    - period: 移动平均周期
    - num_std: 标准差倍数
    返回:
    - 上轨, 中轨, 下轨
    """
    rolling_mean = series.rolling(window=period).mean()
    rolling_std = series.rolling(window=period).std()
    upper_band = rolling_mean + (rolling_std * num_std)
    lower_band = rolling_mean - (rolling_std * num_std)
    return upper_band, rolling_mean, lower_band

def compute_KD(high, low, close, period=14):
    """
    KD指标 (KDJ的基础)
    衡量当前价格相对于过去高点和低点的位置。
    参数:
    - high: 最高价序列
    - low: 最低价序列
    - close: 收盘价序列
    - period: 计算周期
    返回:
    - K值, D值
    """
    low_min = low.rolling(window=period).min()
    high_max = high.rolling(window=period).max()
    rsv = (close - low_min) / (high_max - low_min) * 100
    K = rsv.ewm(com=2).mean()
    D = K.ewm(com=2).mean()
    return K, D

def compute_KDJ(high: pd.Series,
                low: pd.Series,
                close: pd.Series,
                period: int = 9,
                k_smooth: int = 3,
                d_smooth: int = 3) -> tuple[pd.Series, pd.Series, pd.Series]:
    """
    正确计算 KDJ 指标（含 RSV -> K -> D -> J）
    """
    low_min = low.rolling(window=period, min_periods=1).min()
    high_max = high.rolling(window=period, min_periods=1).max()
    rsv = (close - low_min) / (high_max - low_min) * 100

    K = pd.Series(index=close.index, dtype='float64')
    D = pd.Series(index=close.index, dtype='float64')
    K.iloc[0] = 50
    D.iloc[0] = 50

    for i in range(1, len(close)):
        K.iloc[i] = (1 - 1/k_smooth) * K.iloc[i - 1] + (1/k_smooth) * rsv.iloc[i]
        D.iloc[i] = (1 - 1/d_smooth) * D.iloc[i - 1] + (1/d_smooth) * K.iloc[i]

    J = 3 * K - 2 * D
    return K, D, J

def compute_ATR(high, low, close, period=14):
    """
    ATR (Average True Range) - 平均真实波幅
    衡量价格波动范围的指标。
    参数:
    - high: 最高价序列
    - low: 最低价序列
    - close: 收盘价序列
    - period: 计算周期
    返回:
    - ATR值序列
    """
    hl = high - low
    hc = (high - close.shift()).abs()
    lc = (low - close.shift()).abs()
    tr = hl.combine(hc, max).combine(lc, max)
    atr = tr.rolling(window=period).mean()
    return atr

def compute_ADX(high, low, close, period=14):
    """
    ADX (Average Directional Index) - 平均趋向指数
    衡量趋势强度的指标。
    参数:
    - high: 最高价序列
    - low: 最低价序列
    - close: 收盘价序列
    - period: 计算周期
    返回:
    - +DI, -DI, ADX值
    """
    up_move = high.diff()
    down_move = low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * (-down_move)

    hl = high - low
    hc = (high - close.shift()).abs()
    lc = (low - close.shift()).abs()
    tr = hl.combine(hc, max).combine(lc, max)
    tr_sum = tr.rolling(window=period).sum()

    plus_di = 100 * (plus_dm.rolling(window=period).sum() / tr_sum)
    minus_di = 100 * (minus_dm.rolling(window=period).sum() / tr_sum)
    dx = 100 * ((plus_di - minus_di).abs() / (plus_di + minus_di))
    adx = dx.rolling(window=period).mean()
    return plus_di, minus_di, adx

def compute_CCI(high, low, close, period=20):
    """
    CCI (Commodity Channel Index) - 商品通道指标
    衡量价格偏离其统计均值的程度。
    参数:
    - high: 最高价序列
    - low: 最低价序列
    - close: 收盘价序列
    - period: 计算周期
    返回:
    - CCI值序列
    """
    tp = (high + low + close) / 3
    ma = tp.rolling(window=period).mean()
    md = (tp - ma).abs().rolling(window=period).mean()
    cci = (tp - ma) / (0.015 * md)
    return cci

def compute_momentum(series, period=10):
    """
    Momentum - 动量指标
    衡量当前价格相对于过去N天价格的变化幅度，反映价格变化的速度和方向。
    参数:
    - series: 时间序列 (如收盘价)
    - period: 计算周期 (默认10)
    返回:
    - 动量值序列
    """
    return series.diff(period)

def compute_ROC(series, period=10):
    """
    ROC (Rate of Change) - 变化率指标
    衡量当前价格相对于过去N天价格的变化百分比，用于反映趋势的强弱。
    参数:
    - series: 时间序列 (如收盘价)
    - period: 计算周期 (默认10)
    返回:
    - ROC值序列（百分比）
    """
    return series.pct_change(period) * 100

def compute_volume_change(volume, period=10):
    """
    Volume Change - 成交量变化率
    衡量当前成交量相对于过去N天成交量的变化比例，用于捕捉市场活跃度的变化。
    参数:
    - volume: 成交量序列
    - period: 计算周期 (默认10)
    返回:
    - 成交量变化率序列
    """
    return volume.diff(period) / volume.shift(period)

def compute_VWAP(high, low, close, volume):
    """
    VWAP (Volume Weighted Average Price) - 成交量加权平均价
    衡量市场的平均成交成本，常用于判断价格的合理区间。
    参数:
    - high: 最高价序列
    - low: 最低价序列
    - close: 收盘价序列
    - volume: 成交量序列
    返回:
    - VWAP值序列
    """
    typical_price = (high + low + close) / 3
    vwap = (typical_price * volume).cumsum() / volume.cumsum()
    return vwap

def compute_zscore(series, period=20):
    """
    Z-Score - 标准分数
    衡量当前值相对于过去N天均值的标准化偏差，反映价格的异常程度。
    参数:
    - series: 时间序列 (如收盘价)
    - period: 计算周期 (默认20)
    返回:
    - Z-Score值序列
    """
    mean = series.rolling(window=period).mean()
    std = series.rolling(window=period).std()
    return (series - mean) / std

def compute_volatility(series, period=10):
    """
    Volatility - 波动率
    衡量价格在过去N天的波动幅度，通常以标准差为度量。
    参数:
    - series: 时间序列 (如收盘价的收益率)
    - period: 计算周期 (默认10)
    返回:
    - 波动率序列
    """
    return series.pct_change().rolling(window=period).std()

def compute_OBV(close, volume):
    """
    OBV (On-Balance Volume) - 平衡成交量
    通过成交量的累积变化来衡量买卖力量，从而判断价格趋势的强弱。
    参数:
    - close: 收盘价序列
    - volume: 成交量序列
    返回:
    - OBV值序列
    用法:
    - OBV值随时间上升表示资金流入市场，可能预示价格上涨。
    - OBV值下降表示资金流出市场，可能预示价格下跌。
    """
    # 计算价格变化方向 (+1, 0, -1)
    direction = np.sign(close.diff())
    direction.iloc[0] = 0  # 第一天无法计算变化方向，设为0
    # 根据方向累积成交量
    obv = (volume * direction).fillna(0).cumsum()
    return obv

def compute_williams_r(high, low, close, period=14):
    """
    Williams %R - 威廉指标
    衡量当前收盘价相对于过去N天的高点和低点的位置，常用于超买和超卖状态的判断。
    参数:
    - high: 最高价序列
    - low: 最低价序列
    - close: 收盘价序列
    - period: 计算周期 (默认14)
    返回:
    - Williams %R值序列
    用法:
    - %R接近-100: 表示超卖区域，可能出现反弹。
    - %R接近0: 表示超买区域，可能出现回调。
    """
    # 计算过去N天的最高点和最低点
    hh = high.rolling(window=period).max()
    ll = low.rolling(window=period).min()
    # 计算威廉指标
    wr = -100 * ((hh - close) / (hh - ll))
    return wr

def compute_MFI(high, low, close, volume, period=14):
    """
    MFI (Money Flow Index)
    类似于RSI，但考虑成交量。
    """
    tp = (high + low + close) / 3
    mf = tp * volume
    positive_flow = mf.where(tp > tp.shift(), 0)
    negative_flow = mf.where(tp < tp.shift(), 0)
    positive_sum = positive_flow.rolling(window=period).sum()
    negative_sum = negative_flow.rolling(window=period).sum()
    mfi = 100 * (positive_sum / (positive_sum + negative_sum))
    return mfi

def compute_CMF(high, low, close, volume, period=20):
    """
    CMF (Chaikin Money Flow)
    衡量资金流入流出强度。
    """
    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    mf_volume = mf_multiplier * volume
    cmf = mf_volume.rolling(window=period).sum() / volume.rolling(window=period).sum()
    return cmf

def compute_TRIX(series, period=15):
    """
    TRIX (Triple Exponential Average)
    衡量价格变化的速度，三重平滑的EMA变化率。
    """
    ema1 = series.ewm(span=period, adjust=False).mean()
    ema2 = ema1.ewm(span=period, adjust=False).mean()
    ema3 = ema2.ewm(span=period, adjust=False).mean()
    trix = (ema3.diff() / ema3.shift()) * 100
    return trix

def compute_ultimate_oscillator(high, low, close, short_period=7, medium_period=14, long_period=28):
    """
    Ultimate Oscillator (UO)
    综合不同周期的摆动值衡量市场动能。
    """
    bp = close - np.minimum(low.shift(1), close.shift(1))
    tr = np.maximum(high - low, 
                    np.maximum(abs(high - close.shift(1)), abs(low - close.shift(1))))
    avg7 = bp.rolling(short_period).sum() / tr.rolling(short_period).sum()
    avg14 = bp.rolling(medium_period).sum() / tr.rolling(medium_period).sum()
    avg28 = bp.rolling(long_period).sum() / tr.rolling(long_period).sum()

    uo = 100 * ((4 * avg7) + (2 * avg14) + avg28) / (4 + 2 + 1)
    return uo

def compute_chaikin_oscillator(high, low, close, volume, short_period=3, long_period=10):
    """
    Chaikin Oscillator
    基于ADL(累积/派发线)的MACD式指标。
    """
    adl = compute_ADL_line(high, low, close, volume)
    short_ema = adl.ewm(span=short_period, adjust=False).mean()
    long_ema = adl.ewm(span=long_period, adjust=False).mean()
    cho = short_ema - long_ema
    return cho

def compute_ADL_line(high, low, close, volume):
    """
    ADL (Accumulation/Distribution Line)
    """
    mf_multiplier = ((close - low) - (high - close)) / (high - low)
    mf_multiplier = mf_multiplier.replace([np.inf, -np.inf], np.nan).fillna(0)
    mf_volume = mf_multiplier * volume
    adl = mf_volume.cumsum()
    return adl

def compute_PPO(series, fast_period=12, slow_period=26):
    """
    PPO (Percentage Price Oscillator)
    与MACD类似，只是输出为百分比。
    """
    fast_ema = series.ewm(span=fast_period, adjust=False).mean()
    slow_ema = series.ewm(span=slow_period, adjust=False).mean()
    ppo = (fast_ema - slow_ema) / slow_ema * 100
    return ppo

def compute_DPO(series, period=20):
    """
    DPO (Detrended Price Oscillator)
    去趋势价格振荡指标。
    """
    shifted = series.shift(int((period/2)+1))
    sma = series.rolling(window=period).mean()
    dpo = series - sma.shift(int((period/2)+1))
    return dpo

def compute_KST(series, r1=10, r2=15, r3=20, r4=30, sma1=10, sma2=10, sma3=10, sma4=15):
    """
    KST (Know Sure Thing)
    基于ROC的综合动量指标。
    """
    roc1 = series.pct_change(r1)*100
    roc2 = series.pct_change(r2)*100
    roc3 = series.pct_change(r3)*100
    roc4 = series.pct_change(r4)*100

    sma_roc1 = roc1.rolling(sma1).mean()
    sma_roc2 = roc2.rolling(sma2).mean()
    sma_roc3 = roc3.rolling(sma3).mean()
    sma_roc4 = roc4.rolling(sma4).mean()

    kst = sma_roc1 + 2*sma_roc2 + 3*sma_roc3 + 4*sma_roc4
    signal = kst.rolling(9).mean()
    return kst, signal

def compute_KAMA(series, n=10, pow1=2, pow2=30):
    """
    KAMA (Kaufman's Adaptive Moving Average)
    自适应移动平均
    """
    change = series.diff(n).abs()
    volatility = series.diff(1).abs().rolling(window=n).sum()
    er = change / volatility
    sc = (er * (2/(pow1+1)-2/(pow2+1)) + 2/(pow2+1))**2

    kama = series.copy()
    for i in range(n, len(series)):
        kama.iloc[i] = kama.iloc[i-1] + sc.iloc[i]*(series.iloc[i]-kama.iloc[i-1])
    return kama

import numpy as np
import pandas as pd

def compute_SMA(series, window):
    """
    简单移动平均线 (Simple Moving Average)
    
    参数:
      - series: 数值序列（例如收盘价）
      - window: 窗口长度
    
    返回:
      - 简单移动平均序列
    """
    return series.rolling(window=window, min_periods=1).mean()

def compute_EMA(series, span):
    """
    指数移动平均线 (Exponential Moving Average)
    
    参数:
      - series: 数值序列（例如收盘价）
      - span: EMA的窗口跨度
    
    返回:
      - 指数移动平均序列
    """
    return series.ewm(span=span, adjust=False).mean()

def compute_PercentageB(close, upper_band, lower_band):
    """
    计算Bollinger %B指标
    %B 指标反映收盘价在布林带中的位置，取值范围通常在0到1之间。
    
    参数:
      - close: 收盘价序列
      - upper_band: 上轨序列
      - lower_band: 下轨序列
      
    返回:
      - %B 值序列
    """
    band_range = upper_band - lower_band
    # 防止除零操作
    band_range = band_range.replace(0, np.nan)
    percent_b = (close - lower_band) / band_range
    return percent_b.fillna(0)

def compute_AccumulationDistribution(high, low, close, volume):
    """
    累积/派发线 (Accumulation/Distribution Line)
    A/D线综合考虑价格和成交量信息，用于反映资金流入/流出情况。
    
    参数:
      - high: 最高价序列
      - low: 最低价序列
      - close: 收盘价序列
      - volume: 成交量序列
      
    返回:
      - A/D线序列
    """
    # 计算资金流向因子
    denominator = (high - low)
    denominator = denominator.replace(0, np.nan)
    mfm = ((close - low) - (high - close)) / denominator  # Money Flow Multiplier
    mfm = mfm.fillna(0)
    mfv = mfm * volume  # Money Flow Volume
    return mfv.cumsum()

def compute_MoneyFlowIndex(high, low, close, volume, period=14):
    """
    资金流量指标 (Money Flow Index, MFI)
    MFI 综合价格与成交量信息，反映市场的资金流入和流出情况。
    
    参数:
      - high: 最高价序列
      - low: 最低价序列
      - close: 收盘价序列
      - volume: 成交量序列
      - period: 计算周期 (默认为14)
      
    返回:
      - MFI 序列
    """
    typical_price = (high + low + close) / 3
    money_flow = typical_price * volume
    
    positive_flow = money_flow.where(typical_price.diff() > 0, 0)
    negative_flow = money_flow.where(typical_price.diff() < 0, 0)
    
    positive_mf = positive_flow.rolling(window=period, min_periods=1).sum()
    negative_mf = negative_flow.rolling(window=period, min_periods=1).sum()
    
    mfi = 100 * positive_mf / (positive_mf + negative_mf)
    return mfi.fillna(50)  # 缺失值填充为50，中性水平

def compute_HighLow_Spread(high, low):
    """
    计算日内价差（High-Low Spread）
    
    参数:
      - high: 最高价序列
      - low: 最低价序列
      
    返回:
      - 价差序列（高点减去低点）
    """
    return high - low

def compute_PriceChannel(high, low, close, window=20):
    """
    价格通道 (Price Channel)
    价格通道通常由一定周期内的最高价和最低价构成，可用于捕捉价格突破情况。
    
    参数:
      - high: 最高价序列
      - low: 最低价序列
      - close: 收盘价序列
      - window: 周期 (默认为20)
      
    返回:
      - 一个DataFrame，包含通道上轨、下轨及中轨（中轨为均值）
    """
    upper_channel = high.rolling(window=window, min_periods=1).max()
    lower_channel = low.rolling(window=window, min_periods=1).min()
    middle_channel = (upper_channel + lower_channel) / 2
    return pd.DataFrame({
        'upper_channel': upper_channel,
        'middle_channel': middle_channel,
        'lower_channel': lower_channel
    })

def compute_RenkoSlope(close, bricks=3):
    """
    Renko 块趋势指标（简化版）
    根据价格区间构建Renko图中每个块的斜率，用于反映趋势力度。
    
    参数:
      - close: 收盘价序列
      - bricks: Renko块的价格差（默认为3）
      
    返回:
      - Renko斜率序列
    """
    price_diff = close.diff()
    # 当价格涨跌超过设定的砖块值时，记录为1或-1，否则为0
    renko = price_diff.apply(lambda x: 1 if x >= bricks else (-1 if x <= -bricks else 0))
    # 对renko序列进行累积或平滑处理，作为趋势力度指标
    return renko.rolling(window=5, min_periods=1).sum()

def compute_MACD_histogram(macd, signal):
    """
    MACD Histogram
    用于显示MACD与其信号线之间的差异。
    """
    return macd - signal

def compute_ema_crossover(series, short_period=12, long_period=26):
    """
    计算EMA交叉
    """
    short_ema = series.ewm(span=short_period, adjust=False).mean()
    long_ema = series.ewm(span=long_period, adjust=False).mean()
    crossover = short_ema > long_ema
    return crossover

def compute_average_gain_loss(series, period=14):
    """
    计算平均涨幅和跌幅
    """
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).fillna(0)
    loss = (-delta.where(delta < 0, 0)).fillna(0)
    avg_gain = gain.rolling(window=period).mean()
    avg_loss = loss.rolling(window=period).mean()
    return avg_gain, avg_loss

def compute_mfm(high, low, close):
    """
    计算资金流动乘数（MFM）
    """
    return ((close - low) - (high - close)) / (high - low)

def compute_RVI(series, period=14):
    """
    计算相对波动率指数（RVI）
    """
    log_returns = np.log(series / series.shift(1))
    rolling_mean = log_returns.rolling(window=period).mean()
    rolling_std = log_returns.rolling(window=period).std()
    rvi = rolling_mean / rolling_std
    return rvi

def compute_force_index(close, volume, period=1):
    """
    计算强势指数（Force Index）
    """
    force = close.diff(period) * volume
    return force

def compute_parabolic_sar(high, low, close, acceleration=0.02, maximum=0.2):
    """
    计算抛物线SAR
    """
    sar = close.copy()
    ep = high.max()
    af = acceleration
    for i in range(1, len(sar)):
        sar.iloc[i] = sar.iloc[i-1] + af * (ep - sar.iloc[i-1])
        if close.iloc[i] > sar.iloc[i]:
            ep = high.iloc[i]
            af = min(af + acceleration, maximum)
        else:
            ep = low.iloc[i]
            af = min(af + acceleration, maximum)
    return sar

def compute_DMI(high, low, close, period=14):
    """
    计算方向性运动指数（DMI）
    """
    up_move = high.diff()
    down_move = low.diff()
    plus_dm = ((up_move > down_move) & (up_move > 0)) * up_move
    minus_dm = ((down_move > up_move) & (down_move > 0)) * (-down_move)
    tr = high - low
    tr_sum = tr.rolling(window=period).sum()

    plus_di = 100 * (plus_dm.rolling(window=period).sum() / tr_sum)
    minus_di = 100 * (minus_dm.rolling(window=period).sum() / tr_sum)
    return plus_di, minus_di

def compute_smoothed_RSI(series, period=14):
    """
    计算平滑RSI
    """
    avg_gain, avg_loss = compute_average_gain_loss(series, period)
    rs = avg_gain / avg_loss
    smoothed_rsi = 100 - (100 / (1 + rs))
    return smoothed_rsi

def compute_std(series, period=20):
    """
    计算标准差
    """
    return series.rolling(window=period).std()

def compute_ema_trend(series, period=14):
    """
    计算基于EMA的趋势
    """
    ema = series.ewm(span=period, adjust=False).mean()
    trend = series - ema
    return trend

# ---------- 高低点识别函数 ----------

def identify_high_peaks(df, window=3):
    df = df.copy()
    # 定义滚动窗口大小
    win = 2 * window + 1

    # 使用 NumPy 快速计算滚动最大值
    rolling_max = df['High'].rolling(window=win, center=True).max()

    # 标记潜在高点（等于滚动窗口最大值）
    df['PotentialPeak'] = (df['High'] == rolling_max).astype(int)

    # 计算窗口内最大值出现的次数
    # 使用 NumPy 的布尔操作替代 apply 函数
    rolling_max_counts = (
        df['High']
        .rolling(window=win, center=True)
        .apply(lambda x: np.sum(x == np.max(x)), raw=True)
    )

    # 标记最终的高点：既是潜在高点，又是窗口中唯一最大值
    df['Peak'] = ((df['PotentialPeak'] == 1) & (rolling_max_counts == 1)).astype(int)

    # 清理临时列
    df.drop(columns=['PotentialPeak'], inplace=True)

    return df


def identify_low_troughs(df, window=3):
    df = df.copy()
    # 定义滚动窗口大小
    win = 2 * window + 1

    # 使用 NumPy 快速计算滚动最小值
    rolling_min = df['Low'].rolling(window=win, center=True).min()

    # 标记潜在低点（等于滚动窗口最小值）
    df['PotentialTrough'] = (df['Low'] == rolling_min).astype(int)

    # 计算窗口内最小值出现的次数
    rolling_min_counts = (
        df['Low']
        .rolling(window=win, center=True)
        .apply(lambda x: np.sum(x == np.min(x)), raw=True)
    )

    # 标记最终的低点：既是潜在低点，又是窗口中唯一最小值
    df['Trough'] = ((df['PotentialTrough'] == 1) & (rolling_min_counts == 1)).astype(int)

    # 清理临时列
    df.drop(columns=['PotentialTrough'], inplace=True)

    return df



# ---------- 数据读取与处理函数 ----------

def read_day_fromtdx(file_path, stock_code_tdx):
    """
    从通达信DAY文件中读取股票日线数据。
    参数:
    - file_path: 文件目录路径
    - stock_code_tdx: 股票代码 (如 "sh600000")
    返回:
    - 包含日期、开高低收、成交量等列的DataFrame
    """
    file_full_path = os.path.join(file_path, 'vipdoc', stock_code_tdx[:2].lower(), 'lday', f"{stock_code_tdx}.day")
    print(f"尝试读取文件: {file_full_path}")
    dtype = np.dtype([
        ('date', '<i4'),
        ('open', '<i4'),
        ('high', '<i4'),
        ('low', '<i4'),
        ('close', '<i4'),
        ('amount', '<f4'),
        ('volume', '<i4'),
        ('reserved', '<i4')
    ])
    if not os.path.exists(file_full_path):
        print(f"文件 {file_full_path} 不存在。")
        return pd.DataFrame()
    try:
        data = np.fromfile(file_full_path, dtype=dtype)
        print(f"读取了 {len(data)} 条记录。")
    except Exception as e:
        print(f"读取文件失败：{e}")
        return pd.DataFrame()
    if data.size == 0:
        print("文件为空。")
        return pd.DataFrame()
    df = pd.DataFrame({
        'date': pd.to_datetime(data['date'].astype(str), format='%Y%m%d', errors='coerce'),
        'Open': data['open'] / 100.0,
        'High': data['high'] / 100.0,
        'Low': data['low'] / 100.0,
        'Close': data['close'] / 100.0,
        'Amount': data['amount'],
        'Volume': data['volume'],
    })
    df = df.dropna(subset=['date'])
    df['TradeDate'] = df['date'].dt.strftime('%Y%m%d')
    df.set_index('date', inplace=True)
    print(f"创建了包含 {len(df)} 条记录的DataFrame。")
    return df

def select_time(df, start_time='20230101', end_time='20240910'):
    """
    根据指定的时间范围筛选数据。
    优先使用 'trade_date' 列筛选；如果不存在该列，则尝试用索引（须为 DatetimeIndex）。
    参数:
    - df: 包含日期信息的 DataFrame
    - start_time: 起始时间 (字符串, 格式 'YYYYMMDD')
    - end_time: 截止时间 (字符串, 格式 'YYYYMMDD')
    返回:
    - 筛选后的 DataFrame
    抛出:
    - KeyError: 当既没有 'trade_date' 列，且索引也不是 DatetimeIndex 时
    """
    import pandas as pd

    # 1. 转换字符串边界到 Timestamp
    try:
        start = pd.to_datetime(start_time, format='%Y%m%d')
        end   = pd.to_datetime(end_time,   format='%Y%m%d')
    except Exception as e:
        print(f"日期转换错误：{e}")
        return pd.DataFrame()

    # 2. 如果有 trade_date 列，则基于该列做布尔筛选
    if 'trade_date' in df.columns:
        df2 = df.copy()
        df2['trade_date'] = pd.to_datetime(df2['trade_date'])
        mask = (df2['trade_date'] >= start) & (df2['trade_date'] <= end)
        return df2.loc[mask]

    # 3. 否则，尝试用索引切片
    idx = df.index
    if not pd.api.types.is_datetime64_any_dtype(idx):
        raise KeyError("既不存在 'trade_date' 列，且索引不是 DatetimeIndex，无法按时间筛选。")
    # 索引已是 DatetimeIndex，直接切片
    return df.loc[start:end]


def compute_MACD_histogram(series, fast_period=12, slow_period=26, signal_period=9):
    """MACD直方图：返回 MACD 与 Signal 的差值"""
    macd, signal = compute_MACD(series, fast_period, slow_period, signal_period)
    return macd - signal

def compute_ichimoku(high, low, close, conversion_period=9, base_period=26, span_b_period=52, displacement=26):
    """
    Ichimoku云图指标，返回一个字典包含各条线：
      - tenkan_sen: 转换线 (Conversion Line)
      - kijun_sen: 基准线 (Base Line)
      - senkou_span_a: 领先A线 (Leading Span A)，向未来平移 displacement 个周期
      - senkou_span_b: 领先B线 (Leading Span B)，向未来平移 displacement 个周期
      - chikou_span: 滞后线 (Lagging Span)，向过去平移 displacement 个周期
    """
    tenkan_sen = (high.rolling(window=conversion_period).max() + low.rolling(window=conversion_period).min()) / 2
    kijun_sen = (high.rolling(window=base_period).max() + low.rolling(window=base_period).min()) / 2
    senkou_span_a = ((tenkan_sen + kijun_sen) / 2).shift(displacement)
    senkou_span_b = ((high.rolling(window=span_b_period).max() + low.rolling(window=span_b_period).min()) / 2).shift(displacement)
    chikou_span = close.shift(-displacement)
    return {
        'tenkan_sen': tenkan_sen,
        'kijun_sen': kijun_sen,
        'senkou_span_a': senkou_span_a,
        'senkou_span_b': senkou_span_b,
        'chikou_span': chikou_span
    }

def compute_coppock_curve(series, roc_period1=14, roc_period2=11, sma_period=10):
    """
    Coppock Curve 指标：常用于长周期底部确认
      计算方法：先计算两个不同周期的收益率，再取其和后平滑
    """
    roc1 = series.pct_change(roc_period1) * 100
    roc2 = series.pct_change(roc_period2) * 100
    coppock = (roc1 + roc2).rolling(window=sma_period).mean()
    return coppock

def compute_chaikin_volatility(high, low, period=10, ma_period=10):
    """
    Chaikin Volatility 指标：基于高低价差的移动平均变化率，反映波动性变化
      计算方法：先计算高低价差的简单移动平均，再取其周期性变化率（百分比）
    """
    hl_range = high - low
    sma_hl = hl_range.rolling(window=period).mean()
    volatility = sma_hl.pct_change(periods=ma_period) * 100
    return volatility

def compute_ease_of_movement(high, low, volume, period=14):
    """
    Ease of Movement (EOM) 指标：衡量价格变动与成交量之间的关系
      计算方法：先求中点价格的变化乘以价格幅度，再除以成交量，最后平滑处理
    """
    midpoint_diff = ((high + low) / 2).diff()
    price_range = high - low
    eom = midpoint_diff * price_range / volume.replace(0, 1e-9)
    return eom.rolling(window=period).mean()

def compute_vortex_indicator(high, low, close, period=14):
    """
    Vortex Indicator (VI) 指标：反映趋势的强度和方向
      返回两个系列：(VI+, VI-)
      其中：
        VI+ = rolling sum(|High - PrevLow|) / rolling sum(TR)
        VI- = rolling sum(|Low - PrevHigh|) / rolling sum(TR)
      TR 为真实波幅
    """
    tr = pd.concat([
        high - low, 
        (high - close.shift()).abs(), 
        (low - close.shift()).abs()
    ], axis=1).max(axis=1)
    vm_plus = (high - low.shift()).abs()
    vm_minus = (low - high.shift()).abs()
    sum_tr = tr.rolling(window=period).sum()
    vi_plus = vm_plus.rolling(window=period).sum() / sum_tr.replace(0, 1e-9)
    vi_minus = vm_minus.rolling(window=period).sum() / sum_tr.replace(0, 1e-9)
    return vi_plus, vi_minus

def compute_annualized_volatility(series, period=10, trading_days=252):
    """
    年化波动率：基于滚动收益率标准差转换
      通常年化波动率 = rolling volatility * sqrt(交易日数)
    """
    vol = compute_volatility(series, period)
    return vol * np.sqrt(trading_days)

def compute_fisher_transform(series, period=10):
    """
    Fisher Transform 指标：将数据转换为近似正态分布
      计算方法：先归一化到[-1,1]区间，再应用 Fisher 变换公式
    """
    min_val = series.rolling(window=period).min()
    max_val = series.rolling(window=period).max()
    x = 2 * ((series - min_val) / (max_val - min_val + 1e-9)) - 1
    x = x.clip(-0.999, 0.999)
    fisher = 0.5 * np.log((1 + x) / (1 - x))
    return fisher

def compute_CMO(series, period=14):
    """
    Chande Momentum Oscillator (CMO) 指标：
      计算方法：((正收益之和 - 负收益之和) / (正收益之和 + 负收益之和)) * 100
    """
    delta = series.diff()
    gain = delta.where(delta > 0, 0)
    loss = (-delta).where(delta < 0, 0)
    sum_gain = gain.rolling(window=period).sum()
    sum_loss = loss.rolling(window=period).sum()
    cmo = 100 * (sum_gain - sum_loss) / (sum_gain + sum_loss + 1e-9)
    return cmo


import tushare as ts
import pandas as pd


def read_day_from_tushare(symbol_code, symbol_type='stock',start_date='19920101', end_date='20261231'):
    """
    Fetch daily bar data via the Tushare Pro API.

    Args:
        symbol_code: Stock or index code such as '000001.SZ'.
        symbol_type: 'stock' or 'index' (case insensitive).
        start_date: Inclusive start date string in YYYYMMDD format.
        end_date: Inclusive end date string in YYYYMMDD format.

    Returns:
        pandas.DataFrame with day level OHLCV data (and fundamentals for stocks).
    """
    symbol_type = symbol_type.lower()
    assert symbol_type in ('stock', 'index'), "symbol_type must be 'stock' or 'index'"

    cache_key = (
        symbol_code,
        symbol_type,
        str(start_date) if start_date is not None else '',
        str(end_date) if end_date is not None else '',
    )

    if cache_key in _TUSHARE_CACHE:
        cached_df = _TUSHARE_CACHE[cache_key]
        fetched_at = _TUSHARE_CACHE_TS.get(cache_key)
        now = datetime.now()
        if not _should_refresh_tushare_cache(df=cached_df, end_date=end_date, fetched_at=fetched_at, now=now):
            return cached_df.copy()

    if not _TUSHARE_TOKEN:
        raise RuntimeError(
            "Tushare token is not configured. Set TUSHARE_TOKEN or create backend/.tushare_token to enable data downloads."
        )

    pro = ts.pro_api()

    if symbol_type == 'stock':
        df1 = pro.daily(ts_code=symbol_code, start_date=start_date, end_date=end_date)
        df2 = pro.daily_basic(
            ts_code=symbol_code,
            start_date=start_date,
            end_date=end_date,
            fields='trade_date,turnover_rate_f,volume_ratio,pe,pb'
        )

        df1['trade_date'] = pd.to_datetime(df1['trade_date'], format='%Y%m%d')
        df2['trade_date'] = pd.to_datetime(df2['trade_date'], format='%Y%m%d')

        df = pd.merge(df1, df2, on='trade_date', how='inner', suffixes=('', '_basic'))
        if df.empty:
            print(f"[{symbol_code}] stock data is empty, returning an empty DataFrame")
            _TUSHARE_CACHE[cache_key] = df.copy()
            return df

        df = df.rename(columns={'vol': 'volume'})
    else:
        df = pro.index_daily(ts_code=symbol_code, start_date=start_date, end_date=end_date)
        if df.empty:
            print(f"[{symbol_code}] index data is empty, returning an empty DataFrame")
            _TUSHARE_CACHE[cache_key] = df.copy()
            return df

        df = df.rename(columns={'vol': 'volume'})

    df = df.sort_values(by='trade_date')
    _TUSHARE_CACHE[cache_key] = df.copy()
    _TUSHARE_CACHE_TS[cache_key] = datetime.now()
    return df

import os
import pandas as pd
from sqlalchemy import create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from datetime import datetime, date

def _normalize_date(d):
    """将多种日期输入规范化为 'YYYY-MM-DD' 字符串。允许 None。"""
    if d is None or d == "":
        return None
    # datetime/date 直接处理
    if isinstance(d, (datetime, date)):
        return pd.to_datetime(d).strftime("%Y-%m-%d")
    # 字符串：先尝试纯数字格式，再退回通用解析
    s = str(d).strip()
    if s.isdigit() and len(s) == 8:
        # '20230101'
        return pd.to_datetime(s, format="%Y%m%d").strftime("%Y-%m-%d")
    # 让 pandas 自动识别 '2023-01-01' / '2023/1/1' 等
    return pd.to_datetime(s, errors="raise").strftime("%Y-%m-%d")

def read_day_from_mysql(symbol_code, symbol_type='stock', start_date=None, end_date=None):
    """
    从 MySQL 读取指定标的的日线数据。
    - 支持 start_date/end_date 为 'YYYYMMDD'、'YYYY-MM-DD'、datetime/date、或 None。
    - 如果表不存在或查询失败，返回空 DataFrame 并打印提示。
    """
    # 表名：把 ts_code 中 '.' 改为 '_'（例如 000001.SH -> 000001_SH）
    table_name = symbol_code.replace('.', '_')
    db_name = 'stock_data' if symbol_type == 'stock' else 'index_data'

    # —— 安全建议：使用环境变量保存凭据 ——
    user = os.getenv("MYSQL_USER", "root")
    pwd  = os.getenv("MYSQL_PASSWORD", "7015194zhukunren")
    host = os.getenv("MYSQL_HOST", "localhost")
    port = int(os.getenv("MYSQL_PORT", "3306"))
    charset = "utf8mb4"

    url = f"mysql+pymysql://{user}:{pwd}@{host}:{port}/{db_name}?charset={charset}"

    # 规范化日期
    try:
        start_str = _normalize_date(start_date)
        end_str   = _normalize_date(end_date)
    except Exception as e:
        print(f"❌ 日期解析失败：{e}")
        return pd.DataFrame()

    try:
        engine = create_engine(url)
    except SQLAlchemyError as e:
        print(f"❌ 创建 SQLAlchemy engine 失败：{e}")
        return pd.DataFrame()

    # 构造 SQL（尽量避免包裹列以便使用索引；假设 trade_date 为 DATE/DATETIME）
    base_sql = f"SELECT * FROM `{table_name}`"
    params = {}

    if start_str and end_str:
        where = " WHERE trade_date >= :start AND trade_date <= :end"
        params.update({"start": start_str, "end": end_str})
    elif start_str:
        where = " WHERE trade_date >= :start"
        params.update({"start": start_str})
    elif end_str:
        where = " WHERE trade_date <= :end"
        params.update({"end": end_str})
    else:
        where = ""

    sql = text(base_sql + where)

    try:
        with engine.connect() as conn:
            df = pd.read_sql_query(sql, con=conn, params=params)
    except SQLAlchemyError as e:
        # 更具体地判断“表不存在”
        err_msg = str(getattr(e, "orig", e))
        if "doesn't exist" in err_msg or "Unknown table" in err_msg:
            print(f"⚠️ 表 `{table_name}` 不存在：{err_msg}")
        else:
            print(f"❌ 查询 `{table_name}` 失败：{err_msg}")
        return pd.DataFrame()
    finally:
        engine.dispose()

    if df.empty:
        print(f"[{symbol_code}] 数据为空，返回空 DataFrame。")
        return df

    # 统一日期类型、排序与列名
    if 'trade_date' in df.columns:
        df['trade_date'] = pd.to_datetime(df['trade_date'])
        df.sort_values(by='trade_date', inplace=True)
    if 'ts_code' in df.columns:
        df.rename(columns={'ts_code': 'stock_code'}, inplace=True)

    return df

def get_all_stocks():
    TS_TOKEN = "2876ea85cb005fb5fa17c809a98174f2d5aae8b1f830110a5ead6211"
    pro = ts.pro_api(TS_TOKEN)
    data = pro.stock_basic(exchange='', list_status='L', fields='ts_code,symbol,name,area,industry,list_date')
    print(data)
    #stock_list = data['ts_code'].tolist()
    data.rename(columns={'ts_code': 'stock_code', 'name': 'stock_name'}, inplace=True)
  
    return data

def get_all_stocks_fromcsv():
    df = pd.read_csv("C:\\Users\\11705\\Desktop\\全部A股.csv", encoding='gbk')
    df.rename(columns={'wind_code': 'stock_code', 'sec_name': 'stock_name'}, inplace=True)
    df = df.dropna()

    return df

