<!--
===============================================================================
股价预测系统 - 主界面组件 (ModernView.vue)
===============================================================================

【文件说明】
这是整个前端应用的核心UI组件,实现了股价预测系统的完整用户界面。
采用Vue 3 Composition API + Element Plus构建现代化响应式界面。

【主要功能模块】

一、顶部导航栏 (.navbar)
- 侧边栏折叠开关
- 系统标题和Logo
- 主题切换按钮(深色/浅色模式)
- 用户菜单(导出数据、帮助文档、关于系统)
- 加载状态指示器

二、侧边栏配置面板 (.sidebar)
- 数据配置区
  * 标的代码输入 (支持股票和指数)
  * 时间范围选择器 (起始/结束日期)
  * 基准周期滑块 (window参数,1-20天)

- 模型参数区
  * 预测方式选择 (中位数/均值/保守/激进)
  * TopK值设置 (相似窗口数量)
  * 模型类型选择 (Transformer/LSTM/GRU等)

- 高级设置区(可折叠)
  * 训练轮数调节
  * 置信度阈值设置
  * 结果稳定性开关(固定随机种子)

- 特征选择
  * 技术指标选择按钮(打开弹窗)
  * 已选特征数量显示

- 操作按钮
  * 开始预测按钮(主要操作)

三、主内容区 (.main-content)
- 统计卡片组 (.stats-grid)
  * 预测收盘价卡片
  * 涨跌幅卡片
  * 预测准确度卡片
  * 数据天数卡片

- 图表展示区 (.chart-container)
  * Plotly交互式K线图(iframe渲染)
  * 预测周期滑块(浮动面板,1-10天可调)
  * 图表工具栏(刷新、导出PNG/SVG/HTML)
  * 相似窗口详情卡片

四、弹窗组件
- 特征选择弹窗 (featureDialogVisible)
  * 按类别分组的技术指标复选框
  * 全选/清空功能

- 帮助文档弹窗 (helpDialogVisible)
  * 使用说明文档

- 工作原理弹窗 (howItWorksDialogVisible)
  * 算法流程图和说明

- 关于系统弹窗 (aboutDialogVisible)
  * 版本信息和开发团队

【核心数据状态】

params (预测参数对象):
{
  symbol: "000001.SH",        // 标的代码
  start_date: "20220101",     // 起始日期
  end_date: "YYYYMMDD",       // 结束日期（默认使用当天）
  window: 5,                  // 基准周期(天)
  h_future: 5,                // 预测天数(动态可调)
  epochs: 20,                 // 训练轮数
  topk: 5,                    // TopK值
  selected_features: [],      // 已选特征
  use_fixed_seed: true,       // 结果稳定性
  random_seed: 42,            // 随机种子
  agg: "median",              // 聚合方法
  modelType: "transformer"    // 模型类型
}

chartData (图表数据):
{
  html: "",                   // Plotly图表HTML
  historical_data: [],        // 历史K线数据
  predictions: [],            // 预测K线数据
  similar_windows: []         // 相似窗口列表
}

【关键方法说明】

handlePredict():
  执行预测的主函数
  1. 参数验证
  2. 调用predictAPI发起预测请求
  3. 解析返回数据
  4. 调用generateChartAPI生成图表
  5. 更新UI显示结果

updateChart():
  更新图表显示(不重新预测)
  当用户拖动"预测周期滑块"时调用

exportData():
  导出预测数据
  支持JSON、PNG、SVG、HTML多种格式

loadFeatures():
  加载可用技术指标列表
  页面初始化时调用getFeaturesAPI

toggleTheme():
  切换深色/浅色主题
  修改isDarkMode状态并同步到localStorage

【响应式布局】
- 桌面端: 侧边栏+主内容区双栏布局
- 平板: 侧边栏可折叠,主内容区自适应
- 移动端: 优先竖屏自适应,侧边栏自动折叠

【主题系统】
支持深色/浅色两套主题,CSS变量定义在global.scss中:
- --bg-primary, --bg-secondary: 背景色
- --text-primary, --text-muted: 文字色
- --primary, --success, --warning: 主题色

【项目中的用途】
- 作为单页应用的唯一路由页面
- 集成所有用户交互逻辑
- 连接前端UI与后端预测引擎
- 提供可视化的预测结果展示

【性能优化】
- 使用v-show而非v-if减少DOM操作
- 图表使用iframe隔离避免主线程阻塞
- 防抖处理滑块拖动事件
- 按需加载Element Plus图标组件

