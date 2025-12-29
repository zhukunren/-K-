import axios from 'axios'
import { ElMessage } from 'element-plus'

// 创建axios实例
const API_BASE_URL = window.location.hostname === 'localhost' || window.location.hostname === '127.0.0.1'
  ? '/api'
  : `${window.location.protocol}//${window.location.hostname}/api`

const request = axios.create({
  baseURL: API_BASE_URL,
  // 预测训练较耗时，将全局超时提高到5分钟；单次请求也可覆盖
  timeout: 300000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
request.interceptors.request.use(
  config => {
    // 可以在这里添加token等认证信息
    return config
  },
  error => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
request.interceptors.response.use(
  response => {
    const res = response.data
    return res
  },
  error => {
    console.error('响应错误:', error)
    let message = '请求失败'

    if (error.code === 'ECONNABORTED') {
      message = '请求超时：后端计算较慢，请稍后重试或缩小参数范围'
    } else if (error.response) {
      switch (error.response.status) {
        case 400:
          message = error.response.data?.detail || '请求参数错误'
          break
        case 404:
          message = '请求资源不存在'
          break
        case 500:
          message = error.response.data?.detail || '服务器内部错误'
          break
        default:
          message = error.response.data?.detail || `HTTP ${error.response.status}`
      }
    } else if (error.request) {
      message = '网络连接失败：请确认后端已启动并可访问'
    }

    ElMessage.error(message)
    return Promise.reject(error)
  }
)

export default request
