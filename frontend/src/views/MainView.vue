<template>
  <div class="main-container">
    <el-container>
      <!-- 左侧参数面板 -->
      <el-aside width="350px" class="params-panel">
        <el-card class="params-card">
          <template #header>
            <div class="card-header">
              <span>参数设置</span>
            </div>
          </template>

          <!-- 数据参数 -->
          <div class="param-section">
            <h4>数据参数</h4>
            <el-form :model="params" label-width="100px">
              <el-form-item label="标的代码">
                <el-input v-model="params.symbol" placeholder="000001.SH" />
              </el-form-item>
              <el-form-item label="开始日期">
                <el-date-picker
                  v-model="params.startDate"
                  type="date"
                  placeholder="选择开始日期"
                  format="YYYY-MM-DD"
                  value-format="YYYYMMDD"
                />
              </el-form-item>
              <el-form-item label="结束日期">
                <el-date-picker
                  v-model="params.endDate"
                  type="date"
                  placeholder="选择结束日期"
                  format="YYYY-MM-DD"
                  value-format="YYYYMMDD"
                />
              </el-form-item>
            </el-form>
          </div>

          <!-- 特征选择 -->
          <div class="param-section">
            <h4>特征选择</h4>
            <el-switch v-model="useCustomFeatures" active-text="自定义特征" inactive-text="全部特征" />
            <div v-if="useCustomFeatures" class="feature-selector">
              <el-button-group class="feature-actions">
                <el-button size="small" @click="selectAllFeatures">全选</el-button>
                <el-button size="small" @click="clearFeatures">清空</el-button>
              </el-button-group>
              <el-collapse v-model="activeFeatureGroups">
                <el-collapse-item
                  v-for="(features, groupName) in featureGroups"
                  :key="groupName"
                  :title="`${groupName} (${features.length})`"
                  :name="groupName"
                >
                  <el-checkbox-group v-model="selectedFeatures">
                    <el-checkbox
                      v-for="feat in features"
                      :key="feat"
                      :label="feat"
                      class="feature-checkbox"
                    >
                      {{ featureNameMap[feat] || feat }}
                    </el-checkbox>
                  </el-checkbox-group>
                </el-collapse-item>
              </el-collapse>
              <el-tag type="success" class="feature-count">已选择 {{ selectedFeatures.length }} 个特征</el-tag>
            </div>
          </div>

          <!-- 模型参数 -->
          <div class="param-section">
            <h4>模型参数</h4>
            <el-form :model="params" label-width="100px">
              <el-form-item label="基准周期">
                <el-input-number v-model="params.window" :min="2" :max="100" />
              </el-form-item>
              <el-form-item label="预测天数">
                <el-input-number v-model="params.h_future" :min="1" :max="60" />
              </el-form-item>
              <el-form-item label="显示路径">
                <el-switch v-model="showPaths" />
              </el-form-item>
              <el-form-item label="算法模式">
                <el-radio-group v-model="params.engine" size="small">
                  <el-radio-button label="ml">深度学习</el-radio-button>
                  <el-radio-button label="classic">传统匹配</el-radio-button>
                </el-radio-group>
              </el-form-item>
              <el-divider content-position="left">相似度设置</el-divider>
              <el-form-item label="启用相关">
                <el-switch v-model="params.useCorr" active-text="开启" inactive-text="关闭" />
              </el-form-item>
              <el-form-item label="启用DTW">
                <el-switch v-model="params.useDtw" active-text="开启" inactive-text="关闭" />
              </el-form-item>
              <el-form-item label="余弦权重">
                <el-slider v-model="params.alphaCos" :min="0" :max="1" :step="0.05" show-input />
              </el-form-item>
              <el-form-item label="相关权重">
                <el-slider
                  v-model="params.betaCorr"
                  :min="0"
                  :max="1"
                  :step="0.05"
                  show-input
                  :disabled="!params.useCorr"
                />
              </el-form-item>
              <el-form-item label="DTW权重">
                <el-slider
                  v-model="params.gammaDtw"
                  :min="0"
                  :max="1"
                  :step="0.05"
                  show-input
                  :disabled="!params.useDtw"
                />
              </el-form-item>
              <div class="weight-meta">
                <el-alert
                  v-if="showWeightWarning"
                  type="warning"
                  show-icon
                  :closable="false"
                  class="weight-alert"
                >
                  <template #title>权重和为0，已自动回退到默认配比。</template>
                </el-alert>
                <p class="weight-meta__line">当前设定总权重：{{ (weightSum * 100).toFixed(1) }}%</p>
                <p class="weight-meta__line">
                  归一化后：余弦 {{ (normalizedWeightPreview.alpha * 100).toFixed(1) }}%
                  / 相关 {{ (normalizedWeightPreview.beta * 100).toFixed(1) }}%
                  / DTW {{ (normalizedWeightPreview.gamma * 100).toFixed(1) }}%
                </p>
              </div>
            </el-form>
          </div>

          <el-button type="primary" @click="runPrediction" :loading="loading" class="run-button">
            运行预测
          </el-button>
        </el-card>
      </el-aside>

      <!-- 右侧主内容区 -->
      <el-main class="main-content">
        <div class="header-section">
          <h1>相似K线类比预测系统</h1>
          <p>基于 Transformer 自编码器的历史相似性预测</p>
        </div>

        <!-- 错误提示 -->
        <div v-if="errorMessage" style="margin-bottom: 16px;">
          <el-alert type="error" :closable="true" show-icon @close="errorMessage = ''">
            <template #title>{{ errorMessage }}</template>
          </el-alert>
        </div>

        <!-- 相似窗口结果 -->
        <el-card v-if="similarWindows.length > 0" class="result-card">
          <template #header>
            <div class="card-header">
              <span>最相似的历史窗口</span>
            </div>
          </template>
          <el-table :data="similarWindows" stripe>
            <el-table-column label="窗口天数" width="100" sortable>
              <template #default="scope">
                {{ (scope.row.window_preview && scope.row.window_preview.dates) ? scope.row.window_preview.dates.length : '-' }} 天
              </template>
            </el-table-column>
            <el-table-column prop="start_date" label="起始日期" width="150" />
            <el-table-column prop="end_date" label="截止日期" width="150" />
            <el-table-column prop="similarity" label="余弦相似度" width="120">
              <template #default="scope">
                <el-progress :percentage="Math.round(scope.row.similarity * 100)" :format="() => scope.row.similarity.toFixed(4)" />
              </template>
            </el-table-column>
            <el-table-column prop="final_score" label="综合分" width="120" sortable>
              <template #default="scope">
                <span v-if="scope.row.final_score !== undefined">{{ Number(scope.row.final_score).toFixed(4) }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="sim_corr" label="相关" width="100" sortable>
              <template #default="scope">
                <span v-if="scope.row.sim_corr !== undefined">{{ Number(scope.row.sim_corr).toFixed(4) }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
            <el-table-column prop="sim_dtw" label="DTW" width="100" sortable>
              <template #default="scope">
                <span v-if="scope.row.sim_dtw !== undefined">{{ Number(scope.row.sim_dtw).toFixed(4) }}</span>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>
        </el-card>

        <!-- K线图（Plotly） -->
        <el-card class="chart-card">
          <template #header>
            <div class="card-header">
              <span>K线预测图（Plotly）</span>
              <div class="chart-actions">
                <el-button size="small" @click="exportChart" :disabled="!plotlyHtml">导出图表</el-button>
                <el-button size="small" @click="exportData" :disabled="!chartData">导出数据</el-button>
              </div>
            </div>
          </template>
          <div class="chart-container">
            <iframe v-if="plotlyHtml"
                    :srcdoc="plotlyHtml"
                    style="width: 100%; height: 600px; border: none; background: white;"
                    sandbox="allow-scripts allow-same-origin"
                    @load="onIframeLoad" />
            <div v-else-if="!loading" class="empty-state">
              <el-empty description="请设置参数并点击运行开始预测" />
            </div>
          </div>
        </el-card>
      </el-main>
    </el-container>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { predictAPI, getFeaturesAPI, generateChartAPI } from '@/api/stock'

function formatYmd(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

// 状态
const loading = ref(false)
const plotlyHtml = ref('')
const chartData = ref(null)
const similarWindows = ref([])
const errorMessage = ref('')

// 特征选择状态
const useCustomFeatures = ref(false)
const selectedFeatures = ref([])
const activeFeatureGroups = ref([])
const featureNameMap = ref({})
const featureGroups = ref({})

// 其他状态
const showPaths = ref(true)
const similarityType = ref('shape')
const showAdvancedSettings = ref(false)

// 参数
const params = reactive({
  symbol: '000001.SH',
  startDate: '20200101',
  endDate: formatYmd(),
  window: 30,
  h_future: 1,
  epochs: 20,
  topk: 5,
  engine: 'ml',
  // 相似度重排（与后端一致）
  useCorr: true,
  useDtw: true,
  alphaCos: 0.5,
  betaCorr: 0.3,
  gammaDtw: 0.2,
  strictness: 0.0,
  reRankTop: 30
})

const useWindowZscore = computed(() => similarityType.value === 'shape')

const computeSimilarityWeights = () => {
  const cosWeight = Math.max(0, Number(params.alphaCos) || 0)
  const corrRaw = Math.max(0, Number(params.betaCorr) || 0)
  const dtwRaw = Math.max(0, Number(params.gammaDtw) || 0)
  const corrWeight = params.useCorr ? corrRaw : 0
  const dtwWeight = params.useDtw ? dtwRaw : 0
  const total = cosWeight + corrWeight + dtwWeight

  if (total <= 0) {
    const fallbackCos = 0.5
    const fallbackCorr = params.useCorr ? 0.3 : 0
    const fallbackDtw = params.useDtw ? 0.2 : 0
    const fallbackSum = fallbackCos + fallbackCorr + fallbackDtw
    if (fallbackSum <= 0) {
      return { alpha: 1, beta: 0, gamma: 0 }
    }
    return {
      alpha: Number((fallbackCos / fallbackSum).toFixed(4)),
      beta: Number((fallbackCorr / fallbackSum).toFixed(4)),
      gamma: Number((fallbackDtw / fallbackSum).toFixed(4))
    }
  }

  return {
    alpha: Number((cosWeight / total).toFixed(4)),
    beta: Number((corrWeight / total).toFixed(4)),
    gamma: Number((dtwWeight / total).toFixed(4))
  }
}

const weightSum = computed(() => {
  const cosWeight = Math.max(0, Number(params.alphaCos) || 0)
  const corrWeight = params.useCorr ? Math.max(0, Number(params.betaCorr) || 0) : 0
  const dtwWeight = params.useDtw ? Math.max(0, Number(params.gammaDtw) || 0) : 0
  return cosWeight + corrWeight + dtwWeight
})

const normalizedWeightPreview = computed(() => computeSimilarityWeights())
const showWeightWarning = computed(() => weightSum.value <= 0)

onMounted(async () => {
  await loadFeatures()
})

const loadFeatures = async () => {
  try {
    const res = await getFeaturesAPI()
    featureNameMap.value = res.feature_map
    featureGroups.value = res.feature_groups
  } catch (error) {
    ElMessage.error('加载特征列表失败')
  }
}

// 特征选择
const selectAllFeatures = () => {
  selectedFeatures.value = Object.values(featureGroups.value).flat()
}
const clearFeatures = () => {
  selectedFeatures.value = []
}
const selectRecommended = () => {
  selectedFeatures.value = ['RSI_Signal', 'MACD_Diff', 'K_D_Diff', 'Bollinger_Width', 'OBV', 'VWAP', 'ADX_14', 'volume_Change']
}

// 运行预测
const runPrediction = async () => {
  loading.value = true
  errorMessage.value = ''
  try {
    const normalizedWeights = normalizedWeightPreview.value
    const requestData = {
      symbol: params.symbol,
      start_date: params.startDate,
      end_date: params.endDate,
      window: params.window,
      epochs: params.epochs,
      topk: params.topk,
      engine: params.engine,
      use_window_zscore: useWindowZscore.value,
      selected_features: useCustomFeatures.value ? selectedFeatures.value : null,
      h_future: params.h_future,
      // 固定屏蔽最近30个交易日
      min_gap_days: 30,
      lookback: 100,
      show_paths: showPaths.value,
      agg: 'median',
      // 相似度重排参数
      use_corr: params.useCorr,
      use_dtw: params.useDtw,
      alpha_cos: normalizedWeights.alpha,
      beta_corr: normalizedWeights.beta,
      gamma_dtw: normalizedWeights.gamma,
      strictness: params.strictness,
      re_rank_top: params.reRankTop
    }

    const [predResponse, chartResponse] = await Promise.all([
      predictAPI(requestData),
      generateChartAPI(requestData)
    ])

    if (predResponse.status === 'success') {
      similarWindows.value = predResponse.similar_windows || []
      chartData.value = predResponse.data
    }

    if (chartResponse.status === 'success') {
      plotlyHtml.value = chartResponse.html
      ElMessage.success('预测成功')
    }
  } catch (error) {
    const detail = error?.response?.data?.detail || error?.message || '未知错误'
    errorMessage.value = '预测请求失败：' + detail
    ElMessage.error(errorMessage.value)
  } finally {
    loading.value = false
  }
}

// 导出
const exportChart = () => {
  if (!plotlyHtml.value) return
  window.print()
  ElMessage.success('请使用浏览器打印保存图表')
}
const exportData = () => {
  if (!chartData.value) return
  const dataStr = JSON.stringify(chartData.value, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.download = 'prediction-data.json'
  link.href = url
  link.click()
  ElMessage.success('数据已导出')
}

const onIframeLoad = () => {}
</script>

<style scoped lang="scss">
.main-container {
  height: 100vh;
  .el-container { height: 100%; }

  .params-panel {
    background-color: #fff;
    border-right: 1px solid #e4e7ed;
    overflow-y: auto;
    .params-card {
      height: 100%;
      border: none;
      border-radius: 0;
      .card-header { display: flex; align-items: center; gap: 8px; font-size: 16px; font-weight: bold; }
      .param-section { margin-bottom: 24px; }
      .feature-selector { margin-top: 12px; }
      .feature-checkbox { display: block; margin: 8px 0; }
      .weight-meta { margin-top: 12px; font-size: 12px; color: #606266; }
      .weight-meta__line { margin: 4px 0; }
      .weight-alert { margin-bottom: 8px; }
      .run-button { width: 100%; height: 40px; font-size: 16px; }
    }
  }

  .main-content {
    padding: 20px; overflow-y: auto;
    .header-section { margin-bottom: 16px; }
    .result-card, .chart-card { margin-bottom: 16px; }
    .chart-container { min-height: 600px; width: 100%; }
    .empty-state { height: 500px; display: flex; align-items: center; justify-content: center; }
  }
}
</style>
