<template>
  <div class="home-container">
    <!-- 背景装饰 -->
    <div class="bg-decoration">
      <div class="circle circle-1"></div>
      <div class="circle circle-2"></div>
      <div class="circle circle-3"></div>
    </div>

    <!-- 页面标题 -->
    <div class="page-header">
      <div class="icon-wrapper">
        <span class="icon">✈️</span>
      </div>
      <h1 class="page-title">智能旅行助手</h1>
      <p class="page-subtitle">基于AI多智能体协作的个性化旅行规划，让每一次出行都完美无忧</p>
    </div>

    <a-card class="form-card" :bordered="false">
      <a-form
        :model="formData"
        layout="vertical"
        @finish="handleSubmit"
      >
        <!-- 第一步：目的地和日期 -->
        <div class="form-section">
          <div class="section-header">
            <span class="section-icon">📍</span>
            <span class="section-title">目的地与日期</span>
            <!-- 用户历史标签 -->
            <a-tag v-if="lastVisited" color="purple" class="history-tag">
              上次去过：{{ lastVisited }}
            </a-tag>
          </div>

          <a-row :gutter="24">
            <a-col :span="8">
              <a-form-item name="city" :rules="[{ required: true, message: '请输入目的地城市' }]">
                <template #label>
                  <span class="form-label">目的地城市</span>
                </template>
                <a-input
                  v-model:value="formData.city"
                  placeholder="例如：北京"
                  size="large"
                  class="custom-input"
                >
                  <template #prefix>
                    <span style="color: #1890ff;">🏙️</span>
                  </template>
                </a-input>
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item name="start_date" :rules="[{ required: true, message: '请选择开始日期' }]">
                <template #label>
                  <span class="form-label">开始日期</span>
                </template>
                <a-date-picker
                  v-model:value="formData.start_date"
                  style="width: 100%"
                  size="large"
                  class="custom-input"
                  placeholder="选择日期"
                />
              </a-form-item>
            </a-col>
            <a-col :span="6">
              <a-form-item name="end_date" :rules="[{ required: true, message: '请选择结束日期' }]">
                <template #label>
                  <span class="form-label">结束日期</span>
                </template>
                <a-date-picker
                  v-model:value="formData.end_date"
                  style="width: 100%"
                  size="large"
                  class="custom-input"
                  placeholder="选择日期"
                />
              </a-form-item>
            </a-col>
            <a-col :span="4">
              <a-form-item>
                <template #label>
                  <span class="form-label">旅行天数</span>
                </template>
                <div class="days-display-compact">
                  <span class="days-value">{{ formData.travel_days }}</span>
                  <span class="days-unit">天</span>
                </div>
              </a-form-item>
            </a-col>
          </a-row>
        </div>

        <!-- 第二步：偏好设置 -->
        <div class="form-section">
          <div class="section-header">
            <span class="section-icon">⚙️</span>
            <span class="section-title">偏好设置</span>
          </div>

          <a-row :gutter="24">
            <a-col :span="8">
              <a-form-item name="transportation">
                <template #label>
                  <span class="form-label">交通方式</span>
                </template>
                <a-select v-model:value="formData.transportation" size="large" class="custom-select">
                  <a-select-option value="地铁">🚇 地铁</a-select-option>
                  <a-select-option value="公共交通">🚌 公共交通</a-select-option>
                  <a-select-option value="自驾">🚗 自驾</a-select-option>
                  <a-select-option value="步行">🚶 步行</a-select-option>
                  <a-select-option value="混合">🔀 混合</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item name="accommodation">
                <template #label>
                  <span class="form-label">住宿偏好</span>
                </template>
                <a-select v-model:value="formData.accommodation" size="large" class="custom-select">
                  <a-select-option value="经济型酒店">💰 经济型酒店</a-select-option>
                  <a-select-option value="舒适型酒店">🏨 舒适型酒店</a-select-option>
                  <a-select-option value="豪华酒店">⭐ 豪华酒店</a-select-option>
                  <a-select-option value="民宿">🏡 民宿</a-select-option>
                </a-select>
              </a-form-item>
            </a-col>
            <a-col :span="8">
              <a-form-item name="preferences">
                <template #label>
                  <span class="form-label">旅行偏好</span>
                </template>
                <div class="preference-tags">
                  <a-checkbox-group v-model:value="formData.preferences" class="custom-checkbox-group">
                    <a-checkbox value="历史文化" class="preference-tag">🏛️ 历史文化</a-checkbox>
                    <a-checkbox value="自然风光" class="preference-tag">🏞️ 自然风光</a-checkbox>
                    <a-checkbox value="美食" class="preference-tag">🍜 美食</a-checkbox>
                    <a-checkbox value="购物" class="preference-tag">🛍️ 购物</a-checkbox>
                    <a-checkbox value="艺术" class="preference-tag">🎨 艺术</a-checkbox>
                    <a-checkbox value="休闲" class="preference-tag">☕ 休闲</a-checkbox>
                  </a-checkbox-group>
                </div>
              </a-form-item>
            </a-col>
          </a-row>
        </div>

        <!-- 第三步：额外要求 -->
        <div class="form-section">
          <div class="section-header">
            <span class="section-icon">💬</span>
            <span class="section-title">额外要求</span>
          </div>

          <a-form-item name="free_text_input">
            <a-textarea
              v-model:value="formData.free_text_input"
              placeholder="请输入您的额外要求，例如：想去看升旗、需要无障碍设施、对海鲜过敏等..."
              :rows="3"
              size="large"
              class="custom-textarea"
            />
          </a-form-item>
        </div>

        <!-- 提交按钮 -->
        <a-form-item>
          <a-button
            type="primary"
            html-type="submit"
            :loading="loading"
            size="large"
            block
            class="submit-button"
          >
            <template v-if="!loading">
              <span class="button-icon">🚀</span>
              <span>开始规划我的旅行</span>
            </template>
            <template v-else>
              <span>正在生成中...</span>
            </template>
          </a-button>
        </a-form-item>

        <!-- SSE 实时进度（替代假进度条） -->
        <a-form-item v-if="loading">
          <div class="loading-container">
            <!-- 步骤指示器 -->
            <div class="sse-steps">
              <div class="sse-step" :class="{ active: currentStep >= 1, done: currentStep > 1 }">
                <div class="step-dot">
                  <span v-if="currentStep > 1">✅</span>
                  <span v-else-if="currentStep === 1" class="pulse-dot"></span>
                  <span v-else>🔍</span>
                </div>
                <div class="step-label">搜索数据</div>
                <div class="step-sublabel">{{ stepLabels[1] }}</div>
              </div>
              <div class="step-line" :class="{ active: currentStep >= 2 }"></div>
              <div class="sse-step" :class="{ active: currentStep >= 2, done: currentStep > 2 }">
                <div class="step-dot">
                  <span v-if="currentStep > 2">✅</span>
                  <span v-else-if="currentStep === 2" class="pulse-dot"></span>
                  <span v-else>🧹</span>
                </div>
                <div class="step-label">数据清洗</div>
                <div class="step-sublabel">{{ stepLabels[2] }}</div>
              </div>
              <div class="step-line" :class="{ active: currentStep >= 3 }"></div>
              <div class="sse-step" :class="{ active: currentStep >= 3, done: currentStep > 3 }">
                <div class="step-dot">
                  <span v-if="currentStep > 3">✅</span>
                  <span v-else-if="currentStep === 3" class="pulse-dot"></span>
                  <span v-else>📋</span>
                </div>
                <div class="step-label">AI 规划</div>
                <div class="step-sublabel">{{ stepLabels[3] }}</div>
              </div>
            </div>

            <!-- 进度条 -->
            <a-progress
              :percent="sseProgress"
              :status="sseProgress >= 100 ? 'success' : 'active'"
              :stroke-color="{
                '0%': '#667eea',
                '100%': '#764ba2',
              }"
              :stroke-width="8"
            />

            <!-- 错误提示 -->
            <a-alert
              v-if="sseError"
              type="error"
              :message="sseError"
              closable
              style="margin-top: 16px"
              @close="sseError = ''"
            />
          </div>
        </a-form-item>
      </a-form>
    </a-card>

    <!-- 历史计划 -->
    <a-card v-if="planHistory.length > 0" class="history-card" :bordered="false" title="📚 历史计划">
      <template #extra>
        <a-button type="link" size="small" @click="loadHistory">🔄 刷新</a-button>
      </template>
      <a-list :data-source="planHistory.slice(0, 6)" :grid="{ gutter: 16, column: 3 }">
        <template #renderItem="{ item }">
          <a-list-item>
            <a-card
              hoverable
              size="small"
              class="history-item"
              @click="loadHistoryPlan(item.plan_id)"
            >
              <div class="history-city">🏙️ {{ item.city }}</div>
              <div class="history-meta">
                {{ item.start_date }} ~ {{ item.end_date }} · {{ item.travel_days }}天
              </div>
              <div class="history-tags">
                <a-tag v-for="p in item.preferences.slice(0, 2)" :key="p" size="small">{{ p }}</a-tag>
              </div>
              <div class="history-time">🕐 {{ formatHistoryTime(item.created_at) }}</div>
            </a-card>
          </a-list-item>
        </template>
      </a-list>
    </a-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, watch, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { generateTripPlanStream, getUserProfile, getPlanHistory } from '@/services/api'