【作者】前端主界面
【更新日期】2024-10
===============================================================================
-->
<template>
  <div class="app-container" :class="{ 'dark-mode': isDarkMode, 'mobile-portrait': isMobilePortrait }">
    <!-- 顶部导航栏 -->
    <nav class="navbar">
      <div class="navbar-content">
        <div class="navbar-left">
          <button class="menu-toggle" @click="toggleSidebar">
            <el-icon :size="20">
              <component :is="sidebarCollapsed ? 'Expand' : 'Fold'" />
            </el-icon>
          </button>
          <div class="brand">
            <div class="brand-icon">
              <svg width="28" height="28" viewBox="0 0 24 24">
                <path fill="currentColor" d="M3 13h2v-2H3v2zm0 4h2v-2H3v2zm0-8h2V7H3v2zm4 4h14v-2H7v2zm0 4h14v-2H7v2zM7 7v2h14V7H7z"/>
              </svg>
            </div>
            <h1 class="brand-title">智能K线预测系统</h1>
          </div>
        </div>

        <div class="navbar-right">
          <div class="status-indicator" v-if="loading">
            <el-icon class="loading-icon"><Loading /></el-icon>
            <span>正在预测...</span>
          </div>

          <el-tooltip content="切换主题">
            <button class="theme-toggle" @click="toggleTheme">
              <el-icon :size="20">
                <component :is="isDarkMode ? 'Sunny' : 'Moon'" />
              </el-icon>
            </button>
          </el-tooltip>

          <el-dropdown class="user-menu">
            <div class="user-avatar">
              <el-icon :size="24"><User /></el-icon>
            </div>
            <template #dropdown>
              <el-dropdown-menu>
                <el-dropdown-item @click="exportData">
                  <el-icon><Download /></el-icon> 导出数据
                </el-dropdown-item>
                <el-dropdown-item @click="showHelp">
                  <el-icon><QuestionFilled /></el-icon> 如何使用
                </el-dropdown-item>
                <el-dropdown-item @click="showHowItWorks">
                  <el-icon><Opportunity /></el-icon> 工作原理
                </el-dropdown-item>
                <el-dropdown-item divided @click="showAbout">
                  <el-icon><InfoFilled /></el-icon> 关于系统
                </el-dropdown-item>
              </el-dropdown-menu>
            </template>
          </el-dropdown>
        </div>
      </div>
    </nav>

    <div class="main-layout">
      <!-- 侧边栏 -->
      <aside
        v-if="!isMobileView"
        class="sidebar"
        :class="{ collapsed: sidebarCollapsed }"
      >
        <div class="sidebar-content">
          <div class="sidebar-section fade-in">
            <h3 class="section-title">
              <el-icon><DataLine /></el-icon>
              <span v-show="!sidebarCollapsed">数据配置</span>
            </h3>
            <div class="form-group" v-show="true">
              <label>
                标的代码
                <el-tooltip content="输入股票或指数代码，例如：000001.SH 代表上证指数" placement="right">
                  <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </label>
              <el-input
                v-model="params.symbol"
                placeholder="例：000001.SH"
                prefix-icon="Ticket"
                size="small"
              />
            </div>
            <div class="form-group" v-show="false && !sidebarCollapsed">
              <label>
                训练起始时间
                <el-tooltip content="选择历史数据的开始日期" placement="right">
                  <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </label>
              <el-config-provider :locale="zhCn">
                <el-date-picker
                  v-model="params.startDate"
                  type="date"
                  format="YYYY-MM-DD"
                  value-format="YYYYMMDD"
                  placeholder="选择开始日期"
                  style="width: 100%"
                  size="small"
                />
              </el-config-provider>
            </div>
            <div class="form-group" v-show="false && !sidebarCollapsed">
              <label>
                训练截止时间
                <el-tooltip content="选择历史数据的结束日期，数据越多预测越准确" placement="right">
                  <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                </el-tooltip>
              </label>
              <el-config-provider :locale="zhCn">
                <el-date-picker
                  v-model="params.endDate"
                  type="date"
                  format="YYYY-MM-DD"
                  value-format="YYYYMMDD"
                  placeholder="选择结束日期"
                  style="width: 100%"
                  size="small"
                />
              </el-config-provider>
            </div>
          </div>

          <div class="sidebar-section fade-in" style="animation-delay: 0.1s" v-if="false">
            <h3 class="section-title">
              <el-icon><Operation /></el-icon>
              <span v-show="!sidebarCollapsed">基本设置</span>
            </h3>
            <div v-show="!sidebarCollapsed">
              <div class="form-group">
                <label>
                  基准周期
                  <el-tooltip content="使用最近几天的走势作为参考模式，用于寻找历史相似形态" placement="right">
                    <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-slider
                  v-model="params.window"
                  :min="1"
                  :max="100"
                  :marks="{
                    1: '1天',
                    10: '10天',
                    30: '30天',
                    60: '60天',
                    100: '100天'
                  }"
                  :show-tooltip="true"
                />
              </div>

              <div class="form-group">
                <label>
                  预测周期
                  <el-tooltip content="预测未来多少天的走势" placement="right">
                    <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-slider
                  v-model="params.h_future"
                  :min="1"
                  :max="30"
                  :marks="{
                    1: '1天',
                    5: '5天',
                    10: '10天',
                    20: '20天',
                    30: '30天'
                  }"
                  :show-tooltip="true"
                />
              </div>

              <div class="form-group">
                <label>
                  相似窗口数
                  <el-tooltip content="从历史中找几个相似的走势作为参考，越多越稳定" placement="right">
                    <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-radio-group v-model="params.topk" size="small">
                  <el-radio-button :label="3">3个</el-radio-button>
                  <el-radio-button :label="5">5个</el-radio-button>
                  <el-radio-button :label="8">8个</el-radio-button>
                  <el-radio-button :label="10">10个</el-radio-button>
                </el-radio-group>
              </div>
            </div>
          </div>

          <div class="sidebar-section fade-in" style="animation-delay: 0.15s">
            <div class="section-title collapsible" @click="showAdvancedSettings = !showAdvancedSettings" v-show="!sidebarCollapsed">
              <div style="display: flex; align-items: center; gap: 8px; flex: 1;">
                <el-icon><Setting /></el-icon>
                <span>高级设置</span>
              </div>
              <el-icon :class="['collapse-icon', { 'collapsed': !showAdvancedSettings }]">
                <ArrowDown />
              </el-icon>
            </div>
            <el-collapse-transition>
            <div v-show="!sidebarCollapsed && showAdvancedSettings">
              <!-- 基准设置（已从独立栏移动至高级设置） -->
              <div class="form-group">
                <label>
                  标准窗口
                  <el-tooltip content="使用最近窗口作为参考模式，去寻找历史段落形态" placement="right">
                    <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-slider
                  v-model="params.window"
                  :min="1"
                  :max="100"
                  :marks="{
                    1: '1天',
                    10: '10天',
                    30: '30天',
                    60: '60天',
                    100: '100天'
                  }"
                  :show-tooltip="true"
                />
              </div>

              <div class="form-group" v-if="!isMobileView">
                <label>
                  预测周期
                  <el-tooltip content="预测未来的天数长度" placement="right">
                    <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-slider
                  v-model="params.h_future"
                  :min="1"
                  :max="30"
                  :marks="{
                    1: '1天',
                    5: '5天',
                    10: '10天',
                    20: '20天',
                    30: '30天'
                  }"
                  :show-tooltip="true"
                />
              </div>

              <div class="form-group">
                <label>
                  相似段数
                  <el-tooltip content="历史参考段越多越稳健" placement="right">
                    <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                  </el-tooltip>
                </label>
                <el-radio-group v-model="params.topk" size="small">
                  <el-radio-button :label="3">3段</el-radio-button>
                  <el-radio-button :label="5">5段</el-radio-button>
                  <el-radio-button :label="8">8段</el-radio-button>
                  <el-radio-button :label="10">10段</el-radio-button>
                </el-radio-group>
              </div>
                <div class="form-group">
                  <label>
                    预测方式
                    <el-tooltip content="选择如何综合历史数据：中位数最稳定，均值较平衡，保守偏谨慎" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <el-select v-model="params.predictionMethod" placeholder="选择预测方式" style="width: 100%">
                    <el-option label="中位数预测（稳健）" value="median">
                      <span style="float: left">中位数预测</span>
                      <span style="float: right; color: #8492a6; font-size: 12px">推荐</span>
                    </el-option>
                    <el-option label="均值预测（平衡）" value="mean">
                      <span style="float: left">均值预测</span>
                      <span style="float: right; color: #8492a6; font-size: 12px">平衡</span>
                    </el-option>
                    <el-option label="保守预测（谨慎）" value="conservative">
                      <span style="float: left">保守预测</span>
                      <span style="float: right; color: #8492a6; font-size: 12px">谨慎</span>
                    </el-option>
                    <el-option label="乐观预测（激进）" value="best">
                      <span style="float: left">乐观预测</span>
                      <span style="float: right; color: #8492a6; font-size: 12px">激进</span>
                    </el-option>
                  </el-select>
                </div>

                <div class="form-group">
                  <label>
                    预测模型
                    <el-tooltip content="AI模型类型，Transformer标准模型适合大多数情况" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <el-select v-model="params.modelType" placeholder="选择模型类型" style="width: 100%" :disabled="params.engine === 'classic'">
                    <el-option label="标准模型（推荐）" value="transformer" />
                    <el-option label="长期记忆模型" value="transformer_lstm" />
                    <el-option label="高效模型" value="transformer_gru" />
                    <el-option label="形态识别模型" value="cnn_transformer" />
                  </el-select>
                </div>

                <div class="form-group">
                  <label>
                    算法模式
                    <el-tooltip content="选择传统匹配可跳过深度学习训练，使用标准化距离进行相似度计算" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <el-radio-group v-model="params.engine" size="small">
                    <el-radio-button label="ml">深度学习</el-radio-button>
                    <el-radio-button label="classic">传统匹配</el-radio-button>
                  </el-radio-group>
                </div>

                <div class="form-group">
                  <label>
                    逐日评估
                    <el-tooltip content="开启后将从指定日期起逐日回测1天涨跌幅" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <el-switch
                    v-model="params.evaluateDaily"
                    active-text="开启"
                    inactive-text="关闭"
                    style="margin-bottom: 8px; width: 100%;"
                  />
                  <el-date-picker
                    v-if="params.evaluateDaily"
                    v-model="params.evaluationStart"
                    type="date"
                    placeholder="评估起始日期"
                    value-format="YYYYMMDD"
                    style="width: 100%;"
                  />
                </div>

                <div class="form-group">
                  <label>
                    训练轮数
                    <el-tooltip content="AI学习的次数，次数越多越精确但速度越慢，20轮适合日常使用" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <el-slider
                    v-model="params.epochs"
                    :min="5"
                    :max="100"
                    :step="5"
                    :show-tooltip="true"
                    :marks="{
                      5: '快速',
                      20: '标准',
                      50: '精确',
                      100: '深度'
                    }"
                  />
                </div>

                <div class="form-group">
                  <label>
                    置信度阈值
                    <el-tooltip content="相似度要求，越高越严格，找到的历史参考越少但更准确" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <el-slider
                    v-model="params.strictness"
                    :min="0.5"
                    :max="0.95"
                    :step="0.05"
                    :format-tooltip="val => `${(val * 100).toFixed(0)}%`"
                    :show-tooltip="true"
                    :marks="{
                      0.5: '宽松',
                      0.75: '标准',
                      0.95: '严格'
                    }"
                  />
                </div>

                <div class="form-group">
                  <label>
                    相似度权重
                    <el-tooltip content="调节余弦/相关/DTW 在综合评分中的占比，可关闭不需要的指标" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <el-switch
                    v-model="params.useCorr"
                    active-text="启用相关度"
                    inactive-text="忽略相关度"
                    style="margin-bottom: 8px; width: 100%;"
                  />
                  <el-switch
                    v-model="params.useDtw"
                    active-text="启用 DTW"
                    inactive-text="忽略 DTW"
                    style="margin-bottom: 12px; width: 100%;"
                  />
                  <div class="weight-block">
                    <span class="weight-block__label">余弦权重</span>
                    <el-slider v-model="params.alphaCos" :min="0" :max="1" :step="0.05" show-input />
                  </div>
                  <div class="weight-block">
                    <span class="weight-block__label">相关权重</span>
                    <el-slider
                      v-model="params.betaCorr"
                      :min="0"
                      :max="1"
                      :step="0.05"
                      show-input
                      :disabled="!params.useCorr"
                    />
                  </div>
                  <div class="weight-block">
                    <span class="weight-block__label">DTW 权重</span>
                    <el-slider
                      v-model="params.gammaDtw"
                      :min="0"
                      :max="1"
                      :step="0.05"
                      show-input
                      :disabled="!params.useDtw"
                    />
                  </div>
                  <div class="weight-meta">
                    <el-alert
                      v-if="showWeightWarning"
                      type="warning"
                      show-icon
                      :closable="false"
                      class="weight-alert"
                    >
                      <template #title>权重总和为 0，将自动回退到默认配比</template>
                    </el-alert>
                    <p class="weight-meta__line">当前设定总权重：{{ (weightSum * 100).toFixed(1) }}%</p>
                    <p class="weight-meta__line">
                      归一化比重 → 余弦 {{ (normalizedWeightPreview.alpha * 100).toFixed(1) }}%
                      ｜ 相关 {{ (normalizedWeightPreview.beta * 100).toFixed(1) }}%
                      ｜ DTW {{ (normalizedWeightPreview.gamma * 100).toFixed(1) }}%
                    </p>
                  </div>
                </div>

                <div class="form-group">
                  <label>
                    结果稳定性
                    <el-tooltip content="固定模式每次预测结果相同，便于比较；随机模式更接近真实市场" placement="right">
                      <el-icon style="color: var(--text-muted); margin-left: 4px;"><QuestionFilled /></el-icon>
                    </el-tooltip>
                  </label>
                  <div>
                    <el-switch
                      v-model="params.useFixedSeed"
                      active-text="固定结果"
                      inactive-text="随机结果"
                      style="margin-bottom: 8px;"
                    />
                    <div>
                      <el-tag v-if="params.useFixedSeed" type="info" size="small" style="width: 100%; justify-content: center;">
                        每次预测结果相同
                      </el-tag>
                      <el-tag v-else type="warning" size="small" style="width: 100%; justify-content: center;">
                        每次预测略有差异
                      </el-tag>
                    </div>
                  </div>
                </div>

                <div class="form-group" v-if="false">
                  <label>预测风格</label>
                  <el-radio-group v-model="params.predictionStyle" size="small">
                    <el-radio-button label="normal">常规</el-radio-button>
                    <el-radio-button label="aggressive">激进</el-radio-button>
                    <el-radio-button label="conservative">保守</el-radio-button>
                  </el-radio-group>
                </div>
              </div>
            </el-collapse-transition>
          </div>

          <div class="sidebar-section fade-in" style="animation-delay: 0.2s">
            <h3 class="section-title">
              <el-icon><Filter /></el-icon>
              <span v-show="!sidebarCollapsed">特征选择</span>
            </h3>
            <div v-show="!sidebarCollapsed">
              <el-switch
                v-model="useCustomFeatures"
                active-text="自定义"
                inactive-text="全部"
                style="margin-bottom: 12px"
              />
              <div v-if="useCustomFeatures" class="feature-controls">
                <div class="feature-quick-select">
                  <el-button size="small" @click="selectAllFeatures">全选</el-button>
                  <el-button size="small" @click="selectRecommended">推荐</el-button>
                  <el-button size="small" @click="clearFeatures">清空</el-button>
                </div>
              <div v-if="cacheList && cacheList.length" style="margin-top: 8px;">
                <div style="font-weight: 500; margin-bottom: 6px; color: var(--text-primary);">缓存列表</div>
                <div style="max-height: 160px; overflow: auto;">
                  <div v-for="item in cacheList" :key="item.cache_key" style="display:flex; justify-content:space-between; font-size: 12px; padding: 4px 0; border-bottom: 1px dashed var(--border-color);">
                    <span>{{ item.params?.symbol || item.cache_key }}</span>
                    <span>{{ (item.file_size / (1024*1024)).toFixed(1) }} MB</span>
                  </div>
                </div>
              </div>
                <el-button
                  size="small"
                  type="primary"
                  @click="showFeatureDialog = true"
                  style="margin-top: 8px; width: 100%"
                >
                  <el-icon><Setting /></el-icon> 选择特征
                </el-button>
                <el-tag v-if="selectedFeatures.length > 0" type="info" style="margin-top: 8px">
                  已选 {{ selectedFeatures.length }} 个特征
                </el-tag>
              </div>
            </div>
          </div>

          <div class="sidebar-footer" v-show="!sidebarCollapsed">
            <!-- 缓存状态信息 -->
            <div class="cache-status-box" v-if="cacheStats.cache_enabled" style="margin-bottom: 12px; padding: 12px; background: var(--bg-tertiary); border-radius: 8px;">
              <div style="display: flex; align-items: center; margin-bottom: 8px;">
                <el-icon :color="cacheStatus === 'hit' ? '#67c23a' : '#909399'">
                  <Opportunity />
                </el-icon>
                <span style="margin-left: 8px; font-size: 14px; font-weight: 500;">模型缓存</span>
                <el-tag
                  :type="cacheStatus === 'hit' ? 'success' : cacheStatus === 'miss' ? 'warning' : 'info'"
                  size="small"
                  style="margin-left: auto;"
                >
                  {{ cacheStatus === 'hit' ? '已缓存' : cacheStatus === 'miss' ? '未缓存' : cacheStatus === 'checking' ? '检查中' : '未知' }}
                </el-tag>
              </div>
              <div v-if="cacheStats.stats" style="font-size: 12px; color: var(--text-muted);">
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <span>标的代码：</span>
                  <span>{{ params.symbol }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <span>维度：</span>
                  <span>{{ useCustomFeatures ? (selectedFeatures.length || 0) : (modelInfo?.feature_count || allFeatures.length || 0) }}</span>
                </div>
                <div style="display: flex; justify-content: space-between; margin-bottom: 4px;">
                  <span>缓存数量：</span>
                  <span>{{ cacheStats.stats.cache_count || 0 }} 个</span>
                </div>
                <div style="display: flex; justify-content: space-between;">
                  <span>占用空间：</span>
                  <span>{{ (cacheStats.stats.total_size_mb || 0).toFixed(1) }} MB</span>
                </div>
                <el-button
                  text
                  size="small"
                  @click="handleClearCache"
                  style="margin-top: 8px; width: 100%;"
                >
                  清空所有缓存
                </el-button>
              </div>
            </div>

            <el-button
              class="help-button"
              @click="showHowItWorks = true"
              :icon="Opportunity"
            >
              <span>💡 了解工作原理</span>
            </el-button>
            <el-button
              type="primary"
              class="run-button"
              @click="runPrediction"
              :loading="loading"
              :icon="VideoPlay"
            >
              开始预测
            </el-button>
          </div>
        </div>
      </aside>

      <!-- 主内容区 -->
      <main class="main-content">
        <section class="mobile-quick-panel" v-if="isMobileView">
          <div class="quick-header">
            <p class="quick-label">移动端快速预测</p>
            <strong class="quick-title">一键获取最新走势</strong>
          </div>
          <div class="quick-meta">
            <div class="meta-item">
              <span class="label">默认标的</span>
              <span class="value">{{ params.symbol }}</span>
            </div>
          </div>
          <el-button
            class="quick-action"
            type="primary"
            size="large"
            :loading="loading"
            @click="handleQuickPredict"
          >
            <el-icon :size="20"><VideoPlay /></el-icon>
            <span>快速预测</span>
          </el-button>
          <p class="quick-hint">移动端使用系统推荐参数，更多设置请在桌面端打开</p>
        </section>
        <!-- 统计卡片 -->
        <div class="stats-grid">
          <div class="stat-card modern-card fade-in">
            <div class="stat-icon">
              <el-icon :size="24"><TrendCharts /></el-icon>
            </div>
            <div class="stat-content">
              <h4>股票代码</h4>
              <p class="stat-value">{{ params.symbol }}</p>
              <span class="stat-label">上证指数</span>
            </div>
          </div>

          <div v-if="tomorrowPrediction && tomorrowPrediction.return !== null" class="stat-card modern-card fade-in" style="animation-delay: 0.05s">
            <div class="stat-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
              <el-icon :size="24"><TrendCharts /></el-icon>
            </div>
            <div class="stat-content">
              <h4>明日预测结果</h4>
              <p class="stat-value" style="font-size: 14px;">{{ tomorrowPrediction?.date || '-' }}</p>
              <div class="similar-day-details">
                <el-tag size="small" :type="getReturnTagType(tomorrowPrediction.return)">
                  {{ formatPercent(tomorrowPrediction.return) }}
                </el-tag>
              </div>
            </div>
          </div>          <!-- 最相似交易日卡片 - 改为显示相似窗口的最后一天 -->
          <div v-if="similarWindows && similarWindows.length > 0" class="stat-card modern-card fade-in" style="animation-delay: 0.1s">
            <div class="stat-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
              <el-icon :size="24"><Calendar /></el-icon>
            </div>
            <div class="stat-content">
              <h4>与今日最相似历史行情</h4>
              <p class="stat-value" style="font-size: 14px;">{{ similarWindows[0]?.end_date || '-' }}</p>
              <div class="similar-day-details">
                <el-tag size="small" type="success" style="margin-right: 4px;">
                  相似度 {{ ((similarWindows[0]?.similarity || 0) * 100).toFixed(1) }}%
                </el-tag>
                <el-tooltip
                  :content="`该窗口未来走势: ${similarWindows[0]?.future_return ? (similarWindows[0].future_return >= 0 ? '+' : '') + (similarWindows[0].future_return * 100).toFixed(2) + '%' : '无数据'}`"
                  placement="bottom"
                >
                  <el-tag size="small" :type="(similarWindows[0]?.future_return || 0) >= 0 ? 'danger' : 'success'">
                    {{ similarWindows[0]?.future_return ? ((similarWindows[0].future_return >= 0 ? '+' : '') + (similarWindows[0].future_return * 100).toFixed(2) + '%') : '--' }}
                  </el-tag>
                </el-tooltip>
                <el-tag size="small" type="info" style="margin-left: 4px;">
                  维度 {{ selectedFeatures.length > 0 ? selectedFeatures.length : (modelInfo?.feature_count || '--') }}
                </el-tag>
              </div>
            </div>
          </div>
        </div>

        <!-- 相似窗口结果（移动端隐藏） -->
        <div v-if="!isMobileView && similarWindows.length > 0" class="result-section fade-in">
          <div class="section-header">
            <h2>
              <el-icon><Search /></el-icon>
              历史相似窗口
            </h2>
          </div>
          <div class="similar-windows-scroll">
            <div class="similar-windows-row">
              <div
              v-for="(window, index) in similarWindows"
              :key="index"
              class="window-card-compact modern-card"
              :class="{ 'primary-match': index === 0 }"
              :style="{ animationDelay: `${index * 0.08}s` }"
            >
              <div class="window-rank">#{{ index + 1 }}</div>
              <div class="similarity-badge" :class="getSimilarityClass(window.similarity)">
                {{ (window.similarity * 100).toFixed(1) }}%
              </div>
              <div class="window-dates-compact">
                <div class="date-range">{{ window.start_date }} ~ {{ window.end_date }}</div>
              </div>

              <!-- K线图 -->
              <div class="window-kline" v-if="!isMobileView && window.window_preview && window.window_preview.close">
                <MiniKline :data="window.window_preview" :height="80" />
              </div>

              <div class="window-metrics">
                <el-tag size="small" :type="getReturnTagType(window.window_return)" effect="plain">
                  历史 {{ formatReturn(window.window_return) }}
                </el-tag>
                <el-tag size="small" :type="getReturnTagType(window.future_return)" effect="plain">
                  未来 {{ formatReturn(window.future_return) }}
                </el-tag>
              </div>
              <div class="window-snippet">
                <div class="snippet-row">
                  <span class="snippet-label">区间</span>
                  <span class="snippet-value">{{ getWindowSummary(window) }}</span>
                </div>
                <div
                  class="snippet-row"
                  v-if="window.future_preview && window.future_preview.dates && window.future_preview.dates.length"
                >
                  <span class="snippet-label">未来</span>
                  <span class="snippet-value">{{ getFutureSummary(window) }}</span>
                </div>
              </div>
              <div
                class="preview-values"
                v-if="window.window_preview && getPreviewPoints(window.window_preview).length"
              >
                <span
                  class="preview-pill"
                  v-for="point in getPreviewPoints(window.window_preview)"
                  :key="`${window.window_index}-w-${point.date}`"
                >
                  {{ point.date }} ￥{{ formatPrice(point.close) }}
                </span>
              </div>
              <div
                class="preview-values future"
                v-if="window.future_preview && getPreviewPoints(window.future_preview).length"
              >
                <span
                  class="preview-pill"
                  v-for="point in getPreviewPoints(window.future_preview)"
                  :key="`${window.window_index}-f-${point.date}`"
                >
                  {{ point.date }} ￥{{ formatPrice(point.close) }}
                </span>
              </div>
              <div class="similarity-bar">
                <div class="bar-fill" :style="{ width: (window.similarity * 100) + '%' }"></div>
              </div>
            </div>
          </div>
        </div>
        </div>

        <!-- 图表区域 -->
        <div class="chart-section modern-card fade-in" v-if="!isMobileView">
          <div class="chart-header">
            <div class="chart-title">
              <el-icon><DataAnalysis /></el-icon>
              <h2>K线预测图表</h2>
              <el-tag v-if="lastPredictionTime" size="small" effect="plain">
                更新于 {{ lastPredictionTime }}
              </el-tag>
            </div>
            <div class="chart-actions">
              <el-button-group>
                <el-button size="small" @click="zoomIn">
                  <el-icon><ZoomIn /></el-icon>
                </el-button>
                <el-button size="small" @click="resetZoom">
                  <el-icon><Refresh /></el-icon>
                </el-button>
                <el-button size="small" @click="zoomOut">
                  <el-icon><ZoomOut /></el-icon>
                </el-button>
              </el-button-group>
              <el-dropdown>
                <el-button size="small">
                  <el-icon><Download /></el-icon> 导出
                </el-button>
                <template #dropdown>
                  <el-dropdown-menu>
                    <el-dropdown-item @click="exportChart('png')">导出为PNG</el-dropdown-item>
                    <el-dropdown-item @click="exportChart('svg')">导出为SVG</el-dropdown-item>
                    <el-dropdown-item @click="exportData">导出数据JSON</el-dropdown-item>
                  </el-dropdown-menu>
                </template>
              </el-dropdown>
            </div>
          </div>

          <div class="chart-container">
            <!-- 图表iframe容器 -->

            <div v-if="loading" class="chart-loading">
              <div class="loading-container">
                <!-- 多层加载动画 -->
                <div class="loading-spinner-container">
                  <div class="loading-spinner"></div>
                  <div class="loading-pulse"></div>
                </div>

                <!-- 加载文字和进度 -->
                <div class="loading-content">
                  <p class="loading-title">模型正在进行预测</p>
                  <p class="loading-subtitle">预计需要 20-30 秒</p>

                  <!-- 进度条 -->
                  <div class="progress-bar-container">
                    <div class="progress-bar"></div>
                  </div>

                  <!-- 预处理步骤 -->
                  <div class="processing-steps">
                    <div class="step active">
                      <div class="step-icon">1</div>
                      <div class="step-text">数据预处理</div>
                    </div>
                    <div class="step">
                      <div class="step-icon">2</div>
                      <div class="step-text">模型训练</div>
                    </div>
                    <div class="step">
                      <div class="step-icon">3</div>
                      <div class="step-text">相似性搜索</div>
                    </div>
                    <div class="step">
                      <div class="step-icon">4</div>
                      <div class="step-text">生成预测</div>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <iframe
              v-else-if="currentChartHtml || plotlyHtml"
              :srcdoc="currentChartHtml || plotlyHtml"
              style="width: 100%; height: 600px; border: none; border-radius: 8px;"
              sandbox="allow-scripts allow-same-origin"
              @load="onIframeLoad"
            />
            <div v-else class="empty-chart">
              <el-empty :description="isMobileView ? '点击快速预测查看图表' : '设置参数后点击开始预测查看图表'">
                <el-button
                  type="primary"
                  @click="isMobileView ? handleQuickPredict() : scrollToParams()"
                >
                  {{ isMobileView ? '快速预测' : '配置参数' }}
                </el-button>
              </el-empty>
            </div>
          </div>
        </div>
      </main>
    </div>

    <section v-if="evaluationSummary" class="evaluation-section" :class="{ 'sidebar-expanded': !sidebarCollapsed }">
      <h3 class="section-title">
        <el-icon><DataAnalysis /></el-icon>
        <span>逐日评估结果</span>
        <el-tag :type="getEvaluationQualityType()" size="small" style="margin-left: 12px;">
          {{ getEvaluationQualityLabel() }}
        </el-tag>
      </h3>

      <!-- 评估指标卡片网格 -->
      <div class="evaluation-metrics-grid">
        <div class="metric-card">
          <div class="metric-icon" style="background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);">
            <el-icon :size="24"><Document /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">样本数</div>
            <div class="metric-value">{{ evaluationSummary.count }}</div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon" style="background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">方向准确率</div>
            <div class="metric-value" :class="getAccuracyClass(evaluationSummary.direction_accuracy)">
              {{ formatPercent(evaluationSummary.direction_accuracy) }}
            </div>
          </div>
        </div>

        <div class="metric-card">
          <div class="metric-icon" style="background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);">
            <el-icon :size="24"><Histogram /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">最近10日方向准确率</div>
            <div class="metric-value" :class="getAccuracyClass(recentDirectionStats.accuracy)">
              {{ formatPercent(recentDirectionStats.accuracy) }}
            </div>
            <div class="metric-subtext" v-if="recentDirectionStats.sampleSize">
              基于 {{ recentDirectionStats.sampleSize }} 天样本
            </div>
          </div>
        </div>

        <div class="metric-card" v-if="false">
          <div class="metric-icon" style="background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);">
            <el-icon :size="24"><Opportunity /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">平均实际收益</div>
            <div class="metric-value" :class="getReturnClass(evaluationSummary.mean_actual)">
              {{ formatPercent(evaluationSummary.mean_actual) }}
            </div>
          </div>
        </div>

        <div class="metric-card" v-if="false">
          <div class="metric-icon" style="background: linear-gradient(135deg, #43e97b 0%, #38f9d7 100%);">
            <el-icon :size="24"><DataLine /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">平均预测收益</div>
            <div class="metric-value" :class="getReturnClass(evaluationSummary.mean_predicted)">
              {{ formatPercent(evaluationSummary.mean_predicted) }}
            </div>
          </div>
        </div>

        <div class="metric-card" v-if="false">
          <div class="metric-icon" style="background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);">
            <el-icon :size="24"><Warning /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">平均绝对误差</div>
            <div class="metric-value">{{ formatNumber(evaluationSummary.mae, 4) }}</div>
          </div>
        </div>

        <div class="metric-card" v-if="false">
          <div class="metric-icon" style="background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);">
            <el-icon :size="24"><TrendCharts /></el-icon>
          </div>
          <div class="metric-content">
            <div class="metric-label">均方根误差</div>
            <div class="metric-value">{{ formatNumber(evaluationSummary.rmse, 4) }}</div>
          </div>
        </div>
      </div>

      <!-- 详细数据表格 -->
      <div class="evaluation-table-container">
        <div class="table-header">
          <span class="table-title">详细评估记录</span>
          <el-button size="small" @click="exportEvaluationData">
            <el-icon><Download /></el-icon> 导出数据
          </el-button>
        </div>
        <el-table
          :data="evaluationRecords"
          v-bind="evaluationTableProps"
          size="small"
          stripe
          :header-cell-style="{background: 'var(--bg-secondary)', color: 'var(--text-primary)', fontWeight: '600'}"
        >
          <el-table-column prop="date" label="日期" width="120" fixed />

          <el-table-column label="预测涨跌幅" width="140" sortable>
            <template #default="scope">
              <el-tag :type="getReturnTagType(scope.row.predicted_return)" effect="plain" size="small">
                {{ formatPercent(scope.row.predicted_return) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="实际涨跌幅" width="140" sortable>
            <template #default="scope">
              <el-tag :type="getReturnTagType(scope.row.actual_return)" effect="plain" size="small">
                {{ formatPercent(scope.row.actual_return) }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column label="方向判断" width="100" align="center">
            <template #default="scope">
              <el-icon
                :size="20"
                :style="{color: isDirectionCorrect(scope.row) ? 'var(--success-color)' : 'var(--danger-color)'}"
              >
                <component :is="isDirectionCorrect(scope.row) ? 'Select' : 'Close'" />
              </el-icon>
            </template>
          </el-table-column>
        </el-table>
      </div>
    </section>

    <!-- 浮动操作按钮 -->
    <div class="fab-container" v-if="!isMobileView">
      <el-tooltip content="快速预测" placement="left">
        <button class="fab primary" @click="runPrediction" v-if="!sidebarCollapsed">
          <el-icon :size="24"><VideoPlay /></el-icon>
        </button>
      </el-tooltip>
    </div>

    <!-- 特征选择对话框 -->
    <el-dialog
      v-model="showFeatureDialog"
      title="选择技术指标特征"
      width="80%"
      class="feature-dialog"
    >
      <div class="feature-dialog-content">
        <div class="feature-dialog-header">
          <el-input
            v-model="featureSearchKeyword"
            placeholder="搜索特征..."
            prefix-icon="Search"
            clearable
            style="width: 300px"
          />
          <div class="feature-stats">
            <span>已选择 {{ selectedFeatures.length }} / {{ allFeatures.length }} 个特征</span>
          </div>
        </div>

        <el-tabs v-model="activeFeatureTab">
          <el-tab-pane
            v-for="(features, groupName) in filteredFeatureGroups"
            :key="groupName"
            :label="`${featureGroupLabels[groupName] || groupName} (${features.length})`"
            :name="groupName"
          >
            <el-checkbox-group v-model="selectedFeatures" class="feature-checkbox-group">
              <div
                v-for="feature in features"
                :key="feature"
                class="feature-item"
              >
                <el-checkbox
                  :label="feature"
                  :value="feature"
                >
                  <span class="feature-name">{{ featureNameMap[feature] || feature }}</span>
                  <el-tag size="small" type="info">{{ feature }}</el-tag>
                </el-checkbox>
              </div>
            </el-checkbox-group>
          </el-tab-pane>
        </el-tabs>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <div class="footer-left">
            <el-button @click="selectAllInCurrentTab">全选当前组</el-button>
            <el-button @click="clearCurrentTab">清空当前组</el-button>
          </div>
          <div class="footer-right">
            <el-button @click="showFeatureDialog = false">取消</el-button>
            <el-button type="primary" @click="confirmFeatureSelection">
              确认选择 ({{ selectedFeatures.length }})
            </el-button>
          </div>
        </div>
      </template>
    </el-dialog>

    <!-- 工作原理说明对话框 -->
    <el-dialog
      v-model="showHowItWorksDialog"
      title="系统是如何预测股价的？"
      width="70%"
      class="how-it-works-dialog"
    >
      <div class="how-it-works-content">
        <el-tabs v-model="activeHelpTab">
          <el-tab-pane label="📖 简单说明" name="simple">
            <div class="help-section">
              <h3>🎯 核心理念：历史会重演</h3>
              <p>
                我们的系统基于一个简单的投资理念：<strong>股市的历史走势会有相似的模式重复出现</strong>。
                就像天气预报通过寻找历史上相似的天气模式来预测未来天气一样，我们通过寻找历史上相似的K线走势来预测未来股价。
              </p>

              <h3>🔍 工作流程（三步走）</h3>
              <el-steps direction="vertical" :active="3">
                <el-step title="寻找相似历史">
                  <template #description>
                    <div class="step-desc">
                      系统会分析您选择的股票最近一段时间（基准周期，比如5天）的走势特征，
                      包括价格波动、成交量变化、技术指标等，形成一个"特征指纹"。
                    </div>
                  </template>
                </el-step>
                <el-step title="历史模式匹配">
                  <template #description>
                    <div class="step-desc">
                      在过去几年的历史数据中，寻找与当前"特征指纹"最相似的时间段。
                      比如找到了2020年3月、2021年7月、2022年11月这三个相似时段。
                    </div>
                  </template>
                </el-step>
                <el-step title="生成预测结果">
                  <template #description>
                    <div class="step-desc">
                      查看这些历史相似时段之后的走势（预测周期，比如5天），通过统计分析得出最可能的未来走势。
                      如果历史上这些相似情况后大多上涨，系统就会预测未来可能上涨。
                    </div>
                  </template>
                </el-step>
              </el-steps>

              <h3>💡 通俗比喻</h3>
              <div class="analogy-box">
                <p>
                  <strong>想象您是一位经验丰富的老股民：</strong>
                </p>
                <ul>
                  <li>您见过无数次市场涨跌，积累了丰富的经验</li>
                  <li>当您看到某种熟悉的走势时，会想起"上次出现这种情况后，股价涨了"</li>
                  <li>我们的系统就是把这种"经验判断"数字化、系统化</li>
                  <li>不同的是，系统可以瞬间查阅几十年的历史数据，找出所有相似情况</li>
                </ul>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="📊 技术指标说明" name="indicators">
            <div class="help-section">
              <h3>系统使用的技术指标（用人话解释）</h3>

              <el-collapse v-model="activeIndicatorNames">
                <el-collapse-item title="📈 趋势类指标 - 判断大方向" name="trend">
                  <ul class="indicator-list">
                    <li><strong>移动平均线（MA）</strong>：过去N天的平均价格，像是股价的"重心"</li>
                    <li><strong>MACD</strong>：快线与慢线的差值，判断趋势是否在加速</li>
                    <li><strong>均线差值</strong>：股价偏离平均价格多远，偏离太远可能回调</li>
                  </ul>
                </el-collapse-item>

                <el-collapse-item title="💪 动量类指标 - 判断力度" name="momentum">
                  <ul class="indicator-list">
                    <li><strong>RSI（相对强弱）</strong>：像体温计，超过70度"发烧"（超买），低于30度"着凉"（超卖）</li>
                    <li><strong>CCI（商品路径）</strong>：衡量股价偏离正常范围多远</li>
                    <li><strong>威廉指标</strong>：判断股价在近期高低点中的位置</li>
                  </ul>
                </el-collapse-item>

                <el-collapse-item title="📉 波动类指标 - 判断风险" name="volatility">
                  <ul class="indicator-list">
                    <li><strong>布林带</strong>：股价的"正常活动范围"，突破上下轨可能有异动</li>
                    <li><strong>ATR（真实波幅）</strong>：股票的"活跃度"，波动越大风险越高</li>
                    <li><strong>ADX（趋势强度）</strong>：趋势的"可信度"，数值越高趋势越明确</li>
                  </ul>
                </el-collapse-item>

                <el-collapse-item title="📦 成交量指标 - 判断参与度" name="volume">
                  <ul class="indicator-list">
                    <li><strong>OBV（能量潮）</strong>：资金是流入还是流出，"聪明钱"的动向</li>
                    <li><strong>VWAP（均价）</strong>：大资金的平均成本，机构的"底牌"</li>
                    <li><strong>成交量异动</strong>：突然放量可能有重要事件发生</li>
                  </ul>
                </el-collapse-item>
              </el-collapse>
            </div>
          </el-tab-pane>

          <el-tab-pane label="🤖 AI技术" name="technical">
            <div class="help-section">
              <h3>🧠 人工智能如何提升历史K线相似度？</h3>

              <div class="ai-feature">
                <h4>1. 深度学习模型（Transformer）</h4>
                <p>
                  使用与ChatGPT相同的基础技术，但专门训练用于理解股价走势。
                  就像ChatGPT能理解语言一样，我们的模型能"理解"K线图的语言。
                </p>
              </div>

              <div class="ai-feature">
                <h4>2. 特征自动提取</h4>
                <p>
                  传统方法只看价格和成交量，AI可以同时分析29个技术指标，
                  发现人眼难以察觉的复杂关联。就像医生看X光片，AI能看到更多细节。
                </p>
              </div>

              <div class="ai-feature">
                <h4>3. 相似度智能计算</h4>
                <p>
                  不是简单比较数字大小，而是理解走势的"形态相似"和"本质相似"。
                  比如，虽然价格不同，但都是"突破后回踩确认"的形态。
                </p>
              </div>

              <div class="ai-feature">
                <h4>4. 持续学习优化</h4>
                <p>
                  每次预测都会让模型积累经验，逐渐提高对特定股票的理解。
                  使用越多，预测越准确。
                </p>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="🎲 运行示例" name="example">
            <div class="help-section">
              <h3>📊 实际运行示例</h3>
              <div class="example-box">
                <p><strong>假设今天是2024年10月3日，基准周期5天，预测周期5天：</strong></p>
                <ol>
                  <li>
                    <strong>📈 当前市场分析</strong>
                    <p>系统提取9月27日-10月3日（基准周期5天）的技术指标：</p>
                    <ul>
                      <li>RSI从45上升到62（中性转强势）</li>
                      <li>MACD金叉形成，DIF线上穿DEA线</li>
                      <li>成交量温和放大1.3倍</li>
                      <li>股价站上5日均线</li>
                      <li>布林带开始开口向上</li>
                    </ul>
                  </li>

                  <li>
                    <strong>🔍 历史相似片段搜索</strong>
                    <p>AI在2022-2024年的历史数据中找到5个最相似的5天形态：</p>
                    <table style="width: 100%; margin-top: 10px;">
                      <thead>
                        <tr style="background: var(--bg-tertiary);">
                          <th style="padding: 8px; text-align: left;">历史时段</th>
                          <th style="padding: 8px;">相似度</th>
                          <th style="padding: 8px;">后续走势</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td style="padding: 8px;">2023年3月15-21日</td>
                          <td style="padding: 8px; text-align: center; color: var(--success-color);">92%</td>
                          <td style="padding: 8px; text-align: center;">↑ 8%</td>
                        </tr>
                        <tr style="background: var(--bg-tertiary);">
                          <td style="padding: 8px;">2022年11月8-14日</td>
                          <td style="padding: 8px; text-align: center; color: var(--warning-color);">89%</td>
                          <td style="padding: 8px; text-align: center;">↓ 3%</td>
                        </tr>
                        <tr>
                          <td style="padding: 8px;">2023年7月20-26日</td>
                          <td style="padding: 8px; text-align: center; color: var(--warning-color);">87%</td>
                          <td style="padding: 8px; text-align: center;">↑ 5%</td>
                        </tr>
                        <tr style="background: var(--bg-tertiary);">
                          <td style="padding: 8px;">2024年1月10-16日</td>
                          <td style="padding: 8px; text-align: center; color: var(--info-color);">85%</td>
                          <td style="padding: 8px; text-align: center;">↑ 6%</td>
                        </tr>
                        <tr>
                          <td style="padding: 8px;">2023年5月5-11日</td>
                          <td style="padding: 8px; text-align: center; color: var(--info-color);">83%</td>
                          <td style="padding: 8px; text-align: center;">↑ 4%</td>
                        </tr>
                      </tbody>
                    </table>
                  </li>

                  <li>
                    <strong>📉 综合预测结果</strong>
                    <p>基于5个历史相似案例的后续5天走势统计分析：</p>
                    <div style="background: var(--bg-tertiary); padding: 15px; border-radius: 8px; margin-top: 10px;">
                      <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px;">
                        <div>
                          <strong>预测指标：</strong>
                          <ul style="margin-top: 8px;">
                            <li>中位数预测：<span style="color: var(--success-color); font-weight: bold;">上涨 5%</span></li>
                            <li>置信区间：3% - 6%</li>
                            <li>最大涨幅：8%</li>
                            <li>最大跌幅：3%</li>
                          </ul>
                        </div>
                        <div>
                          <strong>统计信息：</strong>
                          <ul style="margin-top: 8px;">
                            <li>上涨案例：4个（80%）</li>
                            <li>下跌案例：1个（20%）</li>
                            <li>平均涨幅：5.2%</li>
                            <li>建议：<span style="color: var(--success-color);">看涨</span></li>
                          </ul>
                        </div>
                      </div>
                    </div>
                  </li>

                  <li>
                    <strong>💡 预测解释</strong>
                    <p>为什么系统预测会上涨？</p>
                    <ul>
                      <li><strong>技术面支撑</strong>：当前技术指标组合（RSI上升+MACD金叉+放量）在历史上80%的情况下导致上涨</li>
                      <li><strong>形态相似性</strong>：找到的5个历史片段都呈现"震荡筑底后开始反弹"的形态</li>
                      <li><strong>统计优势</strong>：4个上涨案例对1个下跌案例，统计上有明显优势</li>
                      <li><strong>风险提示</strong>：仍有20%的历史案例出现下跌，需设置止损</li>
                    </ul>
                  </li>
                </ol>
              </div>

              <h3 style="margin-top: 30px;">🔄 其他应用场景</h3>
              <div class="scenario-grid" style="display: grid; grid-template-columns: 1fr 1fr; gap: 20px; margin-top: 20px;">
                <div class="scenario-card" style="background: var(--bg-tertiary); padding: 15px; border-radius: 8px;">
                  <h4 style="color: var(--primary-color); margin-bottom: 10px;">短线交易</h4>
                  <p>设置预测周期为2-3天，寻找短期反弹或回调机会</p>
                </div>
                <div class="scenario-card" style="background: var(--bg-tertiary); padding: 15px; border-radius: 8px;">
                  <h4 style="color: var(--primary-color); margin-bottom: 10px;">波段操作</h4>
                  <p>设置预测周期为5-10天，把握中期趋势变化</p>
                </div>
                <div class="scenario-card" style="background: var(--bg-tertiary); padding: 15px; border-radius: 8px;">
                  <h4 style="color: var(--primary-color); margin-bottom: 10px;">风险评估</h4>
                  <p>查看历史相似情况的最大回撤，评估潜在风险</p>
                </div>
                <div class="scenario-card" style="background: var(--bg-tertiary); padding: 15px; border-radius: 8px;">
                  <h4 style="color: var(--primary-color); margin-bottom: 10px;">择时入场</h4>
                  <p>等待高相似度（>90%）的历史模式出现再入场</p>
                </div>
              </div>
            </div>
          </el-tab-pane>

          <el-tab-pane label="⚠️ 风险提示" name="risk">
            <div class="help-section risk-section">
              <el-alert
                title="重要提示"
                type="warning"
                :closable="false"
                show-icon
              >
                本系统仅供参考，不构成投资建议。股市有风险，投资需谨慎！
              </el-alert>

              <h3 style="margin-top: 20px;">📌 请注意以下限制</h3>
              <ul class="risk-list">
                <li>
                  <strong>历史不代表未来</strong>：虽然历史会有相似性，但不会100%重复
                </li>
                <li>
                  <strong>无法预测突发事件</strong>：如政策变化、黑天鹅事件等
                </li>
                <li>
                  <strong>预测仅供参考</strong>：应结合基本面、资金面等多方面分析
                </li>
                <li>
                  <strong>适用性限制</strong>：对流动性差、操纵性强的股票预测效果较差
                </li>
              </ul>

              <h3>✅ 正确使用方式</h3>
              <ul class="usage-list">
                <li>作为辅助工具，不作为唯一决策依据</li>
                <li>结合自己的投资经验和风险承受能力</li>
                <li>设置止损，控制仓位，做好风险管理</li>
                <li>长期使用，统计验证，逐步建立信任</li>
              </ul>
            </div>
          </el-tab-pane>
        </el-tabs>
      </div>

      <template #footer>
        <div class="dialog-footer">
          <el-button @click="showHowItWorksDialog = false" type="primary">我已了解</el-button>
        </div>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, onUnmounted, nextTick, watch } from 'vue'
import { ElMessage, ElNotification, ElConfigProvider } from 'element-plus'
import zhCn from 'element-plus/es/locale/lang/zh-cn'
import {
  Expand, Fold, Loading, User, Download, QuestionFilled, InfoFilled,
  DataLine, Operation, Filter, VideoPlay, TrendCharts, Clock, DataAnalysis,
  Histogram, Search, ZoomIn, ZoomOut, Refresh, Sunny, Moon, Ticket, Setting, Opportunity, ArrowDown
} from '@element-plus/icons-vue'
import { predictAPI, getFeaturesAPI, generateChartAPI } from '@/api/stock'
import { getCacheStats, getCacheList, checkCache, clearCache } from '@/api/cache'
import MiniKline from '@/components/MiniKline.vue'
import { debounce } from '@/utils/performance'

// 主题状态
const isDarkMode = ref(false)
const sidebarCollapsed = ref(false)

// 缓存相关状态
const cacheStats = ref({
  cache_enabled: false,
  stats: null
})
const cacheList = ref([])
const cacheStatus = ref('unknown') // unknown, hit, miss, checking
const showCacheInfo = ref(false)
const showDetails = ref(true)
const showAdvancedSettings = ref(false) // 高级设置折叠状态

// 移动端相关状态
const isMobile = ref(false)
const isPortrait = ref(true)
const isMobilePortrait = computed(() => isMobile.value && isPortrait.value)
const isMobileView = computed(() => isMobile.value)

// 初始化设备信息，避免移动端首屏闪烁
if (typeof window !== 'undefined') {
  const ua = (typeof navigator !== 'undefined' ? navigator.userAgent || navigator.vendor || window.opera : '') || ''
  const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/i.test(ua.toLowerCase())
  const width = window.innerWidth
  const height = window.innerHeight
  isMobile.value = isMobileUA || width <= 768
  isPortrait.value = height >= width
}

// 数据状态
const loading = ref(false)
const plotlyHtml = ref('')
const chartData = ref(null)
const modelInfo = ref(null)
const similarWindows = ref([])
const evaluationResult = ref(null)
// const mostSimilarDay = ref(null)  // 不再需要单独的最相似交易日，直接使用similarWindows[0]

const formatPrice = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '--'
  const num = Number(value)
  if (!Number.isFinite(num)) return '--'
  return num >= 1000 ? num.toFixed(0) : num.toFixed(2)
}

const formatReturn = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '无数据'
  return `${(value * 100).toFixed(2)}%`
}

const evaluationSummary = computed(() => evaluationResult.value?.summary || null)
// 逐日评估记录：默认按日期倒序展示（新日期在上）
const evaluationRecords = computed(() => {
  const records = evaluationResult.value?.records || []
  return [...records].sort((a, b) => {
    const timeA = new Date(a?.date || 0).getTime()
    const timeB = new Date(b?.date || 0).getTime()
    const safeA = Number.isFinite(timeA) ? timeA : 0
    const safeB = Number.isFinite(timeB) ? timeB : 0
    return safeB - safeA
  })
})
const evaluationTableProps = computed(() => (isMobileView.value ? { height: 400 } : {}))
const recentDirectionStats = computed(() => {
  const records = evaluationRecords.value
  if (!records || !records.length) {
    return { accuracy: null, sampleSize: 0 }
  }

  const sorted = [...records].sort((a, b) => {
    const timeA = new Date(a?.date || 0).getTime()
    const timeB = new Date(b?.date || 0).getTime()
    const safeA = Number.isFinite(timeA) ? timeA : 0
    const safeB = Number.isFinite(timeB) ? timeB : 0
    return safeB - safeA
  })

  const recent = sorted.slice(0, 10)
  const valid = recent.filter((row) => {
    const actual = Number(row?.actual_return)
    const predicted = Number(row?.predicted_return)
    return Number.isFinite(actual) && Number.isFinite(predicted)
  })

  const sampleSize = valid.length
  if (!sampleSize) {
    return { accuracy: null, sampleSize }
  }

  const correct = valid.reduce((count, row) => {
    const actualSign = Math.sign(Number(row.actual_return))
    const predictedSign = Math.sign(Number(row.predicted_return))
    return count + (actualSign === predictedSign ? 1 : 0)
  }, 0)

  return {
    accuracy: correct / sampleSize,
    sampleSize
  }
})
const formatPercent = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return `${(value * 100).toFixed(2)}%`
}
const formatNumber = (value, digits = 4) => {
  if (value === null || value === undefined || Number.isNaN(value)) return '-'
  return Number(value).toFixed(digits)
}

