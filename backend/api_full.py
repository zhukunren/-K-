# -*- coding: utf-8 -*-
# Stock prediction API (full transformer pipeline).
from datetime import datetime
from typing import List, Optional, Literal

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, ConfigDict
import asyncio
import traceback
import numpy as np
import plotly.graph_objs as go
import plotly.offline as pyo
from plotly.subplots import make_subplots

# Defer heavy pipeline import to endpoints to avoid hard dependency at startup

app = FastAPI(title="Stock Prediction API - Full Version", version="3.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加响应头中间件：确保JSON响应包含UTF-8编码声明
@app.middleware("http")
async def add_utf8_header(request, call_next):
    response = await call_next(request)
    # 为JSON响应添加charset=utf-8
    if "application/json" in response.headers.get("content-type", ""):
        response.headers["content-type"] = "application/json; charset=utf-8"
    return response


class PredictionRequest(BaseModel):
    model_config = ConfigDict(protected_namespaces=())

    symbol: str = "000001.SH"
    start_date: str = "20200101"
    end_date: str = "20261231"
    window: int = 30
    h_future: int = 5
    epochs: int = 20
    topk: int = 5
    selected_features: Optional[List[str]] = None
    use_fixed_seed: bool = True
    random_seed: int = 42
    agg: str = "median"
    engine: Literal["ml", "classic"] = "ml"
    model_type: Literal["transformer", "lstm", "gru", "cnn_transformer", "transformer_lstm", "transformer_gru"] = "transformer"
    use_window_zscore: bool = True
    min_gap_days: Optional[int] = None
    lookback: int = 100
    stride: int = 1
    dedup_radius: int = 5
    prefilter: bool = True
    prefilter_multiplier: int = 5
    prefilter_tolerance: float = 0.6
    show_paths: bool = False
    # Similarity method: corr_only/dtw_only/hybrid/mp_hybrid
    sim_method: Literal["corr_only", "dtw_only", "hybrid", "mp_hybrid"] = "hybrid"
    # Hybrid similarity re-ranking parameters
    re_rank_top: int = 30  # number of candidates to re-rank by shape
    use_corr: bool = True
    use_dtw: bool = True
    alpha_cos: float = 0.5
    beta_corr: float = 0.3
    gamma_dtw: float = 0.2
    strictness: float = 0.75  # default aligned with cached评估
    evaluate_daily: bool = True
    evaluation_start_date: Optional[str] = "20250101"
    # 缓存控制参数
    use_cache: bool = True  # 是否启用模型缓存
    freeze_eval_history: bool = True  # 是否冻结逐日评估历史，避免新行情改变旧结果
    force_eval_refresh: bool = False  # 强制重算逐日评估（忽略缓存）


FEATURE_NAME_MAP = {
    # Trend indicators
    "MA5_MA20_Diff": "MA5-MA20差值",
    "Slope_MA5": "MA5斜率",
    "close_MA5_Diff": "收盘价-MA5",
    "Cross_MA5_Count": "MA5穿越次数",

    # Momentum indicators
    "RSI_Signal": "RSI信号",
    "RSI_14": "RSI相对强弱指标(14)",
    "K_D_Diff": "KD差值",
    "CCI_20": "顺势指标(20)",
    "Williams_%R_14": "威廉指标(14)",
    "Ultimate_Osc": "终极震荡指标",

    # Volatility indicators
    "Bollinger_Width": "布林带宽度",
    "ADX_14": "平均趋向指标(14)",
    "Plus_DI": "上升动向指标",
    "Minus_DI": "下降动向指标",
    "ZScore_20": "标准分数(20)",

    # Volume indicators
    "OBV": "能量潮指标",
    "VWAP": "成交量加权均价",
    "volume_Change": "成交量变化",
    "volume_Spike_Count": "成交量异动次数",
    "Chaikin_Osc": "蔡金振荡指标",
    "volume": "成交量",

    # MACD indicator
    "MACD_Diff": "MACD差值",

    # Price stats
    "Price_Mean_Diff": "价格-均值差",
    "high_Mean_Diff": "最高价-均值差",
    "low_Mean_Diff": "最低价-均值差",

    # Other indicators
    "PPO": "价格震荡百分比",
    "KST": "确定指标",
    "KST_signal": "确定指标信号",
    "KAMA_10": "考夫曼自适应均线(10)",
}

FEATURE_GROUPS = {
    "Trend": ["MA5_MA20_Diff", "Slope_MA5", "close_MA5_Diff", "Cross_MA5_Count"],
    "Momentum": ["RSI_Signal", "RSI_14", "K_D_Diff", "CCI_20", "Williams_%R_14", "Ultimate_Osc"],
    "Volatility": ["Bollinger_Width", "ADX_14", "Plus_DI", "Minus_DI", "ZScore_20"],
    "Volume": ["OBV", "VWAP", "volume_Change", "volume_Spike_Count", "Chaikin_Osc", "volume"],
    "MACD": ["MACD_Diff"],
    "Price": ["Price_Mean_Diff", "high_Mean_Diff", "low_Mean_Diff"],
    "Other": ["PPO", "KST", "KST_signal", "KAMA_10"],
}

# Feature group display labels
FEATURE_GROUP_LABELS = {
    "Trend": "趋势指标",
    "Momentum": "动量指标",
    "Volatility": "波动指标",
    "Volume": "成交量指标",
    "MACD": "MACD指标",
    "Price": "价格指标",
    "Other": "其他指标",
}


@app.get("/")
def read_root():
    return {"message": "Stock Prediction API (Full Version) is running", "version": "3.0.0"}


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "timestamp": datetime.now().isoformat(), "version": "3.0.0"}


