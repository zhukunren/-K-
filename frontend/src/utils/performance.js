/**
 * 性能优化工具函数
 * 用于防抖、节流等高频事件优化
 */

/**
 * 防抖函数 - 在最后一次调用后延迟执行
 * 适用场景：resize、input、search 等频繁触发的事件
 *
 * @param {Function} func - 要执行的函数
 * @param {number} delay - 延迟时间（毫秒），默认 300ms
 * @param {Object} options - 配置选项
 * @param {boolean} options.leading - 是否在开始时立即执行（默认 false）
 * @param {boolean} options.trailing - 是否在延迟后执行（默认 true）
 * @param {number} options.maxWait - 最大等待时间（毫秒），超过此时间必须执行
 * @returns {Function} 防抖后的函数
 */
export function debounce(func, delay = 300, options = {}) {
  let timeoutId = null
  let lastCallTime = 0
  let lastInvokeTime = 0
  let lastThis
  let lastArgs
  let result

  const { leading = false, trailing = true, maxWait } = options

  function invokeFunc(time) {
    const args = lastArgs
    const thisArg = lastThis

    lastArgs = lastThis = null
    lastInvokeTime = time
    result = func.apply(thisArg, args)
    return result
  }

  function shouldInvoke(time) {
    const timeSinceLastCall = time - (lastCallTime || 0)
    const timeSinceLastInvoke = time - lastInvokeTime

    return (
      lastCallTime === 0 ||
      timeSinceLastCall >= delay ||
      timeSinceLastCall < 0 ||
      (maxWait && timeSinceLastInvoke >= maxWait)
    )
  }

  function timerExpired() {
    const time = Date.now()
    if (shouldInvoke(time)) {
      trailingEdge(time)
    } else {
      const timeSinceLastCall = Date.now() - (lastCallTime || 0)
      const timeWaitingForMaxWait = maxWait ? Math.max(0, maxWait - timeSinceLastCall) : 0
      timeoutId = setTimeout(timerExpired, Math.max(delay - timeSinceLastCall, timeWaitingForMaxWait))
    }
  }

  function trailingEdge(time) {
    timeoutId = null
    if (trailing && lastArgs) {
      return invokeFunc(time)
    }
    lastArgs = lastThis = null
    return result
  }

  function leadingEdge(time) {
    lastInvokeTime = time
    timeoutId = setTimeout(timerExpired, delay)
    return leading ? invokeFunc(time) : result
  }

  function cancel() {
    if (timeoutId) {
      clearTimeout(timeoutId)
    }
    lastInvokeTime = 0
    lastCallTime = 0
    lastArgs = lastThis = timeoutId = null
  }

  function flush() {
    return timeoutId ? trailingEdge(Date.now()) : result
  }

  function debounced(...args) {
    const time = Date.now()
    const isInvoking = shouldInvoke(time)

    lastArgs = args
    lastThis = this
    lastCallTime = time

    if (isInvoking) {
      if (!timeoutId && leading) {
        return leadingEdge(time)
      }
      if (timeoutId) {
        clearTimeout(timeoutId)
      }
      timeoutId = setTimeout(timerExpired, delay)
    }
    return result
  }

  debounced.cancel = cancel
  debounced.flush = flush

  return debounced
}

/**
 * 节流函数 - 在时间段内最多执行一次
 * 适用场景：scroll、mousemove 等持续触发的事件
 *
 * @param {Function} func - 要执行的函数
 * @param {number} limit - 时间限制（毫秒），默认 300ms
 * @param {Object} options - 配置选项
 * @param {boolean} options.leading - 是否在开始时立即执行（默认 true）
 * @param {boolean} options.trailing - 是否在时间段后执行（默认 true）
 * @returns {Function} 节流后的函数
 */