import type { TripFormData, PlanSummary } from '@/types'
import type { Dayjs } from 'dayjs'

const router = useRouter()
const loading = ref(false)

// --- 用户身份（localStorage 持久化） ---
const USER_ID_KEY = 'trip_planner_user_id'
const userId = ref(localStorage.getItem(USER_ID_KEY) || '')
const lastVisited = ref('')

// 历史计划列表
const planHistory = ref<PlanSummary[]>([])
const historyLoading = ref(false)

onMounted(async () => {
  // 首次访问：生成唯一 user_id
  if (!userId.value) {
    userId.value = 'user_' + Date.now().toString(36) + '_' + Math.random().toString(36).slice(2, 8)
    localStorage.setItem(USER_ID_KEY, userId.value)
  }

  // 后台加载用户历史和偏好
  try {
    const [profile, historyRes] = await Promise.all([
      getUserProfile(userId.value),
      getPlanHistory(userId.value)
    ])
    if (profile?.visited_cities?.length) {
      lastVisited.value = profile.visited_cities[profile.visited_cities.length - 1]
    }
    if (historyRes?.plans) {
      planHistory.value = historyRes.plans
    }
  } catch { /* 静默失败 */ }
})

// --- SSE 进度状态 ---
const currentStep = ref(0)        // 0-3
const stepLabels = ref<Record<number, string>>({
  1: '景点·天气·酒店·餐厅',
  2: '结构化提取关键信息',
  3: '生成详细行程计划'
})
const sseProgress = ref(0)
const sseError = ref('')

