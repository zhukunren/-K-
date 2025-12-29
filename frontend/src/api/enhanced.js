// 增强版API服务 - 支持20个新功能
import axios from 'axios'

// 使用增强版API端口
const API_BASE_URL = 'http://localhost:5001'

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// ==================== 1. 批量股票对比分析 ====================
export const batchCompareAPI = async (symbols, params) => {
  const response = await api.post('/api/batch_compare', {
    symbols,
    params
  })
  return response.data
}

// ==================== 2. 实时数据接入 ====================
export const getRealtimeDataAPI = async (symbol) => {
  const response = await api.get('/api/realtime_data', {
    params: { symbol }
  })
  return response.data
}

// ==================== 3. 历史预测回测 ====================
export const runBacktestAPI = async (params) => {
  const response = await api.post('/api/backtest', params)
  return response.data
}

// ==================== 4. 自定义技术指标 ====================
export const createCustomIndicatorAPI = async (name, formula, params) => {
  const response = await api.post('/api/custom_indicator', {
    name,
    formula,
    params
  })
  return response.data
}

// ==================== 5. 多模型集成预测 ====================
export const multiModelPredictAPI = async (features) => {
  const response = await api.post('/api/multi_model_predict', {
    features
  })
  return response.data
}

// ==================== 6. 预测置信度 ====================
export const getPredictionConfidenceAPI = async (params) => {
  const response = await api.post('/api/prediction_confidence', params)
  return response.data
}

// ==================== 7. 异常检测告警 ====================
export const detectAnomaliesAPI = async (data) => {
  const response = await api.post('/api/anomaly_detection', data)
  return response.data
}

// ==================== 8. 自适应参数优化 ====================
export const optimizeParametersAPI = async (data) => {
  const response = await api.post('/api/optimize_params', data)
  return response.data
}

// ==================== 9. 买卖点提示 ====================
export const getTradingSignalsAPI = async (data) => {
  const response = await api.post('/api/trading_signals', data)
  return response.data
}

// ==================== 10. 止损止盈计算 ====================
export const calculateRiskManagementAPI = async (params) => {
  const response = await api.post('/api/risk_management', params)
  return response.data
}

// ==================== 11. 仓位管理建议 ====================
export const getPositionManagementAPI = async (portfolio, riskProfile) => {
  const response = await api.post('/api/position_management', {
    portfolio,
    risk_profile: riskProfile
  })
  return response.data
}

// ==================== 12. 模拟交易系统 ====================
export const paperTradingAPI = async (action, data) => {
  const response = await api.post('/api/paper_trading', {
    action,
    ...data
  })
  return response.data
}

// ==================== 13. 预测结果订阅 ====================
export const subscribePredictionsAPI = async (email, symbols, frequency) => {
  const response = await api.post('/api/subscribe', {
    email,
    symbols,
    frequency
  })
  return response.data
}

// ==================== 14. 自选股票列表 ====================
export const getWatchlistAPI = async () => {
  const response = await api.get('/api/watchlist')
  return response.data
}

export const addToWatchlistAPI = async (symbol, notes) => {
  const response = await api.post('/api/watchlist', {
    symbol,
    notes
  })
  return response.data
}

export const removeFromWatchlistAPI = async (symbol) => {
  const response = await api.delete('/api/watchlist', {
    data: { symbol }
  })
  return response.data
}

// ==================== 15. 预测历史记录 ====================
export const getPredictionHistoryAPI = async (symbol, limit = 50) => {
  const response = await api.get('/api/prediction_history', {
    params: { symbol, limit }
  })
  return response.data
}

// ==================== 16. 数据导出增强 ====================
export const exportDataAPI = async (format, data) => {
  const response = await api.post(`/api/export/${format}`, {
    data
  })
  return response.data
}

// ==================== 17. 热力图可视化 ====================
export const generateHeatmapAPI = async (symbols) => {
  const response = await api.post('/api/heatmap', {
    symbols
  })
  return response.data
}

// ==================== 18. 3D K线图表 ====================
export const generate3DChartAPI = async (params) => {
  const response = await api.post('/api/3d_chart', params)
  return response.data
}

// ==================== 19. 预测路径动画 ====================
export const createPredictionAnimationAPI = async (params) => {
  const response = await api.post('/api/prediction_animation', params)
  return response.data
}

// ==================== 20. 移动端优化API ====================
export const getMobileSummaryAPI = async () => {
  const response = await api.get('/api/mobile/summary')
  return response.data
}

export default api