@app.get("/api/features")
def get_features():
    try:
        # Dynamically extend: MA_5, MA_20, pct_change and raw OHLC
        feature_map = dict(FEATURE_NAME_MAP)
        feature_groups = {k: list(v) for k, v in FEATURE_GROUPS.items()}

        # Additional readable labels (中文名称)
        feature_map.setdefault("MA_5", "MA5均线")
        feature_map.setdefault("MA_20", "MA20均线")
        feature_map.setdefault("pct_change", "涨跌幅")
        feature_map.setdefault("open", "开盘价")
        feature_map.setdefault("high", "最高价")
        feature_map.setdefault("low", "最低价")
        feature_map.setdefault("close", "收盘价")

        # Update groups
        if "Trend" in feature_groups:
            if "MA_5" not in feature_groups["Trend"]:
                feature_groups["Trend"].append("MA_5")
            if "MA_20" not in feature_groups["Trend"]:
                feature_groups["Trend"].append("MA_20")
        if "Price" in feature_groups:
            if "pct_change" not in feature_groups["Price"]:
                feature_groups["Price"].insert(0, "pct_change")  # 添加到开头
            if "close" not in feature_groups["Price"]:
                feature_groups["Price"].insert(0, "close")  # 添加到开头
            if "volume" not in feature_groups["Price"]:
                # 将成交量从Volume组复制到Price组
                feature_groups["Price"].append("volume")
            for col in ["open", "high", "low"]:
                if col not in feature_groups["Price"]:
                    feature_groups["Price"].append(col)

        return {
            "feature_map": feature_map,
            "feature_groups": feature_groups,
            "feature_group_labels": FEATURE_GROUP_LABELS,
            "total_features": len(feature_map),
        }
    except Exception as e:
        print(f"Error in get_features: {str(e)}")
        import traceback
        traceback.print_exc()
        raise HTTPException(
            status_code=500,
            detail=f"加载特征列表失败: {str(e)}"
        )


@app.post("/api/predict")
async def predict(request: PredictionRequest):
    # Local import to avoid importing torch/pandas at startup for health checks
    from pipeline_core import run_transformer_pipeline
    try:
        result = run_transformer_pipeline(request)
        response = {
            "status": "success",
            "message": f"Found {len(result['similar_windows'])} similar windows",
            "data": {
                "historical_data": result["historical_data"],
                "predictions": result["predictions"],
                "future_dates": result["future_dates"],
                "mean_path": result["mean_path"],
                "q25_path": result["q25_path"],
                "q75_path": result["q75_path"],
                "close_paths": result["close_paths"],
                "last_window": result["last_window"],
                "similar_windows": result["similar_windows"],
                "most_similar_day": result.get("most_similar_day"),  # 添加最相似交易日
            },
            "similar_windows": result["similar_windows"],
            "most_similar_day": result.get("most_similar_day"),  # 添加到顶层
            "model_info": result["model_info"],
        }
        evaluation = result.get("evaluation")
        if evaluation is not None:
            response["evaluation"] = evaluation
        return response
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Prediction failed: {exc}") from exc