const formData = reactive<{ city: string; start_date: Dayjs | null; end_date: Dayjs | null; travel_days: number; transportation: string; accommodation: string; preferences: string[]; free_text_input: string; user_id: string }>({
  city: '',
  start_date: null,
  end_date: null,
  travel_days: 1,
  transportation: '地铁',
  accommodation: '经济型酒店',
  preferences: [],
  free_text_input: '',
  user_id: userId.value
})

// 监听日期变化，自动计算旅行天数
watch([() => formData.start_date, () => formData.end_date], ([start, end]) => {
  if (start && end) {
    const days = end.diff(start, 'day') + 1
    if (days > 0 && days <= 30) {
      formData.travel_days = days
    } else if (days > 30) {
      message.warning('旅行天数不能超过30天')
      formData.end_date = null
    } else {
      message.warning('结束日期不能早于开始日期')
      formData.end_date = null
    }
  }
})

const handleSubmit = async () => {
  if (!formData.start_date || !formData.end_date) {
    message.error('请选择日期')
    return
  }

  loading.value = true
  currentStep.value = 0
  sseProgress.value = 0
  sseError.value = ''

  const requestData: TripFormData = {
    city: formData.city,
    start_date: formData.start_date.format('YYYY-MM-DD'),
    end_date: formData.end_date.format('YYYY-MM-DD'),
    travel_days: formData.travel_days,
    transportation: formData.transportation,
    accommodation: formData.accommodation,
    preferences: formData.preferences,
    free_text_input: formData.free_text_input,
    user_id: userId.value
  }

  try {
    await generateTripPlanStream(
      requestData,
      // onEvent: SSE 事件回调
      (eventType, data) => {
        switch (eventType) {
          case 'query_start':
            currentStep.value = 1
            sseProgress.value = 10
            stepLabels.value[1] = data.status || `🔍 搜索 ${data.city || formData.city}…`
            break
          case 'query_complete':
            currentStep.value = 2
            sseProgress.value = 40
            stepLabels.value[2] = data.status || '正在清洗和筛选数据…'
            break
          case 'planning_start':
            currentStep.value = 3
            sseProgress.value = 55
            stepLabels.value[3] = data.status || 'AI 正在规划行程…'
            break
          case 'plan_complete':
            currentStep.value = 3
            sseProgress.value = 100
            stepLabels.value[3] = '✅ 完成！'
            if (data.plan) {
              sessionStorage.setItem('tripPlan', JSON.stringify(data.plan))
              if (data.plan_id) {
                sessionStorage.setItem('currentPlanId', data.plan_id)
              }
              if (lastVisited.value !== requestData.city) {
                lastVisited.value = requestData.city
              }
              message.success('旅行计划生成成功！')
              setTimeout(() => router.push('/result'), 600)
            }
            break
        }
      },
      // onError: 错误回调
      (error) => {
        sseError.value = error
        message.error(error)
      }
    )
  } catch (error: any) {
    message.error(error.message || '生成旅行计划失败，请稍后重试')
  } finally {
    setTimeout(() => {
      loading.value = false
      currentStep.value = 0
      sseProgress.value = 0
    }, 1200)
  }
}

