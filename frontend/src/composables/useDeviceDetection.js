/**
 * Device Detection Composable
 * Detects device type and orientation, adapts UI accordingly
 */
import { ref, onMounted, onUnmounted, computed } from 'vue'

export function useDeviceDetection() {
  const deviceInfo = ref(window.__DEVICE_INFO__ || {
    isMobile: false,
    isTablet: false,
    isLandscape: window.innerWidth > window.innerHeight,
    userAgent: navigator.userAgent
  })

  const viewport = ref({
    width: window.innerWidth,
    height: window.innerHeight,
    breakpoint: getBreakpoint()
  })

  // Computed properties for easier access
  const isMobile = computed(() => deviceInfo.value.isMobile)
  const isTablet = computed(() => deviceInfo.value.isTablet)
  const isLandscape = computed(() => deviceInfo.value.isLandscape)
  const isPortrait = computed(() => !deviceInfo.value.isLandscape)
  const isSmallScreen = computed(() => viewport.value.width < 768)
  const isMediumScreen = computed(() => viewport.value.width >= 768 && viewport.value.width < 1024)
  const isLargeScreen = computed(() => viewport.value.width >= 1024)

  // Get current breakpoint
  function getBreakpoint() {
    const width = window.innerWidth
    if (width < 480) return 'xs'
    if (width < 768) return 'sm'
    if (width < 1024) return 'md'
    if (width < 1440) return 'lg'
    return 'xl'
  }

  // Handle orientation change
  function handleOrientationChange(event) {
    const detail = event.detail || window.__DEVICE_INFO__
    deviceInfo.value = {
      ...deviceInfo.value,
      isLandscape: detail.isLandscape || window.innerWidth > window.innerHeight
    }
  }

  // Handle window resize
  function handleResize() {
    viewport.value = {
      width: window.innerWidth,
      height: window.innerHeight,
      breakpoint: getBreakpoint()
    }
  }

  onMounted(() => {
    // Listen to custom device orientation change event
    window.addEventListener('deviceOrientationChange', handleOrientationChange)
    // Also listen to native orientationchange
    window.addEventListener('orientationchange', handleOrientationChange)
    // Listen to resize
    window.addEventListener('resize', handleResize)
  })

  onUnmounted(() => {
    window.removeEventListener('deviceOrientationChange', handleOrientationChange)
    window.removeEventListener('orientationchange', handleOrientationChange)
    window.removeEventListener('resize', handleResize)
  })

  return {
    deviceInfo,
    viewport,
    isMobile,
    isTablet,
    isLandscape,
    isPortrait,
    isSmallScreen,
    isMediumScreen,
    isLargeScreen
  }
}
