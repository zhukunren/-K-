// 模型缓存相关API
import axios from 'axios'

const BASE_URL = 'http://localhost:8001/api'

// 创建axios实例
const api = axios.create({
  baseURL: BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json'
  }
})

/**
 * 获取缓存统计信息
 */
export const getCacheStats = async () => {
  try {
    const response = await api.get('/cache/stats')
    return response.data
  } catch (error) {
    console.error('Failed to get cache stats:', error)
    throw error
  }
}

/**
 * 检查特定参数的缓存是否存在
 */
export const checkCache = async (params) => {
  try {
    const response = await api.post('/cache/check', params)
    return response.data
  } catch (error) {
    console.error('Failed to check cache:', error)
    throw error
  }
}

/**
 * 清空所有缓存
 */
export const clearCache = async () => {
  try {
    const response = await api.delete('/cache/clear')
    return response.data
  } catch (error) {
    console.error('Failed to clear cache:', error)
    throw error
  }
}

/**
 * 获取缓存列表
 */
export const getCacheList = async () => {
  try {
    const response = await api.get('/cache/list')
    return response.data
  } catch (error) {
    console.error('Failed to get cache list:', error)
    throw error
  }
}

export default {
  getCacheStats,
  getCacheList,
  checkCache,
  clearCache
}