// --- 历史计划 ---
const loadHistory = async () => {
  historyLoading.value = true
  try {
    const res = await getPlanHistory(userId.value)
    if (res?.plans) planHistory.value = res.plans
  } catch { /* 静默 */ }
  finally { historyLoading.value = false }
}

const loadHistoryPlan = async (planId: string) => {
  try {
    const apiBase = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'
    const res = await fetch(`${apiBase}/api/trip/plan/${planId}`)
    const data = await res.json()
    if (data?.plan) {
      sessionStorage.setItem('tripPlan', JSON.stringify(data.plan))
      sessionStorage.setItem('currentPlanId', planId)
      message.success('已加载历史计划')
      router.push('/result')
    }
  } catch {
    message.error('加载历史计划失败')
  }
}

const formatHistoryTime = (iso: string) => {
  const d = new Date(iso)
  const now = new Date()
  const diff = now.getTime() - d.getTime()
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return d.toLocaleDateString('zh-CN')
}
</script>

<style scoped>
.home-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  padding: 60px 20px;
  position: relative;
  overflow: hidden;
}

/* 背景装饰 */
.bg-decoration {
  position: absolute;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  pointer-events: none;
  overflow: hidden;
}

.circle {
  position: absolute;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.1);
  animation: float 20s infinite ease-in-out;
}

