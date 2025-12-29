<template>
  <div class="mini-kline" ref="chartRef"></div>
</template>

<script setup>
import { ref, onMounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Object,
    required: true
  },
  height: {
    type: Number,
    default: 80
  }
})

const chartRef = ref(null)
let chartInstance = null

const initChart = () => {
  if (!chartRef.value || !props.data) return

  if (chartInstance) {
    chartInstance.dispose()
  }

  chartInstance = echarts.init(chartRef.value)

  const dates = props.data.dates || []
  const opens = props.data.open || []
  const highs = props.data.high || []
  const lows = props.data.low || []
  const closes = props.data.close || []

  // 构建K线数据 [open, close, low, high]
  const klineData = dates.map((date, i) => [
    opens[i],
    closes[i],
    lows[i],
    highs[i]
  ])

  const option = {
    animation: false,
    grid: {
      left: 2,
      right: 2,
      top: 5,
      bottom: 5,
      containLabel: false
    },
    xAxis: {
      type: 'category',
      data: dates,
      show: false
    },
    yAxis: {
      type: 'value',
      show: false,
      scale: true
    },
    series: [
      {
        type: 'candlestick',
        data: klineData,
        itemStyle: {
          color: '#ef5350',
          color0: '#26a69a',
          borderColor: '#ef5350',
          borderColor0: '#26a69a'
        },
        barWidth: '60%'
      }
    ]
  }

  chartInstance.setOption(option)
}

onMounted(() => {
  initChart()
})

watch(() => props.data, () => {
  initChart()
}, { deep: true })
</script>

<style scoped lang="scss">
.mini-kline {
  width: 100%;
  height: v-bind('height + "px"');
  min-height: 60px;
}
</style>
