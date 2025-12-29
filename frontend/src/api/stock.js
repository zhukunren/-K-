/**
 * ============================================================================
 * 股价预测系统 - 前端API接口模块
 * ============================================================================
 *
 * 【文件说明】
 * 本文件封装了与后端FastAPI服务通信的所有HTTP请求接口。
 * 使用axios进行HTTP请求,统一管理API调用逻辑。
 *
 * 【接口列表】
 * 1. getFeaturesAPI() - 获取可用技术指标特征列表
 * 2. predictAPI() - 发起股价预测请求
 * 3. generateChartAPI() - 生成Plotly交互式图表HTML
 * 4. healthCheckAPI() - 后端服务健康检查
 *
 * 【请求基础配置】
 * - baseURL: http://localhost:8001/api (在utils/request.js中配置)
 * - timeout: 180000ms (3分钟,因为模型训练需要时间)
 * - Content-Type: application/json
 *
 * 【使用示例】
 * import { predictAPI } from '@/api/stock'
 *
 * const result = await predictAPI({
 *   symbol: "000001.SH",
 *   start_date: "20220101",
 *   end_date: "20251231",
 *   window: 5,
 *   h_future: 5
 * })
 *
 * 【返回数据格式】
 * predictAPI返回:
 * {
 *   historical_data: [...],  // 历史K线数据
 *   predictions: [...],      // 预测K线数据
 *   similar_windows: [...],  // 相似历史窗口
 *   message: "预测成功"
 * }
 *
 * getFeaturesAPI返回:
 * {
 *   features: [...],         // 特征名称列表
 *   feature_groups: {...}    // 按类别分组的特征
 * }
 *
 * 【项目中的用途】
 * - ModernView.vue组件调用这些API函数与后端通信
 * - 支持用户配置预测参数、选择技术指标、获取预测结果
 * - 实现前后端分离架构,便于维护和扩展
 *
 * 【作者】前端API层
 * 【更新日期】2024-10
 * ============================================================================
 */
import request from '@/utils/request'

/**
 * 获取可用的技术指标特征列表
 * @returns {Promise} 返回特征列表和分组信息
 *
 * 用途: 在前端特征选择界面显示可选的29个技术指标
 * 调用时机: 页面加载时或用户点击"高级特征选择"时
 */
export function getFeaturesAPI() {
  return request({
    url: '/features',
    method: 'get'
  })
}

/**
 * 执行股价预测
 * @param {Object} data - 预测参数对象
 * @param {string} data.symbol - 股票/指数代码 (如"000001.SH")
 * @param {string} data.start_date - 起始日期 (YYYYMMDD格式)
 * @param {string} data.end_date - 结束日期 (YYYYMMDD格式)
 * @param {number} data.window - 滑动窗口大小 (默认5天)
 * @param {number} data.h_future - 预测未来天数 (1-10天)
 * @param {number} data.epochs - 训练轮数 (默认20)
 * @param {number} data.topk - TopK相似窗口数量 (默认5)
 * @param {Array} data.selected_features - 用户选择的特征列表 (可选)
 * @param {boolean} data.use_fixed_seed - 是否使用固定随机种子 (默认true)
 * @param {number} data.random_seed - 随机种子值 (默认42)
 * @param {string} data.agg - 聚合方法 (median/mean/min/max)
 * @returns {Promise} 返回预测结果,包含历史数据、预测数据、相似窗口
 *
 * 用途: 核心预测功能,调用后端Transformer模型进行股价预测
 * 调用时机: 用户点击"开始预测"按钮时
 * 注意: 此接口可能耗时较长(10-60秒),需要显示加载提示
 */
export function predictAPI(data) {
  return request({
    url: '/predict',
    method: 'post',
    data,
    // 训练与重排可能耗时，单请求超时设为5分钟
    timeout: 300000
  })
}

/**
 * 生成Plotly交互式图表HTML
 * @param {Object} data - 图表数据对象
 * @param {Array} data.historical_data - 历史K线数据
 * @param {Array} data.predictions - 预测K线数据
 * @param {Array} data.similar_windows - 相似窗口数据
 * @param {string} data.symbol - 股票代码
 * @returns {Promise} 返回Plotly图表的HTML字符串
 *
 * 用途: 生成可交互的K线预测图表,支持缩放、悬停查看数据等功能
 * 调用时机: 获取预测结果后,用于在iframe中渲染图表
 */
export function generateChartAPI(data) {
  return request({
    url: '/generate_chart',
    method: 'post',
    data,
    timeout: 300000
  })
}

/**
 * 后端服务健康检查
 * @returns {Promise} 返回服务状态信息
 *
 * 用途: 检查后端API服务是否正常运行
 * 调用时机: 应用启动时或需要验证后端连接时
 */
export function healthCheckAPI() {
  return request({
    url: '/health',
    method: 'get'
  })
}