@app.post("/api/generate_chart")
async def generate_chart(request: PredictionRequest):
    # Local import to avoid importing torch/pandas at startup for health checks
    from pipeline_core import run_transformer_pipeline
    try:
        # Pydantic v2: BaseModel.copy 已废弃，使用 model_copy 以消除告警
        chart_request = request.model_copy(update={"evaluate_daily": False})
        result = run_transformer_pipeline(chart_request)
        hist = result.get("historical_data", [])
        # Limit to the most recent 120 trading days for display
        try:
            if len(hist) > 120:
                hist = hist[-120:]
        except Exception:
            pass
        # Limit historical window to show from 2025-01-01 onward
        try:
            hist = [item for item in hist if item.get("date", "") >= "2025-01-01"]
        except Exception:
            pass
        preds = result.get("predictions", [])

        # Build chart: historical and forecast K-lines + MA5/MA20 + volume + returns
        fig = make_subplots(
            rows=2,
            cols=1,
            shared_xaxes=True,
            vertical_spacing=0.06,
            row_heights=[0.7, 0.3],
            specs=[[{}], [{"secondary_y": True}]],
        )

        hist_dates = [item["date"] for item in hist]
        hist_open = [item.get("open", item.get("close", 0.0)) for item in hist]
        hist_high = [item.get("high", item.get("close", 0.0)) for item in hist]
        hist_low = [item.get("low", item.get("close", 0.0)) for item in hist]
        hist_close = [item.get("close", item.get("open", 0.0)) for item in hist]
        hist_vol = [item.get("volume", 0.0) for item in hist]

        future_dates = [item["date"] for item in preds]
        fut_open = [item.get("open", 0.0) for item in preds]
        fut_high = [item.get("high", 0.0) for item in preds]
        fut_low = [item.get("low", 0.0) for item in preds]
        fut_close = [item.get("close", 0.0) for item in preds]

        def _build_candle_custom(open_values, close_values, prev_close=None):
            custom_rows = []
            prev = prev_close
            for o_val, c_val in zip(open_values, close_values):
                change = float("nan")
                if o_val not in (None, 0):
                    change = ((c_val - o_val) / o_val) * 100.0
                gap = float("nan")
                if prev not in (None, 0):
                    gap = ((o_val - prev) / prev) * 100.0
                custom_rows.append([change, gap])
                prev = c_val
            return custom_rows

        def _build_tooltips(dates, opens, highs, lows, closes, extras):
            tooltips = []
            for d, o_val, h_val, l_val, c_val, extra in zip(dates, opens, highs, lows, closes, extras):
                change, gap = extra
                lines = [
                    f"<b>{d}</b>",
                    f"Open: {o_val:.2f}",
                    f"High: {h_val:.2f}",
                    f"Low: {l_val:.2f}",
                    f"Close: {c_val:.2f}",
                ]
                if not np.isnan(change):
                    lines.append(f"Change: {change:+.2f}%")
                if not np.isnan(gap):
                    lines.append(f"Gap: {gap:+.2f}%")
                tooltips.append("<br>".join(lines))
            return tooltips

        hist_custom = _build_candle_custom(hist_open, hist_close)
        hist_hover = _build_tooltips(hist_dates, hist_open, hist_high, hist_low, hist_close, hist_custom)
        prev_close = hist_close[-1] if hist_close else None
        fut_custom = _build_candle_custom(fut_open, fut_close, prev_close)
        fut_hover = _build_tooltips(future_dates, fut_open, fut_high, fut_low, fut_close, fut_custom)

        # Historical and forecast candlesticks
        if hist:
            fig.add_trace(go.Candlestick(
                x=hist_dates, open=hist_open, high=hist_high, low=hist_low, close=hist_close,
                name="Price",
                increasing_line_color="#ef5350",
                decreasing_line_color="#26a69a",
                increasing_fillcolor="rgba(239,83,80,0.6)",
                decreasing_fillcolor="rgba(38,166,154,0.6)",
                customdata=hist_custom,
                hovertext=hist_hover,
                hoverinfo="text",
            ), row=1, col=1)
        if preds:
            fig.add_trace(go.Candlestick(
                x=future_dates, open=fut_open, high=fut_high, low=fut_low, close=fut_close,
                name="Forecast",
                increasing_line_color="#0D47A1",
                decreasing_line_color="#0D47A1",
                increasing_fillcolor="rgba(13,71,161,1)",
                decreasing_fillcolor="rgba(13,71,161,1)",
                line=dict(width=2),
                customdata=fut_custom,
                hovertext=fut_hover,
                hoverinfo="text",
            ), row=1, col=1)

        # Forecast mean and IQR
        if preds:
            fig.add_trace(go.Scatter(
                x=future_dates,
                y=result.get("mean_path", []),
                mode="lines",
                name="Forecast mean (close)",
                line=dict(color="#42A5F5", width=2, dash="dot"),
            ), row=1, col=1)

            q75 = result.get("q75_path", [])
            q25 = result.get("q25_path", [])
            if q75 and q25:
                fig.add_trace(go.Scatter(x=future_dates, y=q75, mode="lines", line=dict(width=0),
                                         showlegend=False, hoverinfo="skip"), row=1, col=1)
                fig.add_trace(go.Scatter(x=future_dates, y=q25, mode="lines", line=dict(width=0),
                                         fill="tonexty", fillcolor="rgba(66,165,245,0.15)",
                                         name="Forecast close IQR"), row=1, col=1)

            if result.get("close_paths"):
                for path in result["close_paths"]:
                    if len(path) == len(future_dates):
                        fig.add_trace(go.Scatter(
                            x=future_dates,
                            y=path,
                            mode="lines",
                            line=dict(color="rgba(33,150,243,0.25)", width=1),
                            showlegend=False,
                            hoverinfo="skip",
                        ), row=1, col=1)

        # Append MA5/MA20 over all close values
        all_dates = hist_dates + future_dates
        all_close = hist_close + fut_close
        if all_dates:
            def sma(arr, n):
                out = []
                s = 0.0
                for i, v in enumerate(arr):
                    s += v
                    if i >= n:
                        s -= arr[i - n]
                    out.append(s / float(min(i + 1, n)))
                return out

            ma5 = sma(all_close, 5)
            ma20 = sma(all_close, 20)
            fig.add_trace(go.Scatter(x=all_dates, y=ma5, mode="lines", name="MA5",
                                     line=dict(color="#FF9800", width=1.5)), row=1, col=1)
            fig.add_trace(go.Scatter(x=all_dates, y=ma20, mode="lines", name="MA20",
                                     line=dict(color="#9C27B0", width=1.2)), row=1, col=1)

        # Volume bars (row 2 left axis)
        if hist:
            fig.add_trace(go.Bar(x=hist_dates, y=hist_vol, name="Volume",
                                 marker_color="rgba(100,181,246,0.6)"), row=2, col=1, secondary_y=False)

        # Returns line (row 2 right axis, in %)
        if all_close:
            rets = [None]
            for i in range(1, len(all_close)):
                prev = all_close[i - 1]
                cur = all_close[i]
                rets.append(((cur - prev) / prev) * 100 if prev else None)
            fig.add_trace(go.Scatter(x=all_dates, y=rets, mode="lines", name="Return (%)",
                                     line=dict(color="#607D8B", width=1)), row=2, col=1, secondary_y=True)

        # Hide distinction between similar windows and standard window: no highlight rectangles and no split line

        fig.update_layout(
            title=f"{request.symbol} forecast",
            xaxis_title="Date",
            yaxis_title="Price",
            xaxis_rangeslider_visible=False,
            template="plotly_white",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="left", x=0),
            height=680,
            hovermode="x unified",
        )
        if all_dates:
            fig.update_xaxes(type='date', categoryorder='array', categoryarray=all_dates, row=1, col=1)
            fig.update_xaxes(type='date', categoryorder='array', categoryarray=all_dates, row=2, col=1)
        fig.update_yaxes(title_text="Volume", row=2, col=1, secondary_y=False)
        fig.update_yaxes(title_text="Return (%)", row=2, col=1, secondary_y=True)

        # Use fig.to_html() instead of pyo.plot() to get clean HTML
        html_str = fig.to_html(include_plotlyjs="cdn", config={"responsive": True})

        return {
            "status": "success",
            "html": html_str,
            "data": {
                "historical_data": hist,
                "predictions": preds,
                "similar_windows": result.get("similar_windows", []),
            },
            "model_info": result.get("model_info", {}),
        }
    except HTTPException as exc:
        raise exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Chart rendering failed: {exc}") from exc