// 计算明日预测收益（基于预测首日收盘与历史最后一日收盘）
const tomorrowPrediction = computed(() => {
  const data = fullPredictionData.value
  if (!data) return null
  const preds = data.predictions || []
  const hist = data.historical_data || []
  if (!preds.length || !hist.length) return null
  const pred = preds[0]
  const last = hist[hist.length - 1]
  const lastClose = Number(last?.close ?? last?.open)
  const predClose = Number(pred?.close ?? pred?.open)
  if (!Number.isFinite(lastClose) || !Number.isFinite(predClose) || lastClose === 0) {
    return { date: pred?.date || null, return: null }
  }
  return { date: pred?.date || null, return: (predClose - lastClose) / lastClose }
})

// 评估相关的辅助函数
const getEvaluationQualityType = () => {
  if (!evaluationSummary.value) return 'info'
  const accuracy = evaluationSummary.value.direction_accuracy
  if (accuracy >= 0.6) return 'success'
  if (accuracy >= 0.5) return 'warning'
  return 'danger'
}

const getEvaluationQualityLabel = () => {
  if (!evaluationSummary.value) return '无数据'
  const accuracy = evaluationSummary.value.direction_accuracy
  if (accuracy >= 0.6) return '优秀'
  if (accuracy >= 0.5) return '良好'
  return '一般'
}