.circle-1 { width: 300px; height: 300px; top: -100px; left: -100px; animation-delay: 0s; }
.circle-2 { width: 200px; height: 200px; top: 50%; right: -50px; animation-delay: 5s; }
.circle-3 { width: 150px; height: 150px; bottom: -50px; left: 30%; animation-delay: 10s; }

@keyframes float {
  0%, 100% { transform: translateY(0) rotate(0deg); }
  50% { transform: translateY(-30px) rotate(180deg); }
}

/* 页面标题 */
.page-header {
  text-align: center;
  margin-bottom: 50px;
  animation: fadeInDown 0.8s ease-out;
  position: relative;
  z-index: 1;
}

.icon-wrapper { margin-bottom: 20px; }

.icon {
  font-size: 80px;
  display: inline-block;
  animation: bounce 2s infinite;
}

@keyframes bounce {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-20px); }
}

.page-title {
  font-size: 56px;
  font-weight: 800;
  color: #ffffff;
  margin-bottom: 16px;
  text-shadow: 3px 3px 6px rgba(0, 0, 0, 0.3);
  letter-spacing: 2px;
}

.page-subtitle {
  font-size: 20px;
  color: rgba(255, 255, 255, 0.95);
  margin: 0;
  font-weight: 300;
}

/* 表单卡片 */
.form-card {
  max-width: 900px;
  margin: 0 auto;
  border-radius: 24px;
  box-shadow: 0 30px 80px rgba(0, 0, 0, 0.4);
  animation: fadeInUp 0.8s ease-out;
  position: relative;
  z-index: 1;
  backdrop-filter: blur(10px);
  background: rgba(255, 255, 255, 0.98) !important;
}

/* 表单分区 */
.form-section {
  margin-bottom: 28px;
  padding: 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
  border-radius: 16px;
  border: 1px solid #e8e8e8;
  transition: all 0.3s ease;
}