@app.get("/api/cache/stats")
def get_cache_stats():
    """获取缓存统计信息"""
    try:
        from model_cache import cache_manager
        stats = cache_manager.get_cache_stats()
        return {
            "status": "success",
            "cache_enabled": True,
            "stats": stats
        }
    except ImportError:
        return {
            "status": "success",
            "cache_enabled": False,
            "message": "Cache module not available"
        }


@app.delete("/api/cache/clear")
def clear_cache():
    """清空所有缓存"""
    try:
        from model_cache import cache_manager
        cache_manager.clear_all_cache()
        # Also clear in-memory market data cache so next request fetches newest bars.
        try:
            from function import clear_tushare_cache
            clear_tushare_cache()
        except Exception:
            traceback.print_exc()
        return {
            "status": "success",
            "message": "All cache cleared successfully"
        }
    except ImportError:
        return {
            "status": "error",
            "message": "Cache module not available"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to clear cache: {str(e)}")
@app.get("/api/cache/list")
def list_cache_entries():
    """List all cache entries for UI."""
    try:
        from model_cache import cache_manager
        entries = cache_manager.list_caches()
        return {
            "status": "success",
            "entries": entries,
            "count": len(entries),
        }
    except ImportError:
        return {"status": "error", "message": "Cache module not available", "entries": []}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list cache: {str(e)}")



@app.post("/api/cache/check")
async def check_cache(request: PredictionRequest):
    """检查特定配置的缓存是否存在"""
    try:
        from model_cache import cache_manager

        # 准备缓存参数
        cache_params = {
            'symbol': request.symbol,
            'start_date': request.start_date,
            'end_date': request.end_date,
            'selected_features': sorted(getattr(request, 'selected_features', []) or []),
            'engine': getattr(request, 'engine', 'ml'),
            'window': request.window,
            'stride': getattr(request, 'stride', 1),
            'd_model': 64,
            'nhead': 4,
            'num_layers': 2,
            'epochs': request.epochs,
            'use_window_zscore': getattr(request, 'use_window_zscore', True),
            'model_type': getattr(request, 'model_type', 'transformer'),
        }

        exists = cache_manager.check_cache_exists(cache_params)
        cache_key = cache_manager._generate_cache_key(cache_params)

        return {
            "status": "success",
            "cache_exists": exists,
            "cache_key": cache_key,
            "message": "Cache hit - model will load from cache" if exists else "Cache miss - model will be trained"
        }
    except ImportError:
        return {
            "status": "error",
            "cache_exists": False,
            "message": "Cache module not available"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Cache check failed: {str(e)}")

async def _daily_cache_refresh_task():
    """Every day at 16:30 local time: clear cache and retrain default model into cache (with retries)."""
    from datetime import datetime, timedelta
    while True:
        try:
            now = datetime.now()
            target = now.replace(hour=16, minute=30, second=0, microsecond=0)
            if target <= now:
                target = target + timedelta(days=1)
            wait_seconds = (target - now).total_seconds()
            await asyncio.sleep(wait_seconds)
            try:
                from model_cache import cache_manager
                cache_manager.clear_all_cache()
            except Exception:
                traceback.print_exc()
            # Clear in-memory Tushare data cache so the refresh job can fetch the newest bars.
            try:
                from function import clear_tushare_cache
                clear_tushare_cache()
            except Exception:
                traceback.print_exc()
            from pipeline_core import run_transformer_pipeline
            default_request = PredictionRequest()
            default_request.window = 5
            default_request.h_future = 5
            default_request.use_window_zscore = True
            default_request.use_cache = True
            retries = 3
            backoff = 5
            for attempt in range(retries):
                try:
                    run_transformer_pipeline(default_request)
                    break
                except Exception:
                    if attempt == retries - 1:
                        traceback.print_exc()
                        break
                    await asyncio.sleep(backoff)
                    backoff *= 2
        except asyncio.CancelledError:
            break
        except Exception:
            traceback.print_exc()
            await asyncio.sleep(60)

@app.on_event("startup")
async def _on_startup():
    asyncio.create_task(_daily_cache_refresh_task())


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8001)