const getAccuracyClass = (accuracy) => {
  if (accuracy === null || accuracy === undefined) return ''
  if (accuracy >= 0.6) return 'metric-success'
  if (accuracy >= 0.5) return 'metric-warning'
  return 'metric-danger'
}

const getReturnClass = (value) => {
  if (value === null || value === undefined) return ''
  return value >= 0 ? 'metric-success' : 'metric-danger'
}

const getErrorClass = (error) => {
  if (error === null || error === undefined) return ''
  const absError = Math.abs(error)
  if (absError <= 0.02) return 'error-low'
  if (absError <= 0.05) return 'error-medium'
  return 'error-high'
}

const isDirectionCorrect = (row) => {
  if (!row.predicted_return || !row.actual_return) return false
  return (row.predicted_return * row.actual_return) >= 0
}

const exportEvaluationData = () => {
  const records = evaluationResult.value?.records || []
  if (!records.length) {
    ElMessage.warning('暂无评估数据可导出')
    return
  }

  const data = {
    summary: evaluationSummary.value,
    records,
    export_time: new Date().toISOString(),
    params: {
      symbol: params.symbol,
      window: params.window,
      topk: params.topk
    }
  }

  const dataStr = JSON.stringify(data, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.download = `evaluation-${params.symbol}-${new Date().getTime()}.json`
  link.href = url
  link.click()
  URL.revokeObjectURL(url)
  ElMessage.success('评估数据已导出')
}

const getReturnTagType = (value) => {
  if (value === null || value === undefined || Number.isNaN(value)) return 'info'
  // 红色为上涨(danger)，绿色为下跌(success)
  return value >= 0 ? 'danger' : 'success'
}

const getWindowSummary = (window) => {
  const preview = window?.window_preview
  const closes = preview?.close || []
  if (!closes.length) {
    return '无收盘数据'
  }
  const start = formatPrice(closes[0])
  const end = formatPrice(closes[closes.length - 1])
  return `￥${start} → ￥${end}`
}

const getFutureSummary = (window) => {
  const preview = window?.future_preview
  const closes = preview?.close || []
  if (!closes.length) {
    return '无跟随数据'
  }
  const start = formatPrice(closes[0])
  const end = formatPrice(closes[closes.length - 1])
  return `￥${start} → ￥${end}`
}

const getPreviewPoints = (preview, maxPoints = 3) => {
  if (!preview || !preview.dates || !preview.close || !preview.close.length) {
    return []
  }
  const dates = preview.dates
  const closes = preview.close
  const length = closes.length
  const indices = new Set([0, Math.max(0, length - 1)])
  if (length > 3) {
    indices.add(Math.floor(length / 2))
  }
  return Array.from(indices).sort((a, b) => a - b).map((idx) => ({
    date: dates[idx],
    close: closes[idx]
  }))
}
const lastPredictionTime = ref('')
const accuracy = ref(92.3)

// 存储完整的预测数据（最多10天）
const fullPredictionData = ref(null)
const currentChartHtml = ref('')  // 当前显示的图表HTML

// 特征相关
const useCustomFeatures = ref(false)
const selectedFeatures = ref([])
const featureNameMap = ref({})
const featureGroups = ref({})
const showFeatureDialog = ref(false)
const featureSearchKeyword = ref('')
const activeFeatureTab = ref('')

// 帮助对话框相关
const showHowItWorksDialog = ref(false)
const activeHelpTab = ref('simple')
const activeIndicatorNames = ref(['trend'])

// 特征组标签映射
const featureGroupLabels = {
  'price_features': '价格特征',
  'volume_features': '成交量特征',
  'technical_indicators': '技术指标',
  'pattern_features': '形态特征',
  '趋势指标': '趋势指标',
  '动量指标': '动量指标',
  '波动率指标': '波动率指标',
  '成交量指标': '成交量指标',
  '方向性指标': '方向性指标',
  '偏离度指标': '偏离度指标',
  '计数指标': '计数指标'
}

// 计算所有特征
const allFeatures = computed(() => {
  return Object.values(featureGroups.value).flat()
})

// 将默认覆盖逻辑放到 params 初始化之后，避免未定义引用

// 过滤后的特征组
const filteredFeatureGroups = computed(() => {
  if (!featureSearchKeyword.value) {
    return featureGroups.value
  }

  const keyword = featureSearchKeyword.value.toLowerCase()
  const filtered = {}

  Object.entries(featureGroups.value).forEach(([group, features]) => {
    const filteredFeatures = features.filter(feature => {
      const name = (featureNameMap.value[feature] || feature).toLowerCase()
      const code = feature.toLowerCase()
      return name.includes(keyword) || code.includes(keyword)
    })

    if (filteredFeatures.length > 0) {
      filtered[group] = filteredFeatures
    }
  })

  return filtered
})

function formatYmd(date = new Date()) {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}${month}${day}`
}

// 参数配置
const params = reactive({
  symbol: '000001.SH',
  startDate: '20200101',
  endDate: formatYmd(),
  window: 5,              // 基准周期：用于查找历史段
  h_future: 5,            // 预测周期：预测未来天数
  epochs: 20,
  topk: 5,
  engine: 'ml',
  predictionMethod: 'median',  // 预测方式
  modelType: 'transformer',     // 模型类型
  prefilter: true,              // 是否启用相似窗口预过滤
  prefilterMultiplier: 5,       // 预过滤候选倍数
  prefilterTolerance: 0.6,      // 预过滤容忍度
  strictness: 0.75,             // 相似度阈值
  useCorr: true,                // 是否启用相关度
  useDtw: true,                 // 是否启用 DTW
  alphaCos: 0.5,                // 余弦初始权重
  betaCorr: 0.3,                // 相关度初始权重
  gammaDtw: 0.2,                // DTW 初始权重
  reRankTop: 30,                // 重排候选数量
  predictionStyle: 'normal',    // 预测风格
  useFixedSeed: true,           // 是否使用固定随机种子
  randomSeed: 42                // 随机种子
})

// 默认覆盖：基准周期30天、预测周期1天、启用逐日评估、评估起始20250101
params.window = 30
params.h_future = 5
params.evaluateDaily = true
params.evaluationStart = '20250101'

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

// 生命周期
onMounted(async () => {
  await loadFeatures()
  await loadCacheStats()
  initTheme()
  showWelcomeNotification()
  updateDeviceState()

  // 使用防抖处理 resize 和 orientationchange 事件，避免频繁触发
  const debouncedUpdateDevice = debounce(updateDeviceState, 300, {
    leading: true,
    trailing: true,
    maxWait: 1000
  })

  window.addEventListener('resize', debouncedUpdateDevice)
  window.addEventListener('orientationchange', debouncedUpdateDevice)

  // 保存防抖函数引用，用于清理
  window.__debouncedUpdateDevice = debouncedUpdateDevice
})

onUnmounted(() => {
  const debouncedUpdateDevice = window.__debouncedUpdateDevice
  if (debouncedUpdateDevice) {
    window.removeEventListener('resize', debouncedUpdateDevice)
    window.removeEventListener('orientationchange', debouncedUpdateDevice)
    debouncedUpdateDevice.cancel()
  }

  // 清理图表防抖函数
  if (debouncedUpdateChart) {
    debouncedUpdateChart.cancel()
  }
})

// 设备与方向检测 - 优化版本
const updateDeviceState = () => {
  if (typeof window === 'undefined') {
    return
  }
  const userAgentSource = (typeof navigator !== 'undefined' ? navigator.userAgent || navigator.vendor : '') || ''
  const operaInfo = typeof window.opera !== 'undefined' ? String(window.opera) : ''
  const userAgent = (userAgentSource || operaInfo).toLowerCase()
  const isMobileUA = /android|webos|iphone|ipad|ipod|blackberry|iemobile|opera mini/.test(userAgent)
  const windowWidth = window.innerWidth
  const windowHeight = window.innerHeight

  // 更新移动设备状态（768px 为移动端分界线）
  isMobile.value = isMobileUA || windowWidth <= 768
  // 更新方向状态
  isPortrait.value = windowHeight >= windowWidth
}

watch(isMobilePortrait, (value, previousValue) => {
  if (value && !previousValue) {
    sidebarCollapsed.value = true
  }
})

// 加载特征
const loadFeatures = async () => {
  try {
    const res = await getFeaturesAPI()
    featureNameMap.value = res.feature_map
    featureGroups.value = res.feature_groups

    // 使用后端返回的中文分组标签,如果没有则保留原有映射
    if (res.feature_group_labels) {
      Object.assign(featureGroupLabels, res.feature_group_labels)
    }

    // 如果默认使用全部特征，则选择所有特征
    if (!useCustomFeatures.value) {
      selectedFeatures.value = []  // 不选择时使用后端的全部特征
    }

    // 设置初始活动标签页
    const groupNames = Object.keys(featureGroups.value)
    if (groupNames.length > 0) {
      activeFeatureTab.value = groupNames[0]
    }
  } catch (error) {
    ElMessage.error('加载特征列表失败')
  }
}

// 主题切换
const toggleTheme = () => {
  isDarkMode.value = !isDarkMode.value
  document.documentElement.setAttribute('data-theme', isDarkMode.value ? 'dark' : 'light')
  localStorage.setItem('theme', isDarkMode.value ? 'dark' : 'light')
}

const initTheme = () => {
  const savedTheme = localStorage.getItem('theme')
  if (savedTheme) {
    isDarkMode.value = savedTheme === 'dark'
    document.documentElement.setAttribute('data-theme', savedTheme)
  }
}

// 侧边栏切换
const toggleSidebar = () => {
  sidebarCollapsed.value = !sidebarCollapsed.value
}

// 特征选择
const selectAllFeatures = () => {
  selectedFeatures.value = Object.values(featureGroups.value).flat()
  ElMessage.success('已选择所有特征')
}

const selectRecommended = () => {
  selectedFeatures.value = [
    'RSI_Signal', 'MACD_Diff', 'K_D_Diff', 'Bollinger_Width',
    'OBV', 'VWAP', 'ADX_14', 'volume_Change'
  ]
  ElMessage.success('已选择推荐特征')
}

const clearFeatures = () => {
  selectedFeatures.value = []
  ElMessage.info('已清空特征选择')
}

// 全选当前标签页的特征
const selectAllInCurrentTab = () => {
  const currentFeatures = featureGroups.value[activeFeatureTab.value] || []
  currentFeatures.forEach(feature => {
    if (!selectedFeatures.value.includes(feature)) {
      selectedFeatures.value.push(feature)
    }
  })
  const tabLabel = featureGroupLabels[activeFeatureTab.value] || activeFeatureTab.value
  ElMessage.success(`已全选${tabLabel}组`)
}

// 清空当前标签页的特征
const clearCurrentTab = () => {
  const currentFeatures = featureGroups.value[activeFeatureTab.value] || []
  selectedFeatures.value = selectedFeatures.value.filter(
    feature => !currentFeatures.includes(feature)
  )
  const tabLabel = featureGroupLabels[activeFeatureTab.value] || activeFeatureTab.value
  ElMessage.info(`已清空${tabLabel}组`)
}

// 确认特征选择
const confirmFeatureSelection = () => {
  showFeatureDialog.value = false
  ElMessage.success(`已选择 ${selectedFeatures.value.length} 个特征`)
}

// 缓存相关方法
const loadCacheStats = async () => {
  try {
    const result = await getCacheStats()
    cacheStats.value = result
  } catch (error) {
    console.error('Failed to load cache stats:', error)
  }
}

const loadCacheList = async () => {
  try {
    const res = await getCacheList()
    cacheList.value = res.entries || []
  } catch (error) {
    console.error("Failed to load cache list:", error)
  }
}


const checkCacheStatus = async () => {
  try {
    cacheStatus.value = 'checking'

    const requestData = {
      symbol: params.symbol,
      start_date: params.startDate,
      end_date: params.endDate,
      window: params.window,
      epochs: params.epochs,
      topk: params.topk,
      selected_features: useCustomFeatures.value ? selectedFeatures.value : [],
      model_type: params.modelType,
      use_window_zscore: true,
      engine: params.engine
    }

    const result = await checkCache(requestData)
    cacheStatus.value = result.cache_exists ? 'hit' : 'miss'

    // 显示缓存提示
    if (result.cache_exists) {
      ElMessage.success('发现缓存，将直接加载模型，预计3-5秒完成')
    } else {
      ElMessage.info('未发现缓存，将训练新模型，预计需要20-30秒')
    }

    return result.cache_exists
  } catch (error) {
    console.error('Failed to check cache:', error)
    cacheStatus.value = 'unknown'
    return false
  }
}

const handleClearCache = async () => {
  try {
    await clearCache()
    ElMessage.success('缓存已清空')
    await loadCacheStats()
      await loadCacheList()  // 刷新缓存列表
    await loadCacheList()
    cacheStatus.value = 'unknown'
  } catch (error) {
    ElMessage.error('清空缓存失败')
    console.error('Failed to clear cache:', error)
  }
}

// 运行预测
const runPrediction = async () => {
  loading.value = true
  if (!params.evaluateDaily) {
    evaluationResult.value = null
  }

  try {
    // 避免 endDate 长期写死导致“预测首日=今天”
    const todayYmd = formatYmd()
    if (!/^\d{8}$/.test(String(params.endDate || '')) || String(params.endDate) < todayYmd) {
      params.endDate = todayYmd
    }

    // 先检查缓存状态
    await checkCacheStatus()
    // 根据预测方式设置聚合方法
    let aggMethod = params.predictionMethod
    if (aggMethod === 'weighted') {
      aggMethod = 'mean'  // 加权预测暂时使用均值，后续可以实现加权逻辑
    } else if (aggMethod === 'best') {
      aggMethod = 'max'  // 最优路径使用最大值
    } else if (aggMethod === 'conservative') {
      aggMethod = 'min'  // 保守预测使用最小值
    }

    // 获取预测方式名称
    const methodName = {
      'median': '中位数预测',
      'mean': '均值预测',
      'weighted': '加权预测',
      'best': '最优路径',
      'conservative': '保守预测'
    }[params.predictionMethod]

    // 始终请求最大10天的预测数据
    const normalizedWeightsPredict = normalizedWeightPreview.value
    const requestData = {
      symbol: params.symbol,
      start_date: params.startDate,
      end_date: params.endDate,
      window: params.window,
      epochs: params.epochs,
      topk: params.topk,
      engine: params.engine,
      evaluate_daily: params.evaluateDaily,
      evaluation_start_date: params.evaluationStart,
      use_window_zscore: true,
      selected_features: useCustomFeatures.value ? selectedFeatures.value : null,
      h_future: params.h_future,  // 始终请求10天数据
      min_gap_days: Math.max(params.window * 2, 5),
      lookback: 100,
      show_paths: true,
      agg: aggMethod,
      model_type: params.modelType,
      use_fixed_seed: params.useFixedSeed,
      random_seed: params.randomSeed,
      prefilter: params.prefilter,
      prefilter_multiplier: params.prefilterMultiplier,
      prefilter_tolerance: params.prefilterTolerance,
      use_corr: params.useCorr,
      use_dtw: params.useDtw,
      alpha_cos: normalizedWeightsPredict.alpha,
      beta_corr: normalizedWeightsPredict.beta,
      gamma_dtw: normalizedWeightsPredict.gamma,
      strictness: params.strictness,
      re_rank_top: params.reRankTop
    }

    // Ensure h_future follows UI before chartRequestData snapshot
    requestData.h_future = params.h_future
    const chartRequestData = { ...requestData, evaluate_daily: false }

    // 优先让后端在 /predict 里直接返回图表，避免并发触发两次 pipeline 导致超时
    const predResponse = await predictAPI({ ...requestData, include_chart: true })

    if (predResponse.status === 'success') {
      similarWindows.value = predResponse.similar_windows || []
      fullPredictionData.value = predResponse.data  // 存储完整的10天数据
      chartData.value = predResponse.data
      lastPredictionTime.value = new Date().toLocaleTimeString()
      // 处理评估结果
      evaluationResult.value = predResponse.evaluation || null
      modelInfo.value = predResponse.model_info || modelInfo.value
      await loadCacheStats()  // 预测后刷新缓存统计
      // 处理最相似交易日
      // mostSimilarDay.value = predResponse.most_similar_day || null  // 不再需要
    }

    // 图表优先使用 /predict 返回的 html；如缺失则降级调用 /generate_chart
    let chartHtml = predResponse.html
    if (!chartHtml) {
      try {
        const chartResponse = await generateChartAPI(chartRequestData)
        if (chartResponse.status === 'success') {
          chartHtml = chartResponse.html
        }
      } catch (chartError) {
        console.error('Chart generation error:', chartError)
        ElMessage.warning('图表生成失败：' + (chartError?.message || 'unknown error'))
      }
    }

    if (chartHtml) {
      plotlyHtml.value = chartHtml
      currentChartHtml.value = chartHtml
    }

    if (predResponse.status === 'success') {
      ElNotification({
        title: '预测成功',
        message: `使用${methodName || '默认'}方式，找到 ${similarWindows.value.length} 个相似历史窗口`,
        type: 'success',
        duration: 3000
      })
    }
  } catch (error) {
    evaluationResult.value = null
    ElMessage.error('预测失败: ' + error.message)
  } finally {
    loading.value = false
  }
}

const handleQuickPredict = () => {
  if (loading.value) {
    ElMessage.info('预测进行中，请稍候')
    return
  }
  runPrediction()
}

// 动态更新图表显示（简化版本）
const updateChartForDays = async () => {
  if (!fullPredictionData.value || !similarWindows.value.length) {
    return
  }

  loading.value = true
  try {
    // 根据预测方式设置聚合方法
    let aggMethod = params.predictionMethod
    if (aggMethod === 'weighted') {
      aggMethod = 'mean'
    } else if (aggMethod === 'best') {
      aggMethod = 'max'
    } else if (aggMethod === 'conservative') {
      aggMethod = 'min'
    }

    // 请求新的图表，但只使用指定的天数
    const normalizedWeightsChart = normalizedWeightPreview.value
    const requestData = {
      symbol: params.symbol,
      start_date: params.startDate,
      end_date: params.endDate,
      window: params.window,
      epochs: params.epochs,
      topk: params.topk,
      engine: params.engine,
      use_window_zscore: true,
      selected_features: useCustomFeatures.value ? selectedFeatures.value : null,
      h_future: params.h_future,  // 使用当前选择的预测天数
      min_gap_days: Math.max(params.window * 2, 5),
      lookback: 100,
      show_paths: true,
      agg: aggMethod,
      model_type: params.modelType,
      use_fixed_seed: params.useFixedSeed,
      random_seed: params.randomSeed,
      prefilter: params.prefilter,
      prefilter_multiplier: params.prefilterMultiplier,
      prefilter_tolerance: params.prefilterTolerance,
      use_corr: params.useCorr,
      use_dtw: params.useDtw,
      alpha_cos: normalizedWeightsChart.alpha,
      beta_corr: normalizedWeightsChart.beta,
      gamma_dtw: normalizedWeightsChart.gamma,
      strictness: params.strictness,
      re_rank_top: params.reRankTop
    }

    // 只请求新的图表HTML，不重新计算预测
    const chartResponse = await generateChartAPI(requestData)
    if (chartResponse.status === 'success') {
      plotlyHtml.value = chartResponse.html
      currentChartHtml.value = chartResponse.html
    }
  } catch (error) {
    console.error('更新图表失败:', error)
  } finally {
    loading.value = false
  }
}

// 监听预测周期变化（使用防抖工具函数）
const debouncedUpdateChart = debounce(() => {
  if (fullPredictionData.value) {
    updateChartForDays()
  }
}, 300, { leading: false, trailing: true })

watch(() => params.h_future, (newValue, oldValue) => {
  if (fullPredictionData.value && oldValue !== undefined) {
    debouncedUpdateChart()
  }
})

// iframe加载完成处理（简化）
const onIframeLoad = () => {
  // 不需要复杂的通信，已经通过重新生成HTML实现
}

// 图表操作
const zoomIn = () => {
  ElMessage.info('请在图表上使用鼠标滚轮放大')
}

const zoomOut = () => {
  ElMessage.info('请在图表上使用鼠标滚轮缩小')
}

const resetZoom = () => {
  ElMessage.info('双击图表重置视图')
}

// 导出功能
const exportChart = (format) => {
  ElMessage.success(`导出${format.toUpperCase()}功能开发中`)
}

const exportData = () => {
  if (!chartData.value) {
    ElMessage.warning('暂无数据可导出')
    return
  }

  const dataStr = JSON.stringify(chartData.value, null, 2)
  const blob = new Blob([dataStr], { type: 'application/json' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.download = 'prediction-data.json'
  link.href = url
  link.click()
  ElMessage.success('数据已导出')
}

// 其他功能
const showHelp = () => {
  ElNotification({
    title: '使用提示',
    message: "1. 输入股票代码\n2. 选择日期范围\n3. 调整参数\n4. 点击开始预测",
    duration: 5000,
    type: 'info'
  })
}

const showHowItWorks = () => {
  showHowItWorksDialog.value = true
}

const showAbout = () => {
  ElNotification({
    title: '关于系统',
    message: '智能K线预测系统 v2.0.0\n基于 Transformer 的行情预测',
    duration: 5000
  })
}

const scrollToParams = () => {
  sidebarCollapsed.value = false
}

const showWelcomeNotification = () => {
  ElNotification({
    title: '欢迎使用智能K线预测系统',
    message: '系统已加载默认演示参数，调整配置后点击“开始预测”即可查看结果',
    type: 'info',
    duration: 4000
  })
}

// 进度条颜色（保留用于其他地方）
const getProgressColor = (value) => {
  if (value >= 0.9) return '#10b981'
  if (value >= 0.7) return '#3b82f6'
  if (value >= 0.5) return '#f59e0b'
  return '#dc2626'
}

// 相似度样式类
const getSimilarityClass = (value) => {
  if (value >= 0.9) return 'high'
  if (value >= 0.7) return 'medium'
  if (value >= 0.5) return 'low'
  return 'very-low'
}
</script>

<style scoped lang="scss">
@import '@/styles/global.scss';

.app-container {
  min-height: 100vh;
  background: var(--bg-primary);
  transition: var(--transition-base);

  &.dark-mode {
    color-scheme: dark;
  }
}

// 导航栏样式 - 金融专业风格
.navbar {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  height: 60px;
  z-index: 1000;
  background: var(--bg-secondary);
  border-bottom: 1px solid var(--border-color);
  box-shadow: var(--shadow-sm);
  transition: var(--transition-base);

  .navbar-content {
    height: 100%;
    padding: 0 24px;
    display: flex;
    align-items: center;
    justify-content: space-between;
  }

  .navbar-left {
    display: flex;
    align-items: center;
    gap: 20px;

    .menu-toggle {
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      cursor: pointer;
      padding: 8px;
      border-radius: var(--radius-md);
      transition: var(--transition-fast);
      color: var(--text-primary);

      &:hover {
        background: var(--bg-hover);
        border-color: var(--primary-color);
      }
    }

    .brand {
      display: flex;
      align-items: center;
      gap: 12px;

      .brand-icon {
        width: 36px;
        height: 36px;
        display: flex;
        align-items: center;
        justify-content: center;
        background: var(--gradient-primary);
        border-radius: var(--radius-md);
        color: white;
      }

      .brand-title {
        font-size: 18px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }
  }

  .navbar-right {
    display: flex;
    align-items: center;
    gap: 12px;

    .status-indicator {
      display: flex;
      align-items: center;
      gap: 8px;
      padding: 6px 14px;
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-full);
      font-size: 13px;
      color: var(--text-secondary);

      .loading-icon {
        animation: spin 1s linear infinite;
        color: var(--primary-color);
      }
    }

    .theme-toggle {
      background: var(--bg-tertiary);
      border: 1px solid var(--border-color);
      width: 36px;
      height: 36px;
      border-radius: var(--radius-md);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: var(--transition-fast);
      color: var(--text-secondary);

      &:hover {
        background: var(--bg-hover);
        color: var(--primary-color);
        border-color: var(--primary-color);
      }
    }

    .user-avatar {
      width: 36px;
      height: 36px;
      background: var(--gradient-primary);
      border-radius: var(--radius-full);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      cursor: pointer;
      transition: var(--transition-fast);

      &:hover {
        transform: scale(1.05);
        box-shadow: var(--shadow-md);
      }
    }
  }
}

// 主布局
.main-layout {
  display: flex;
  padding-top: 60px;
  min-height: 100vh;
}

// 侧边栏 - 金融专业风格
.sidebar {
  width: 280px;
  background: var(--bg-secondary);
  border-right: 1px solid var(--border-color);
  transition: var(--transition-base);
  overflow-y: auto;
  position: fixed;
  left: 0;
  top: 60px;
  bottom: 0;
  z-index: 100;

  &.collapsed {
    width: 64px;

    .sidebar-content {
      padding: 16px 8px;
    }

    .section-title {
      justify-content: center;
    }
  }

  .sidebar-content {
    padding: 20px;
  }

  .sidebar-section {
    margin-bottom: 28px;
    padding: 0 4px;

    &:last-child {
      margin-bottom: 0;
    }

    .section-title {
      display: flex;
      align-items: center;
      gap: 10px;
      margin-bottom: 16px;
      padding: 8px 0;
      font-size: 13px;
      font-weight: 600;
      color: var(--text-secondary);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      border-bottom: 1px solid var(--border-light);

      .el-icon {
        font-size: 16px;
      }

      &.collapsible {
        cursor: pointer;
        user-select: none;
        padding: 10px 12px;
        margin: 0 -12px 16px -12px;
        border-radius: var(--radius-md);
        border-bottom: none;
        transition: var(--transition-fast);
        justify-content: space-between;
        background: var(--bg-tertiary);
        border: 1px solid var(--border-light);

        &:hover {
          background: var(--bg-hover);
          border-color: var(--primary-color);
        }

        .collapse-icon {
          transition: transform 0.3s ease;

          &.collapsed {
            transform: rotate(-90deg);
          }
        }
      }
    }

    .form-group {
      margin-bottom: 20px;

      label {
        display: flex;
        align-items: center;
        margin-bottom: 10px;
        font-size: 13px;
        font-weight: 500;
        color: var(--text-secondary);
        height: 20px;
      }

      // 统一输入框高度
      .el-input {
        .el-input__inner {
          height: 32px;
        }
      }

      // 统一选择器高度
      .el-select {
        width: 100%;

        .el-input__inner {
          height: 32px;
        }
      }

      // 统一滑块样式
      .el-slider {
        padding: 0 12px;

        .el-slider__runway {
          margin: 16px 0;
          height: 6px;
        }

        .el-slider__bar {
          height: 6px;
        }

        .el-slider__button-wrapper {
          height: 36px;
          width: 36px;
          top: -15px;
        }

        .el-slider__button {
          height: 16px;
          width: 16px;
          border: 2px solid var(--primary-color);
        }

        .el-slider__marks {
          .el-slider__marks-text {
            font-size: 11px;
            color: var(--text-muted);
            margin-top: 12px;
            white-space: nowrap;
          }
        }
      }

      // 统一单选按钮组
      .el-radio-group {
        display: flex;
        width: 100%;

        .el-radio-button {
          flex: 1;

          .el-radio-button__inner {
            width: 100%;
            text-align: center;
            padding: 0 8px;
            height: 32px;
            line-height: 30px;
          }
        }
      }

      // 统一开关样式
      .el-switch {
        height: 20px;

        .el-switch__label {
          font-size: 12px;
          color: var(--text-secondary);

          &.is-active {
            color: var(--primary-color);
          }
        }
      }

      // 特殊处理带提示的标签
      .el-tooltip {
        margin-left: 4px;

        .el-icon {
          font-size: 14px;
          color: var(--text-muted);
          cursor: help;
          vertical-align: middle;
        }
      }

      // 标签样式
      .el-tag {
        height: 22px;
        line-height: 20px;
        padding: 0 8px;
        font-size: 11px;
      }

      .weight-block {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;

        &__label {
          flex: 0 0 70px;
          font-size: 12px;
          color: var(--text-secondary);
        }

        .el-slider {
          flex: 1;
        }
      }

      .weight-meta {
        margin-top: 4px;
        font-size: 12px;
        color: var(--text-muted);
        line-height: 1.6;

        &__line {
          margin: 4px 0;
        }
      }

      .weight-alert {
        margin-bottom: 6px;
      }
    }

    .feature-controls {
      .feature-quick-select {
        display: flex;
        gap: 8px;
        margin-bottom: 12px;

        .el-button {
          flex: 1;
          height: 32px;
          font-size: 13px;
        }
      }

      .el-button {
        width: 100%;
      }

      .el-tag {
        width: 100%;
        text-align: center;
        font-size: 12px;
      }
    }

    // 特殊样式：特征选择区域
    .feature-quick-select {
      display: flex;
      gap: 8px;
      margin-bottom: 12px;

      .el-button {
        flex: 1;
        height: 32px;
      }
    }
  }

  .sidebar-footer {
    position: sticky;
    bottom: 0;
    padding: 16px 20px;
    background: var(--bg-secondary);
    border-top: 1px solid var(--border-color);
    display: flex;
    flex-direction: column;
    align-items: center;
    gap: 10px;

    .help-button {
      width: 100%;
      height: 40px;
      font-size: 14px;
      font-weight: 500;
      background: var(--bg-tertiary);
      color: var(--primary-color);
      border: 1px solid var(--primary-color);
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: var(--transition-base);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 4px;

      &:hover {
        background: var(--primary-color);
        color: white;
      }
    }

    .run-button {
      width: 100%;
      height: 44px;
      font-size: 15px;
      font-weight: 600;
      background: var(--gradient-primary);
      border: none;
      color: white;
      border-radius: var(--radius-md);
      cursor: pointer;
      transition: var(--transition-base);
      display: flex;
      align-items: center;
      justify-content: center;
      gap: 6px;
      position: relative;
      overflow: hidden;

      // 按钮涟漪效果
      &::before {
        content: '';
        position: absolute;
        top: 50%;
        left: 50%;
        width: 0;
        height: 0;
        border-radius: 50%;
        background: rgba(255, 255, 255, 0.3);
        transform: translate(-50%, -50%);
        transition: width 0.6s, height 0.6s;
      }

      &:hover {
        box-shadow: 0 8px 20px rgba(30, 58, 138, 0.3);
        transform: translateY(-2px);
      }

      &:active {
        transform: translateY(0);

        &::before {
          width: 300px;
          height: 300px;
        }
      }
    }
  }
}

// 主内容区
.main-content {
  margin-left: 280px;
  padding: 32px;
  width: calc(100% - 280px);
  transition: var(--transition-base);

  .sidebar.collapsed ~ & {
    margin-left: 64px;
    width: calc(100% - 64px);
  }
}

.mobile-quick-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  margin-bottom: 20px;
  padding: 20px;
  border: 1px solid var(--border-color);
  border-radius: var(--radius-lg);
  background: var(--bg-secondary);
  box-shadow: var(--shadow-sm);

  .quick-header {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .quick-label {
      font-size: 12px;
      color: var(--text-muted);
      letter-spacing: 0.08em;
      text-transform: uppercase;
    }

    .quick-title {
      font-size: 18px;
      color: var(--text-primary);
    }
  }

  .quick-meta {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;

    .meta-item {
      flex: 1;
      min-width: 120px;
      padding: 12px;
      border-radius: var(--radius-md);
      background: var(--bg-tertiary);

      .label {
        display: block;
        font-size: 12px;
        color: var(--text-muted);
        margin-bottom: 4px;
      }

      .value {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }
  }

  .quick-action {
    width: 100%;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    height: 48px;
    font-size: 16px;
  }

  .quick-hint {
    font-size: 12px;
    color: var(--text-muted);
    text-align: center;
    margin: 0;
  }
}

@media (max-width: 480px) {
  .mobile-quick-panel {
    .quick-meta {
      flex-direction: column;
    }
  }
}

// 统计卡片网格
.stats-grid {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 20px;
  margin-bottom: 24px;
  max-width: 100%;

  @media (max-width: 1400px) {
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
  }

  @media (max-width: 1024px) {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  @media (max-width: 768px) {
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  @media (max-width: 640px) {
    grid-template-columns: 1fr;
    gap: 12px;
  }

  .stat-card {
    padding: 16px;
    display: flex;
    flex-direction: column;
    align-items: flex-start;
    gap: 12px;
    min-height: auto;
    position: relative;
    overflow: hidden;
    transition: var(--transition-base);

    // 卡片顶部色带装饰
    &::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      height: 3px;
      background: var(--primary-color);
      border-radius: var(--radius-lg) var(--radius-lg) 0 0;
    }

    // 卡片悬停效果
    &:hover {
      transform: translateY(-2px);
      box-shadow: var(--shadow-md);
    }

    // 卡片光泽效果
    &::after {
      content: '';
      position: absolute;
      top: 0;
      left: -100%;
      width: 100%;
      height: 100%;
      background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.1), transparent);
      transition: left 0.5s ease;
    }

    &:hover::after {
      left: 100%;
    }

    // 不同卡片的色带颜色
    &:nth-child(2)::before {
      background: linear-gradient(90deg, #dc2626, #f87171);
    }

    &:nth-child(3)::before {
      background: linear-gradient(90deg, #10b981, #34d399);
    }

    .stat-icon {
      width: 40px;
      height: 40px;
      border-radius: var(--radius-md);
      display: flex;
      align-items: center;
      justify-content: center;
      color: white;
      background: var(--gradient-primary);
      font-size: 20px;
      box-shadow: 0 2px 8px rgba(30, 58, 138, 0.2);
      transition: var(--transition-fast);
    }

    .stat-content {
      flex: 1;
      width: 100%;
      min-width: 0;

      h4 {
        font-size: 11px;
        color: var(--text-secondary);
        margin-bottom: 4px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }

      .stat-value {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
        margin: 0 0 6px 0;
        line-height: 1.3;
        word-break: break-word;
      }

      .stat-change {
        font-size: 12px;
        font-weight: 500;

        &.positive {
          color: var(--success-color);
        }

        &.negative {
          color: var(--secondary-color);
        }
      }

      .stat-label {
        font-size: 11px;
        color: var(--text-muted);
        margin-top: 2px;
      }

      // 最相似交易日的详细信息样式
      .similar-day-details {
        display: flex;
        align-items: center;
        gap: 4px;
        margin-top: 6px;
        flex-wrap: wrap;
      }
    }
  }
}

// 结果区域
.result-section {
  margin-bottom: 32px;

  .section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 24px;

    h2 {
      display: flex;
      align-items: center;
      gap: 12px;
      font-size: 24px;
      font-weight: 600;
    }
  }

  .similar-windows-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
    gap: 16px;

    .window-card {
      padding: 16px;
      animation: slideInLeft 0.3s ease-out forwards;

      .window-header {
        display: flex;
        align-items: center;
        justify-content: space-between;
        margin-bottom: 14px;

        .window-rank {
          font-size: 20px;
          font-weight: 600;
          color: var(--primary-color);
        }

        .similarity-badge {
          padding: 4px 12px;
          border-radius: var(--radius-full);
          font-size: 13px;
          font-weight: 600;

          &.high {
            background: #dcfce7;
            color: #15803d;

            [data-theme="dark"] & {
              background: rgba(16, 185, 129, 0.2);
              color: #34d399;
            }
          }

          &.medium {
            background: #dbeafe;
            color: #1e40af;

            [data-theme="dark"] & {
              background: rgba(59, 130, 246, 0.2);
              color: #60a5fa;
            }
          }

          &.low {
            background: #fef3c7;
            color: #d97706;

            [data-theme="dark"] & {
              background: rgba(245, 158, 11, 0.2);
              color: #fbbf24;
            }
          }

          &.very-low {
            background: #fee2e2;
            color: #dc2626;

            [data-theme="dark"] & {
              background: rgba(220, 38, 38, 0.2);
              color: #f87171;
            }
          }
        }
      }

      .window-dates {
        display: flex;
        justify-content: space-between;
        margin-bottom: 12px;
        padding: 10px;
        background: var(--bg-tertiary);
        border-radius: var(--radius-md);

        .date-item {
          .date-label {
            display: block;
            font-size: 11px;
            color: var(--text-muted);
            margin-bottom: 4px;
            text-transform: uppercase;
            letter-spacing: 0.05em;
          }

          .date-value {
            font-size: 13px;
            font-weight: 600;
            color: var(--text-primary);
          }
        }
      }

      .similarity-bar {
        height: 4px;
        background: var(--bg-tertiary);
        border-radius: var(--radius-full);
        overflow: hidden;

        .bar-fill {
          height: 100%;
          background: var(--gradient-primary);
          transition: width 0.3s ease-out;
        }
      }
    }
  }

  // 新增：横向滚动样式
  .similar-windows-scroll {
    overflow-x: auto;
    overflow-y: hidden;
    padding-bottom: 10px;

    &::-webkit-scrollbar {
      height: 6px;
    }

    &::-webkit-scrollbar-track {
      background: var(--bg-tertiary);
      border-radius: var(--radius-full);
    }

    &::-webkit-scrollbar-thumb {
      background: var(--text-muted);
      border-radius: var(--radius-full);

      &:hover {
        background: var(--text-secondary);
      }
    }
  }

  .similar-windows-row {
    display: flex;
    gap: 12px;
    padding: 4px 0;

    .window-card-compact {
      flex: 0 0 auto;
      width: 230px;
      padding: 12px;
      position: relative;
      animation: slideInLeft 0.3s ease-out forwards;

      .window-rank {
        font-size: 14px;
        font-weight: 600;
        color: var(--primary-color);
        margin-bottom: 8px;
      }

      .similarity-badge {
        position: absolute;
        top: 12px;
        right: 12px;
        padding: 2px 8px;
        border-radius: var(--radius-full);
        font-size: 12px;
        font-weight: 600;

        &.high {
          background: #dcfce7;
          color: #15803d;

          [data-theme="dark"] & {
            background: rgba(16, 185, 129, 0.2);
            color: #34d399;
          }
        }

        &.medium {
          background: #dbeafe;
          color: #1e40af;

          [data-theme="dark"] & {
            background: rgba(59, 130, 246, 0.2);
            color: #60a5fa;
          }
        }

        &.low {
          background: #fef3c7;
          color: #d97706;

          [data-theme="dark"] & {
            background: rgba(245, 158, 11, 0.2);
            color: #fbbf24;
          }
        }
      }

      .window-dates-compact {
        margin: 24px 0 8px 0;

        .date-range {
          font-size: 11px;
          color: var(--text-secondary);
          text-align: center;
        }
      }

      .window-kline {
        margin: 8px 0;
        padding: 8px;
        background: var(--bg-secondary);
        border-radius: var(--radius-sm);
      }

      .window-metrics {
        display: flex;
        gap: 6px;
        flex-wrap: wrap;
        margin-bottom: 8px;

        .el-tag {
          font-size: 11px;
        }
      }

      .window-snippet {
        font-size: 11px;
        color: var(--text-secondary);
        margin-bottom: 8px;

        .snippet-row {
          display: flex;
          justify-content: space-between;
          gap: 6px;
          margin-bottom: 2px;

          .snippet-label {
            color: var(--text-muted);
          }

          .snippet-value {
            color: var(--text-primary);
            font-weight: 500;
          }
        }
      }

      .preview-values {
        display: flex;
        flex-wrap: wrap;
        gap: 4px;
        margin-bottom: 8px;

        &.future {
          opacity: 0.9;
        }

        .preview-pill {
          background: var(--bg-tertiary);
          border-radius: var(--radius-full);
          padding: 2px 6px;
          font-size: 10px;
          color: var(--text-secondary);
          line-height: 1.4;
        }
      }

      .similarity-bar {
        height: 3px;
        background: var(--bg-tertiary);
        border-radius: var(--radius-full);
        overflow: hidden;

        .bar-fill {
          height: 100%;
          background: var(--gradient-primary);
          transition: width 0.3s ease-out;
        }
      }

      // 突出显示最相似的窗口卡片（排名第一）
      &.primary-match {
        border: 2px solid var(--primary-color);
        box-shadow: 0 0 12px rgba(59, 130, 246, 0.3),
                    0 4px 12px rgba(0, 0, 0, 0.1);
        background: linear-gradient(135deg,
          rgba(59, 130, 246, 0.08) 0%,
          var(--card-bg) 100%);
        transform: scale(1.02);

        .window-rank {
          color: var(--primary-color);
          font-size: 16px;

          &::after {
            content: ' 最相似';
            font-size: 12px;
            color: var(--primary-color);
            font-weight: 500;
          }
        }

        [data-theme="dark"] & {
          box-shadow: 0 0 16px rgba(59, 130, 246, 0.4),
                      0 4px 12px rgba(0, 0, 0, 0.3);
          background: linear-gradient(135deg,
            rgba(59, 130, 246, 0.15) 0%,
            var(--card-bg) 100%);
        }
      }
    }
  }
}

// 图表区域 - 专业简洁
.chart-section {
  padding: 20px;

  .chart-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 20px;
    position: relative;

    // 标题下划线装饰
    &::after {
      content: '';
      position: absolute;
      bottom: -10px;
      left: 0;
      width: 60px;
      height: 3px;
      background: linear-gradient(90deg, var(--primary-color), transparent);
      border-radius: var(--radius-full);
    }

    .chart-title {
      display: flex;
      align-items: center;
      gap: 10px;

      h2 {
        font-size: 18px;
        font-weight: 600;
        margin: 0;
        color: var(--text-primary);
        text-transform: uppercase;
        letter-spacing: 0.05em;
      }
    }

    .chart-actions {
      display: flex;
      gap: 10px;
    }
  }

  .chart-container {
    position: relative;
    min-height: 600px;
    border: 1px solid var(--border-color);
    border-radius: var(--radius-md);
    overflow: hidden;
    background: var(--bg-secondary);
    box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.5);
    transition: var(--transition-base);

    &:hover {
      box-shadow: inset 0 1px 0 0 rgba(255, 255, 255, 0.5), var(--shadow-sm);
    }

    // 预测周期控制面板
    .prediction-control-panel {
      position: absolute;
      top: 20px;
      left: 50%;
      transform: translateX(-50%);
      z-index: 10;
      background: rgba(255, 255, 255, 0.95);
      border: 1px solid var(--border-color);
      border-radius: var(--radius-lg);
      padding: 20px 32px;
      box-shadow: var(--shadow-md);
      backdrop-filter: blur(10px);
      min-width: 420px;
      transition: var(--transition-base);

      [data-theme="dark"] & {
        background: rgba(30, 30, 30, 0.95);
      }

      &:hover {
        box-shadow: var(--shadow-lg);
        transform: translateX(-50%) translateY(-2px);
      }

      .control-panel-content {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 16px;

        .control-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 16px;
          font-weight: 600;
          color: var(--text-primary);

          .el-icon {
            font-size: 20px;
            color: var(--primary-color);
          }
        }

        .control-value {
          font-size: 24px;
          color: var(--primary-color);

          strong {
            font-size: 32px;
            font-weight: 700;
            margin: 0 8px;
          }
        }

        .control-slider {
          width: 100%;
          padding: 0 8px;

          .el-slider {
            .el-slider__runway {
              height: 8px;
              background: var(--bg-tertiary);
              border-radius: var(--radius-full);
            }

            .el-slider__bar {
              height: 8px;
              background: var(--gradient-primary);
              border-radius: var(--radius-full);
            }

            .el-slider__button-wrapper {
              top: -16px;
            }

            .el-slider__button {
              width: 20px;
              height: 20px;
              border: 3px solid var(--primary-color);
              background: white;
              box-shadow: 0 2px 8px rgba(30, 58, 138, 0.25);
              transition: var(--transition-fast);

              &:hover {
                transform: scale(1.1);
                box-shadow: 0 4px 12px rgba(30, 58, 138, 0.35);
              }
            }

            .el-slider__marks-text {
              font-size: 12px;
              color: var(--text-muted);
              margin-top: 14px;
            }
          }
        }

        .el-tag {
          font-size: 12px;
        }
      }
    }

    iframe {
      width: 100%;
      height: 100%;
      border: none;
      display: block;
    }

    .chart-loading {
      position: absolute;
      top: 0;
      left: 0;
      right: 0;
      bottom: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      background: rgba(255, 255, 255, 0.5);
      backdrop-filter: blur(4px);
      z-index: 10;
      border-radius: var(--radius-md);

      .loading-container {
        text-align: center;
      }

      .loading-spinner-container {
        position: relative;
        width: 80px;
        height: 80px;
        margin: 0 auto 24px;
      }

      .loading-spinner {
        position: absolute;
        width: 80px;
        height: 80px;
        border: 4px solid var(--border-light);
        border-top: 4px solid var(--primary-color);
        border-radius: 50%;
        animation: spin 1s linear infinite;
      }

      .loading-pulse {
        position: absolute;
        width: 80px;
        height: 80px;
        border: 2px solid var(--primary-color);
        border-radius: 50%;
        opacity: 0;
        animation: pulse 2s ease-out infinite;
      }

      .loading-content {
        .loading-title {
          font-size: 18px;
          font-weight: 600;
          color: var(--text-primary);
          margin-bottom: 6px;
        }

        .loading-subtitle {
          font-size: 13px;
          color: var(--text-secondary);
          margin-bottom: 20px;
        }
      }

      .progress-bar-container {
        width: 200px;
        height: 4px;
        background: var(--border-light);
        border-radius: var(--radius-full);
        margin: 0 auto 16px;
        overflow: hidden;

        .progress-bar {
          height: 100%;
          background: linear-gradient(90deg, #3b82f6, #0ea5e9);
          border-radius: var(--radius-full);
          width: 30%;
          animation: progress-animation 2s ease-in-out infinite;
        }
      }

      .processing-steps {
        display: flex;
        gap: 16px;
        justify-content: center;
        margin-top: 16px;

        .step {
          display: flex;
          flex-direction: column;
          align-items: center;
          gap: 6px;

          .step-icon {
            width: 32px;
            height: 32px;
            border-radius: 50%;
            background: var(--bg-tertiary);
            border: 2px solid var(--border-light);
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 12px;
            font-weight: 600;
            color: var(--text-secondary);
            transition: all 0.3s ease;
          }

          .step-text {
            font-size: 11px;
            color: var(--text-secondary);
          }

          &.active {
            .step-icon {
              background: var(--primary-color);
              border-color: var(--primary-color);
              color: white;
              box-shadow: 0 0 12px rgba(59, 130, 246, 0.3);
              animation: pulse-scale 1.5s ease-in-out infinite;
            }
          }
        }
      }
    }

    .empty-chart {
      height: 500px;
      display: flex;
      align-items: center;
      justify-content: center;
    }
  }
}

// 浮动按钮 - 简洁专业
.fab-container {
  position: fixed;
  bottom: 32px;
  right: 32px;
  z-index: 100;

  .fab {
    width: 56px;
    height: 56px;
    border-radius: 50%;
    border: none;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    box-shadow: var(--shadow-lg);
    transition: var(--transition-base);
    color: white;
    background: var(--gradient-primary);
    position: relative;
    overflow: hidden;

    // FAB脉冲效果
    &::before {
      content: '';
      position: absolute;
      top: 50%;
      left: 50%;
      width: 100%;
      height: 100%;
      border-radius: 50%;
      background: rgba(255, 255, 255, 0.1);
      transform: translate(-50%, -50%) scale(1);
      opacity: 0;
      animation: fab-pulse 2s ease-out infinite;
    }

    &:hover {
      transform: scale(1.1);
      box-shadow: 0 12px 28px rgba(30, 58, 138, 0.4);
    }

    &:active {
      transform: scale(0.95);
      box-shadow: var(--shadow-md);
    }

    z-index: 99;
  }
}

// 动画
@keyframes spin {
  to { transform: rotate(360deg); }
}

@keyframes pulse {
  0% {
    transform: scale(1);
    opacity: 1;
  }
  100% {
    transform: scale(1.4);
    opacity: 0;
  }
}

@keyframes pulse-scale {
  0%, 100% {
    transform: scale(1);
  }
  50% {
    transform: scale(1.1);
  }
}

@keyframes progress-animation {
  0% {
    width: 0%;
  }
  50% {
    width: 100%;
  }
  100% {
    width: 0%;
  }
}

@keyframes fab-pulse {
  0% {
    transform: translate(-50%, -50%) scale(1);
    opacity: 1;
  }
  100% {
    transform: translate(-50%, -50%) scale(1.8);
    opacity: 0;
  }
}

@keyframes slideInLeft {
  from {
    opacity: 0;
    transform: translateX(-30px);
  }
  to {
    opacity: 1;
    transform: translateX(0);
  }
}

// 响应式设计 - 平板端优化
@media (max-width: 1024px) {
  .main-content {
    margin-left: 240px;
    width: calc(100% - 240px);
    padding: 24px;
  }

  .sidebar {
    width: 240px;

    &.collapsed {
      width: 64px;

      .sidebar-content {
        padding: 16px 8px;
      }
    }

    &:not(.collapsed) {
      width: 240px;
      box-shadow: var(--shadow-lg);
    }
  }

  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
  }

  .chart-container {
    min-height: 450px;
  }

  // 平板端预测控制面板
  .chart-container {
    .prediction-control-panel {
      min-width: 360px;
      padding: 16px 24px;

      .control-panel-content {
        gap: 12px;

        .control-label {
          font-size: 14px;
        }

        .control-value {
          font-size: 20px;

          strong {
            font-size: 28px;
          }
        }

        .control-slider {
          padding: 0 8px;
        }
      }
    }
  }
}

@media (max-width: 768px) {
  .main-layout {
    flex-direction: column;
  }

  .main-content {
    margin-left: 0;
    width: 100%;
    padding: 16px;
  }

  .sidebar {
    position: relative;
    top: 0;
    left: 0;
    width: 100%;
    border-right: none;
    border-bottom: 1px solid var(--border-color);
    box-shadow: none;
    max-height: 70vh;
    overflow: hidden;
    transition: max-height 0.3s ease, opacity 0.3s ease;

    .sidebar-content {
      padding: 16px;
      transition: opacity 0.2s ease;
    }

    &.collapsed {
      max-height: 0;
      border-bottom: none;

      .sidebar-content {
        opacity: 0;
        pointer-events: none;
      }
    }

    &:not(.collapsed) {
      max-height: 70vh;
      overflow-y: auto;

      .sidebar-content {
        opacity: 1;
      }
    }
  }

  .stats-grid {
    grid-template-columns: repeat(3, 1fr);
    gap: 12px;
    margin-bottom: 16px;
  }

  // 移动端 (平板竖屏) 统计卡片显示为 2 列
  @media (max-width: 600px) {
    .stats-grid {
      grid-template-columns: repeat(2, 1fr);
    }
  }

  // 移动端相似窗口列表优化
  .result-section {
    margin-bottom: 24px;

    .similar-windows-scroll {
      overflow-x: visible;
      overflow-y: visible;
      padding-bottom: 0;
    }

    .similar-windows-row {
      flex-direction: column;
      gap: 8px;
      padding: 0;

      .window-card-compact {
        flex: 1;
        width: 100%;
        padding: 10px;
        animation-delay: 0 !important;  // 禁用逐个加载动画

        .window-rank {
          font-size: 12px;
          margin-bottom: 6px;
        }

        .similarity-badge {
          top: 10px;
          right: 10px;
          padding: 2px 6px;
          font-size: 11px;
        }

        .window-dates-compact {
          margin: 6px 0 4px 0;

          .date-range {
            font-size: 10px;
          }
        }

        .window-kline {
          display: none;  // 移动端隐藏 K 线小图，加快加载
        }

        .window-metrics {
          gap: 4px;
          margin-bottom: 6px;

          .el-tag {
            font-size: 10px;
            padding: 1px 4px;
          }
        }

        .window-snippet {
          font-size: 10px;
          margin-bottom: 6px;

          .snippet-row {
            gap: 4px;
            margin-bottom: 1px;
          }
        }

        .preview-values {
          gap: 2px;
          margin-bottom: 6px;

          .preview-pill {
            padding: 1px 4px;
            font-size: 9px;
          }
        }

        .similarity-bar {
          height: 2px;
          margin-top: 6px;
        }
      }
    }
  }

  .chart-container {
    min-height: 350px;
  }

  .section-title {
    font-size: 12px;
  }

  // 移动端预测控制面板
  .chart-container {
    .prediction-control-panel {
      min-width: unset;
      width: calc(100% - 20px);
      left: 10px;
      right: 10px;
      transform: none;
      padding: 12px 16px;

      .control-panel-content {
        gap: 10px;

        .control-label {
          font-size: 14px;
        }

        .control-value {
          font-size: 18px;

          strong {
            font-size: 24px;
          }
        }

        .control-slider {
          width: 100%;
          padding: 0;
        }

        .el-tag {
          font-size: 11px;
        }
      }
    }
  }
}

@media (max-width: 640px) {
  .navbar {
    height: 52px;

    .brand-title {
      display: none;
    }
  }

  .main-layout {
    padding-top: 52px;
  }

  .main-content {
    margin-left: 0;
    width: 100%;
    padding: 12px;
  }

  .sidebar {
    top: 0;
    max-height: 60vh;
  }

  // 移动端小屏优化：统计卡片改为单列显示
  .stats-grid {
    grid-template-columns: 1fr;
    gap: 12px;
    margin-bottom: 16px;
  }

  .similar-windows-grid {
    grid-template-columns: 1fr;
  }

  .chart-container {
    min-height: 320px;
  }

  .stat-card {
    min-height: 100px;

    .stat-icon {
      width: 48px;
      height: 48px;
    }

    .stat-content {
      h4 {
        font-size: 12px;
      }

      .stat-value {
        font-size: 20px;
      }

      .stat-label {
        font-size: 11px;
      }
    }
  }

  .section-title {
    font-size: 11px;
  }

  .form-group {
    label {
      font-size: 12px;
    }
  }
}

// 特征对话框样式
.feature-dialog {
  .el-dialog__body {
    padding: 20px;
  }

  .feature-dialog-content {
    .feature-dialog-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      margin-bottom: 20px;
      padding-bottom: 15px;
      border-bottom: 1px solid var(--border-color);

      .feature-stats {
        font-size: 14px;
        color: var(--text-secondary);
        font-weight: 600;
      }
    }

    .feature-checkbox-group {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(300px, 1fr));
      gap: 12px;
      max-height: 400px;
      overflow-y: auto;
      padding: 10px 0;

      .feature-item {
        padding: 10px;
        background: var(--bg-tertiary);
        border-radius: var(--radius-md);
        transition: var(--transition-fast);

        &:hover {
          background: var(--bg-secondary);
          box-shadow: var(--shadow-sm);
        }

        .el-checkbox {
          width: 100%;

          .feature-name {
            font-weight: 500;
            margin-right: 8px;
          }

          .el-tag {
            font-family: monospace;
            opacity: 0.7;
          }
        }
      }
    }
  }

  .dialog-footer {
    display: flex;
    justify-content: space-between;
    align-items: center;

    .footer-left {
      display: flex;
      gap: 10px;
    }

    .footer-right {
      display: flex;
      gap: 10px;
    }
  }
}

// 工作原理对话框样式
.how-it-works-dialog {
  .el-dialog__body {
    padding: 20px;
    max-height: 70vh;
    overflow-y: auto;
  }

  .how-it-works-content {
    .help-section {
      padding: 20px;
      line-height: 1.8;

      h3 {
        color: var(--primary-color);
        margin: 24px 0 16px 0;
        font-size: 18px;
        font-weight: 600;

        &:first-child {
          margin-top: 0;
        }
      }

      h4 {
        color: var(--text-primary);
        margin: 16px 0 8px 0;
        font-size: 16px;
      }

      p {
        color: var(--text-secondary);
        margin: 12px 0;
        font-size: 15px;
      }

      ul {
        margin: 12px 0;
        padding-left: 24px;

        li {
          margin: 8px 0;
          color: var(--text-secondary);
          font-size: 15px;
        }
      }

      .step-desc {
        color: var(--text-secondary);
        font-size: 14px;
        line-height: 1.6;
        padding: 8px 0;
      }

      .analogy-box {
        background: var(--bg-tertiary);
        border-left: 4px solid var(--primary-color);
        padding: 16px 20px;
        border-radius: var(--radius-md);
        margin: 20px 0;

        p {
          margin-bottom: 12px;
        }

        ul {
          margin-top: 8px;
        }
      }

      .example-box {
        background: var(--bg-tertiary);
        border: 1px solid var(--border-color);
        padding: 20px;
        border-radius: var(--radius-md);
        margin: 20px 0;

        ol {
          margin-top: 12px;
          padding-left: 20px;

          li {
            margin: 16px 0;

            ul {
              margin-top: 8px;
              padding-left: 20px;
              list-style-type: disc;

              li {
                margin: 6px 0;
              }
            }
          }
        }

        strong {
          color: var(--primary-color);
        }
      }

      .ai-feature {
        background: var(--bg-tertiary);
        padding: 16px;
        border-radius: var(--radius-md);
        margin: 16px 0;

        h4 {
          color: var(--primary-color);
          margin-top: 0;
        }

        p {
          margin: 8px 0 0 0;
        }
      }

      .indicator-list {
        li {
          padding: 4px 0;

          strong {
            color: var(--text-primary);
            font-weight: 500;
          }
        }
      }

      &.risk-section {
        .risk-list {
          li {
            color: var(--warning-color);
            margin: 12px 0;
          }
        }

        .usage-list {
          li {
            color: var(--success-color);
            margin: 12px 0;
          }
        }
      }
    }

    .el-steps {
      margin: 20px 0;

      .el-step__title {
        font-size: 16px;
        font-weight: 500;
      }

      .el-step__description {
        margin-top: 8px;
      }
    }

    .el-collapse {
      border: none;
      margin: 20px 0;

      .el-collapse-item__header {
        font-size: 16px;
        font-weight: 500;
        height: 48px;
        background: var(--bg-tertiary);
        padding: 0 20px;
        border-radius: var(--radius-md);
        margin-bottom: 8px;
      }

      .el-collapse-item__content {
        padding: 16px 20px;
      }
    }
  }
}

// 移动端竖屏布局优化
.app-container.mobile-portrait {
  .main-layout {
    flex-direction: column;
  }

  .sidebar {
    position: relative;
    top: 0;
    left: 0;
    bottom: auto;
    width: 100%;
    height: auto;
    border-right: none;
    border-bottom: 1px solid var(--border-color);
  }

  .main-content {
    margin-left: 0;
    width: 100%;
  }
}

// 移动端横屏时的优化
@media screen and (orientation: landscape) and (max-width: 900px) and (max-height: 500px) {
  .app-container {
    .navbar {
      height: 45px;

      .navbar-content {
        padding: 0 12px;

        .brand {
          .brand-icon {
            width: 30px;
            height: 30px;
          }

          .brand-title {
            font-size: 14px;
          }
        }

        .navbar-right {
          gap: 8px;

          .status-indicator {
            padding: 4px 10px;
            font-size: 12px;
          }

          .theme-toggle,
          .user-avatar {
            width: 32px;
            height: 32px;
          }
        }
      }
    }

    .main-layout {
      padding-top: 45px;
    }

    .sidebar {
      top: 45px;
      width: 220px;
      height: calc(100vh - 45px);
      overflow-y: auto;
      overflow-x: hidden;

      &.collapsed {
        width: 50px;
      }

      // 优化滚动条
      &::-webkit-scrollbar {
        width: 4px;
      }

      &::-webkit-scrollbar-track {
        background: transparent;
      }

      &::-webkit-scrollbar-thumb {
        background: var(--text-muted);
        border-radius: 2px;
      }

      .sidebar-content {
        padding: 12px;
        display: flex;
        flex-direction: column;
        min-height: 100%;
      }

      .sidebar-section {
        margin-bottom: 16px;

        .section-title {
          font-size: 12px;
          margin-bottom: 8px;
        }

        .form-group {
          margin-bottom: 12px;

          label {
            font-size: 12px;
            margin-bottom: 4px;
          }
        }

        // 特征选择按钮组
        .feature-quick-select {
          display: flex;
          flex-wrap: wrap;
          gap: 4px;

          .el-button {
            flex: 1;
            min-width: auto;
            padding: 4px;
            font-size: 11px;
          }
        }
      }

      .sidebar-footer {
        margin-top: auto;
        position: sticky;
        bottom: 0;
        background: var(--bg-secondary);
        padding: 12px;
        border-top: 1px solid var(--border-color);

        .help-button,
        .run-button {
          height: 36px;
          font-size: 13px;
        }
      }
    }

    .main-content {
      margin-left: 220px;
      width: calc(100% - 220px);
      padding: 16px;

      .sidebar.collapsed ~ & {
        margin-left: 50px;
        width: calc(100% - 50px);
      }
    }

    // 统计卡片 - 横屏优化
    .stats-grid {
      grid-template-columns: repeat(4, 1fr);
      gap: 12px;
      margin-bottom: 16px;

      .stat-card {
        padding: 12px;

        .stat-icon {
          width: 36px;
          height: 36px;
        }

        .stat-content {
          h4 {
            font-size: 11px;
            margin-bottom: 2px;
          }

          .stat-value {
            font-size: 18px;
          }

          .stat-change,
          .stat-label {
            font-size: 10px;
          }
        }
      }
    }

    // 相似窗口 - 横屏优化
    .result-section {
      margin-bottom: 16px;

      .section-header {
        margin-bottom: 12px;

        h2 {
          font-size: 16px;
        }
      }

      .similar-windows-row {
        .window-card-compact {
          width: 160px;
          padding: 8px;

          .window-rank {
            font-size: 12px;
            margin-bottom: 4px;
          }

          .similarity-badge {
            font-size: 11px;
            padding: 1px 6px;
          }

          .window-dates-compact {
            margin: 12px 0 6px 0;

            .date-range {
              font-size: 10px;
            }
          }

          .similarity-bar {
            height: 2px;
          }
        }
      }
    }

    // 图表区域 - 横屏优化
    .chart-section {
      padding: 12px;

      .chart-header {
        margin-bottom: 12px;

        .chart-title {
          h2 {
            font-size: 14px;
          }

          .el-tag {
            height: 20px;
            font-size: 11px;
          }
        }

        .chart-actions {
          .el-button {
            padding: 4px 8px;
            font-size: 12px;
          }
        }
      }

      .chart-container {
        min-height: 350px;

        iframe {
          height: 350px !important;
        }

        .empty-chart {
          height: 300px;
        }
      }
    }

    // FAB按钮 - 横屏优化
    .fab-container {
      bottom: 16px;
      right: 16px;

      .fab {
        width: 48px;
        height: 48px;
      }
    }

    // Element Plus 组件横屏优化
    .el-input {
      .el-input__inner {
        height: 28px;
        font-size: 12px;
      }

      .el-input__prefix,
      .el-input__suffix {
        .el-icon {
          font-size: 14px;
        }
      }
    }

    .el-date-editor {
      width: 100% !important;

      .el-input__inner {
        font-size: 11px;
      }

      &.el-date-editor--daterange {
        width: 100% !important;
      }
    }

    .el-slider {
      .el-slider__runway {
        height: 4px;
      }

      .el-slider__button {
        width: 12px;
        height: 12px;
      }
    }

    .el-radio-group {
      .el-radio-button {
        .el-radio-button__inner {
          padding: 4px 12px;
          font-size: 12px;
        }
      }
    }

    .el-switch {
      height: 18px;
      line-height: 18px;

      .el-switch__core {
        height: 18px;
      }
    }

    .el-button {
      &.el-button--small {
        padding: 4px 10px;
        font-size: 12px;
      }
    }

    .el-dropdown {
      .el-dropdown-menu {
        .el-dropdown-menu__item {
          padding: 4px 12px;
          font-size: 12px;
          line-height: 20px;
        }
      }
    }

    .el-empty {
      padding: 20px 0;

      .el-empty__image {
        width: 80px;
      }

      .el-empty__description {
        font-size: 12px;
      }
    }

    // 对话框横屏优化
    .el-dialog {
      max-height: 90vh;

      .el-dialog__body {
        max-height: calc(90vh - 100px);
        overflow-y: auto;
      }
    }
  }
}

// 更宽的横屏设备（平板横屏）
@media screen and (orientation: landscape) and (min-width: 900px) and (max-width: 1200px) and (max-height: 800px) {
  .app-container {
    .navbar {
      height: 55px;
    }

    .main-layout {
      padding-top: 55px;
    }

    .sidebar {
      top: 55px;
      width: 260px;

      &.collapsed {
        width: 60px;
      }
    }

    .main-content {
      margin-left: 260px;
      width: calc(100% - 260px);
      padding: 20px;

      .sidebar.collapsed ~ & {
        margin-left: 60px;
        width: calc(100% - 60px);
      }
    }

    .stats-grid {
      grid-template-columns: repeat(4, 1fr);
      gap: 16px;
    }

    .chart-section {
      .chart-container {
        min-height: 450px;

        iframe {
          height: 450px !important;
        }
      }
    }
  }
}

// 评估结果区域样式
.evaluation-section {
  width: calc(100% - 88px); // 默认折叠状态：64px侧边栏 + 24px间距
  max-width: 1400px;
  margin: 32px auto;
  margin-left: 88px; // 64px收起的侧边栏 + 24px间距
  padding: 0 24px;
  animation: slideInUp 0.5s ease-out;
  transition: margin-left 0.3s ease, width 0.3s ease; // 添加过渡效果

  // 当侧边栏展开时调整布局
  &.sidebar-expanded {
    width: calc(100% - 304px); // 280px侧边栏 + 24px间距
    margin-left: 304px; // 280px侧边栏 + 24px间距
  }

  .section-title {
    display: flex;
    align-items: center;
    gap: 12px;
    font-size: 24px;
    font-weight: 600;
    color: var(--text-primary);
    margin-bottom: 24px;
    padding-bottom: 12px;
    border-bottom: 2px solid var(--border-color);

    .el-icon {
      color: var(--primary-color);
    }
  }

  // 评估指标卡片网格
  .evaluation-metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(240px, 1fr));
    gap: 16px;
    margin-bottom: 32px;

    .metric-card {
      background: var(--bg-secondary);
      border-radius: 12px;
      padding: 20px;
      display: flex;
      align-items: center;
      gap: 16px;
      box-shadow: var(--shadow-sm);
      transition: var(--transition-base);
      animation: fadeInScale 0.4s ease-out;
      animation-fill-mode: both;

      @for $i from 1 through 6 {
        &:nth-child(#{$i}) {
          animation-delay: #{$i * 0.05}s;
        }
      }

      &:hover {
        transform: translateY(-4px);
        box-shadow: var(--shadow-lg);
      }

      .metric-icon {
        width: 56px;
        height: 56px;
        border-radius: 12px;
        display: flex;
        align-items: center;
        justify-content: center;
        color: white;
        flex-shrink: 0;
      }

      .metric-content {
        flex: 1;
        min-width: 0;

        .metric-label {
          font-size: 12px;
          color: var(--text-muted);
          margin-bottom: 4px;
          white-space: nowrap;
          overflow: hidden;
          text-overflow: ellipsis;
        }

        .metric-value {
          font-size: 24px;
          font-weight: 700;
          color: var(--text-primary);
          line-height: 1.2;

          &.metric-success {
            color: var(--success-color);
          }

          &.metric-warning {
            color: var(--warning-color);
          }

          &.metric-danger {
            color: var(--danger-color);
          }
        }

        .metric-subtext {
          margin-top: 4px;
          font-size: 12px;
          color: var(--text-muted);
        }
      }
    }
  }

  // 评估表格容器
  .evaluation-table-container {
    background: var(--bg-secondary);
    border-radius: 12px;
    padding: 20px;
    box-shadow: var(--shadow-sm);
    transition: var(--transition-base);

    &:hover {
      box-shadow: var(--shadow-md);
    }

    .table-header {
      display: flex;
      justify-content: space-between;
      align-items: center;
      margin-bottom: 16px;

      .table-title {
        font-size: 16px;
        font-weight: 600;
        color: var(--text-primary);
      }
    }

    // 表格内样式增强
    .el-table {
      --el-table-border-color: var(--border-color);
      --el-table-row-hover-bg-color: var(--bg-tertiary);

      tbody {
        tr {
          transition: var(--transition-fast);

          &:hover {
            background-color: var(--bg-tertiary) !important;

            td {
              background-color: transparent !important;
            }
          }
        }
      }

      .error-low {
        color: var(--success-color);
        font-weight: 600;
      }

      .error-medium {
        color: var(--warning-color);
        font-weight: 600;
      }

      .error-high {
        color: var(--danger-color);
        font-weight: 600;
      }
    }
  }
}

// 评估动画
@keyframes fadeInScale {
  from {
    opacity: 0;
    transform: scale(0.9);
  }
  to {
    opacity: 1;
    transform: scale(1);
  }
}

@keyframes slideInUp {
  from {
    opacity: 0;
    transform: translateY(20px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

// 响应式适配
@media (max-width: 1024px) {
  .evaluation-section {
    width: calc(100% - 64px); // 平板端始终使用折叠侧边栏宽度
    margin-left: 80px; // 64px + 16px间距
    padding: 0 16px;

    &.sidebar-expanded {
      width: calc(100% - 64px); // 平板端强制折叠
      margin-left: 80px;
    }

    .evaluation-metrics-grid {
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 12px;

      .metric-card {
        padding: 16px;

        .metric-icon {
          width: 48px;
          height: 48px;
        }

        .metric-content .metric-value {
          font-size: 20px;
        }
      }
    }
  }
}

@media (max-width: 640px) {
  .evaluation-section {
    width: 100%; // 移动端全宽
    margin-left: 0; // 无左边距
    padding: 0 12px;

    &.sidebar-expanded {
      width: 100%;
      margin-left: 0;
    }

    .evaluation-metrics-grid {
      grid-template-columns: 1fr;

      .metric-card {
        padding: 16px 20px;
      }
    }

    .evaluation-table-container {
      padding: 12px;
      overflow-x: auto;

      .table-header {
        flex-direction: column;
        align-items: flex-start;
        gap: 12px;
      }
    }
  }
}
</style>