.form-section:hover {
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.section-header {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
  padding-bottom: 12px;
  border-bottom: 2px solid #667eea;
}

.section-icon { font-size: 24px; margin-right: 12px; }

.section-title {
  font-size: 18px;
  font-weight: 600;
  color: #333;
  flex: 1;
}

.history-tag {
  margin-left: auto;
  font-size: 13px;
  border-radius: 12px;
}

.form-label { font-size: 15px; font-weight: 500; color: #555; }

/* 输入框 */
.custom-input :deep(.ant-input),
.custom-input :deep(.ant-picker) {
  border-radius: 12px;
  border: 2px solid #e8e8e8;
  transition: all 0.3s ease;
}
.custom-input :deep(.ant-input:hover),
.custom-input :deep(.ant-picker:hover) { border-color: #667eea; }
.custom-input :deep(.ant-input:focus),
.custom-input :deep(.ant-picker-focused) {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* 选择框 */
.custom-select :deep(.ant-select-selector) {
  border-radius: 12px !important;
  border: 2px solid #e8e8e8 !important;
  transition: all 0.3s ease;
}
.custom-select:hover :deep(.ant-select-selector) { border-color: #667eea !important; }
.custom-select :deep(.ant-select-focused .ant-select-selector) {
  border-color: #667eea !important;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1) !important;
}

/* 天数 */
.days-display-compact {
  display: flex;
  align-items: center;
  justify-content: center;
  height: 40px;
  padding: 8px 16px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 12px;
  color: white;
}
.days-display-compact .days-value { font-size: 24px; font-weight: 700; margin-right: 4px; }
.days-display-compact .days-unit { font-size: 14px; }

/* 偏好标签 */
.preference-tags { display: flex; flex-wrap: wrap; gap: 8px; }
.custom-checkbox-group { display: flex; flex-wrap: wrap; gap: 8px; width: 100%; }
.preference-tag :deep(.ant-checkbox-wrapper) {
  margin: 0 !important;
  padding: 8px 16px;
  border: 2px solid #e8e8e8;
  border-radius: 20px;
  transition: all 0.3s ease;
  background: white;
  font-size: 14px;
}
.preference-tag :deep(.ant-checkbox-wrapper:hover) { border-color: #667eea; background: #f5f7ff; }
.preference-tag :deep(.ant-checkbox-wrapper-checked) {
  border-color: #667eea;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
}

/* 文本域 */
.custom-textarea :deep(.ant-input) {
  border-radius: 12px;
  border: 2px solid #e8e8e8;
  transition: all 0.3s ease;
}
.custom-textarea :deep(.ant-input:hover) { border-color: #667eea; }
.custom-textarea :deep(.ant-input:focus) {
  border-color: #667eea;
  box-shadow: 0 0 0 3px rgba(102, 126, 234, 0.1);
}

/* 提交按钮 */
.submit-button {
  height: 56px;
  border-radius: 28px;
  font-size: 18px;
  font-weight: 600;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border: none;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
  transition: all 0.3s ease;
}
.submit-button:hover { transform: translateY(-2px); box-shadow: 0 12px 32px rgba(102, 126, 234, 0.5); }
.submit-button:active { transform: translateY(0); }
.button-icon { margin-right: 8px; font-size: 20px; }

/* ===== SSE 步骤指示器 ===== */
.loading-container {
  text-align: center;
  padding: 28px 24px;
  background: linear-gradient(135deg, #f5f7fa 0%, #ffffff 100%);
  border-radius: 16px;
  border: 2px dashed #667eea;
}

.sse-steps {
  display: flex;
  align-items: flex-start;
  justify-content: center;
  gap: 0;
  margin-bottom: 24px;
}

.sse-step {
  display: flex;
  flex-direction: column;
  align-items: center;
  width: 120px;
  opacity: 0.45;
  transition: all 0.4s ease;
}

.sse-step.active { opacity: 1; }
.sse-step.done { opacity: 0.9; }

.step-dot {
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: #e8e8e8;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 18px;
  transition: all 0.4s ease;
  margin-bottom: 8px;
}

.sse-step.active .step-dot {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  box-shadow: 0 0 0 6px rgba(102, 126, 234, 0.15);
}

.sse-step.done .step-dot {
  background: linear-gradient(135deg, #52c41a 0%, #389e0d 100%);
}

.pulse-dot {
  width: 12px;
  height: 12px;
  border-radius: 50%;
  background: white;
  animation: pulse 1s infinite;
}

@keyframes pulse {
  0%, 100% { transform: scale(1); opacity: 1; }
  50% { transform: scale(1.4); opacity: 0.6; }
}

.step-line {
  width: 40px;
  height: 3px;
  background: #e8e8e8;
  margin-top: 20px;
  border-radius: 2px;
  transition: background 0.5s ease;
}
.step-line.active { background: linear-gradient(90deg, #667eea, #764ba2); }

.step-label {
  font-size: 14px;
  font-weight: 600;
  color: #333;
  margin-bottom: 2px;
}

.step-sublabel {
  font-size: 11px;
  color: #999;
  white-space: nowrap;
}

/* ===== 历史计划 ===== */
.history-card {
  max-width: 900px;
  margin: 24px auto;
  border-radius: 24px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.3);
  background: rgba(255, 255, 255, 0.98) !important;
  position: relative;
  z-index: 1;
}

.history-item {
  border-radius: 12px;
  transition: all 0.3s ease;
  cursor: pointer;
}

.history-item:hover {
  transform: translateY(-4px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.25);
}

.history-city {
  font-size: 16px;
  font-weight: 700;
  color: #333;
  margin-bottom: 4px;
}

.history-meta {
  font-size: 12px;
  color: #999;
  margin-bottom: 6px;
}

.history-tags {
  margin-bottom: 4px;
}

.history-time {
  font-size: 11px;
  color: #bbb;
}

/* 动画 */
@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-30px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(30px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