export function throttle(func, limit = 300, options = {}) {
  let inThrottle = false
  let lastFunc
  let lastRan
  let lastArgs
  let lastThis
  let result

  const { leading = true, trailing = true } = options

  function invokeFunc() {
    result = func.apply(lastThis, lastArgs)
    lastRan = Date.now()
  }

  function cancel() {
    if (lastFunc) {
      clearTimeout(lastFunc)
      lastFunc = null
    }
    inThrottle = false
    lastRan = null
    lastArgs = lastThis = null
  }

  function flush() {
    if (lastFunc) {
      clearTimeout(lastFunc)
      invokeFunc()
      lastFunc = null
    }
  }

  function throttled(...args) {
    const now = Date.now()

    if (!lastRan && !leading) {
      lastRan = now
    }

    lastArgs = args
    lastThis = this

    const remaining = limit - (now - (lastRan || 0))

    if (remaining <= 0) {
      if (lastFunc) {
        clearTimeout(lastFunc)
        lastFunc = null
      }
      invokeFunc()
    } else if (!lastFunc && trailing) {
      lastFunc = setTimeout(invokeFunc, remaining)
    }

    return result
  }

  throttled.cancel = cancel
  throttled.flush = flush

  return throttled
}

/**
 * 判断是否为移动设备
 * @returns {boolean}
 */
export function isMobileDevice() {
  const userAgent = navigator.userAgent || navigator.vendor || window.opera
  return /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(userAgent.toLowerCase())
}

/**
 * 判断设备方向
 * @returns {boolean} true 为竖屏，false 为横屏
 */
export function isPortraitOrientation() {
  return window.innerHeight >= window.innerWidth
}

/**
 * 获取设备窗口尺寸
 * @returns {Object} { width, height }
 */
export function getViewportSize() {
  return {
    width: Math.max(document.documentElement.clientWidth || 0, window.innerWidth || 0),
    height: Math.max(document.documentElement.clientHeight || 0, window.innerHeight || 0)
  }
}

/**
 * 创建带有内存限制的缓存函数
 * 避免在高频调用中反复计算相同结果
 *
 * @param {Function} func - 要缓存的函数
 * @param {number} maxSize - 最大缓存条数，默认 100
 * @returns {Function} 带缓存的函数
 */
export function memoize(func, maxSize = 100) {
  const cache = new Map()

  function generateKey(args) {
    return JSON.stringify(args)
  }

  function memoized(...args) {
    const key = generateKey(args)

    if (cache.has(key)) {
      return cache.get(key)
    }

    const result = func.apply(this, args)

    if (cache.size >= maxSize) {
      const firstKey = cache.keys().next().value
      cache.delete(firstKey)
    }

    cache.set(key, result)
    return result
  }

  memoized.clear = () => cache.clear()
  memoized.size = () => cache.size

  return memoized
}

/**
 * 性能监控 - 测量函数执行时间
 *
 * @param {Function} func - 要监控的函数
 * @param {string} label - 标签，用于控制台输出
 * @returns {Function} 包装后的函数
 */
export function measurePerformance(func, label = 'Function') {
  return function(...args) {
    const startTime = performance.now()
    const result = func.apply(this, args)
    const endTime = performance.now()

    const duration = (endTime - startTime).toFixed(2)
    console.log(`[Performance] ${label}: ${duration}ms`)

    return result
  }
}

/**
 * 批量处理 - 将多个异步操作分批执行
 *
 * @param {Array} items - 要处理的项目数组
 * @param {Function} processor - 处理函数，接收单个项目
 * @param {number} batchSize - 每批处理的数量，默认 10
 * @returns {Promise} 当所有项目都处理完成时 resolve
 */
export async function batchProcess(items, processor, batchSize = 10) {
  const results = []

  for (let i = 0; i < items.length; i += batchSize) {
    const batch = items.slice(i, i + batchSize)
    const batchResults = await Promise.all(
      batch.map(item => Promise.resolve(processor(item)))
    )
    results.push(...batchResults)
  }

  return results
}

/**
 * 请求去重 - 防止短时间内的重复请求
 *
 * @param {Function} requestFunc - 发送请求的函数
 * @param {number} dedupeTime - 去重时间窗口（毫秒），默认 1000ms
 * @returns {Function} 去重后的请求函数
 */
export function dedupeRequest(requestFunc, dedupeTime = 1000) {
  const pendingRequests = new Map()

  return function(...args) {
    const key = JSON.stringify(args)

    // 如果相同请求在时间窗口内已存在，直接返回之前的 promise
    if (pendingRequests.has(key)) {
      return pendingRequests.get(key).promise
    }

    // 发送新请求
    const promise = Promise.resolve(requestFunc.apply(this, args))
      .finally(() => {
        // 延迟后清除缓存
        setTimeout(() => {
          pendingRequests.delete(key)
        }, dedupeTime)
      })

    pendingRequests.set(key, { promise, time: Date.now() })

    return promise
  }
}
