<template>
  <div class="result-container">
    <!-- 页面头部 -->
    <div class="page-header">
      <a-button class="back-button" size="large" @click="goBack">
        ← 返回首页
      </a-button>
      <a-space size="middle">
        <a-button v-if="!editMode" @click="toggleEditMode" type="default">
          ✏️ 编辑行程
        </a-button>
        <a-button v-else @click="saveChanges" type="primary">
          💾 保存修改
        </a-button>
        <a-button v-if="editMode" @click="cancelEdit" type="default">
          ❌ 取消编辑
        </a-button>

        <!-- AI 微调按钮 -->
        <a-button v-if="!editMode" type="primary" class="chat-toggle-btn" @click="chatVisible = !chatVisible">
          🤖 AI 微调
        </a-button>

        <!-- 导出按钮 -->
        <a-dropdown v-if="!editMode">
          <template #overlay>
            <a-menu>
              <a-menu-item key="image" @click="exportAsImage">📷 导出为图片</a-menu-item>
              <a-menu-item key="pdf" @click="exportAsPDF">📄 导出为PDF</a-menu-item>
            </a-menu>
          </template>
          <a-button type="default">📥 导出行程 <DownOutlined /></a-button>
        </a-dropdown>
      </a-space>
    </div>

    <!-- AI 微调聊天面板 -->
    <div v-if="chatVisible && tripPlan" class="chat-panel">
      <a-card :bordered="false" size="small" class="chat-card" title="🤖 AI 微调助手">
        <template #extra>
          <a-button type="text" size="small" @click="chatVisible = false">✕</a-button>
        </template>

        <!-- 提示文字 -->
        <div v-if="!currentPlanId" class="chat-warning">
          ⚠️ 未找到 plan_id，无法使用微调功能。请重新生成计划。
        </div>

        <!-- 聊天消息 -->
        <div class="chat-body" ref="chatBodyRef">
          <div v-if="chatMessages.length === 0" class="chat-hint">
            💡 试试这些修改：<br/>
            • "第1天早餐店离酒店太远了，换一家步行10分钟以内的"<br/>
            • "第2天下午想加一个博物馆"<br/>
            • "第3天下雨，改成室内景点吧"
          </div>
          <div v-for="(msg, i) in chatMessages" :key="i" class="chat-msg" :class="'msg-' + msg.role">
            <div class="msg-bubble">
              <div class="msg-text">{{ msg.content }}</div>
              <div v-if="msg.changes && msg.changes.length" class="msg-changes">
                <a-tag v-for="(c, j) in msg.changes" :key="j" color="green" size="small">✅ {{ c }}</a-tag>
              </div>

              <!-- 多方案选择 -->
              <div v-if="msg.role === 'ai' && msg.options && msg.options.length > 1 && (msg.pending || msg.applying)" class="msg-options">
                <div class="options-label">👇 请选择你想采用的方案（或直接在输入框指定其他方案）：</div>
                <div class="options-list">
                  <a-tag
                    v-for="(opt, oi) in msg.options"
                    :key="oi"
                    :color="msg.selectedOption === oi ? '#667eea' : 'default'"
                    class="option-tag"
                    @click="msg.selectedOption = msg.selectedOption === oi ? undefined : oi"
                  >
                    {{ opt }}
                  </a-tag>
                </div>
              </div>

              <!-- AI 回复后的操作区 -->
              <div v-if="msg.role === 'ai' && (msg.pending || msg.applying)" class="msg-actions">
                <template v-if="msg.applying">
                  <a-spin size="small" />
                  <span class="applying-text">正在调用工具修改计划…</span>
                </template>
                <template v-else>
                  <a-button type="primary" size="small" @click="handleApplyChanges(i)">
                    🤝 帮我改
                  </a-button>
                  <a-button size="small" @click="handleEditMyself">
                    ✏️ 自己编辑
                  </a-button>
                </template>
              </div>
            </div>
          </div>
          <div v-if="chatLoading" class="chat-loading">
            <a-spin size="small" /> AI 思考中...
          </div>
        </div>

        <!-- 输入区 -->
        <div class="chat-input" v-if="currentPlanId">
          <a-textarea
            v-model:value="chatMessage"
            placeholder="输入修改请求，例如：第1天早餐店离酒店太远了..."
            :rows="2"
            :disabled="chatLoading"
            @pressEnter="handleChatSend"
          />
          <a-button
            type="primary"
            :loading="chatLoading"
            :disabled="!chatMessage.trim()"
            @click="handleChatSend"
            class="chat-send-btn"
          >
            ➤
          </a-button>
        </div>
      </a-card>
    </div>

    <div v-if="tripPlan" class="content-wrapper">
      <!-- 侧边导航 -->
      <div class="side-nav">
        <a-affix :offset-top="80">
          <a-menu mode="inline" :selected-keys="[activeSection]" @click="scrollToSection">
            <a-menu-item key="overview"><span>📋 行程概览</span></a-menu-item>
            <a-menu-item key="budget" v-if="tripPlan.budget"><span>💰 预算明细</span></a-menu-item>
            <a-menu-item key="map"><span>📍 景点地图</span></a-menu-item>
            <a-menu-item key="timeline"><span>🕐 时间线</span></a-menu-item>
            <a-sub-menu key="days" title="📅 每日行程">
              <a-menu-item v-for="(day, index) in tripPlan.days" :key="`day-${index}`">
                第{{ day.day_index + 1 }}天
              </a-menu-item>
            </a-sub-menu>
            <a-menu-item key="weather" v-if="tripPlan.weather_info?.length">
              <span>🌤️ 天气信息</span>
            </a-menu-item>
          </a-menu>
        </a-affix>
      </div>

      <!-- 主内容区 -->
      <div class="main-content">
        <!-- 顶部：概览 + 地图 -->
        <div class="top-info-section">
          <div class="left-info">
            <a-card id="overview" :title="`${tripPlan.city}旅行计划`" :bordered="false" class="overview-card">
              <div class="overview-content">
                <div class="info-item">
                  <span class="info-label">📅 日期</span>
                  <span class="info-value">{{ tripPlan.start_date }} 至 {{ tripPlan.end_date }}（{{ tripPlan.days.length }}天）</span>
                </div>
                <div class="info-item">
                  <span class="info-label">💡 建议</span>
                  <span class="info-value">{{ tripPlan.overall_suggestions }}</span>
                </div>
              </div>
            </a-card>

            <a-card id="budget" v-if="tripPlan.budget" title="💰 预算明细" :bordered="false" class="budget-card">
              <div class="budget-grid">
                <div class="budget-item">
                  <div class="budget-icon">🎫</div>
                  <div class="budget-label">景点门票</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_attractions }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-icon">🏨</div>
                  <div class="budget-label">酒店住宿</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_hotels }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-icon">🍽️</div>
                  <div class="budget-label">餐饮费用</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_meals }}</div>
                </div>
                <div class="budget-item">
                  <div class="budget-icon">🚇</div>
                  <div class="budget-label">交通费用</div>
                  <div class="budget-value">¥{{ tripPlan.budget.total_transportation }}</div>
                </div>
              </div>
              <div class="budget-total">
                <span class="total-label">预估总费用</span>
                <span class="total-value">¥{{ tripPlan.budget.total }}</span>
              </div>
            </a-card>
          </div>

          <div class="right-map">
            <a-card id="map" title="📍 景点地图" :bordered="false" class="map-card">
              <div id="amap-container" style="width: 100%; height: 100%"></div>
            </a-card>
          </div>
        </div>

        <!-- 每日行程 -->
        <a-card title="📅 每日行程" :bordered="false" class="days-card">
          <a-collapse v-model:activeKey="activeDays" accordion>
            <a-collapse-panel
              v-for="(day, index) in tripPlan.days"
              :key="index"
              :id="`day-${index}`"
            >
              <template #header>
                <div class="day-header">
                  <span class="day-title">第{{ day.day_index + 1 }}天</span>
                  <span class="day-date">{{ day.date }}</span>
                  <a-tag color="purple" style="margin-left: 12px">{{ day.attractions.length }}景点 · {{ day.meals.length }}餐</a-tag>
                </div>
              </template>

              <div class="day-info">
                <div class="info-row">
                  <span class="label">📝 行程描述</span>
                  <span class="value">{{ day.description }}</span>
                </div>
                <div class="info-row">
                  <span class="label">🚗 交通</span>
                  <span class="value">{{ day.transportation }}</span>
                </div>
              </div>

              <!-- 时间线视图 -->
              <a-divider orientation="left">🕐 时间线</a-divider>
              <div class="timeline">
                <div
                  v-for="item in getDayTimeline(day)"
                  :key="item.key"
                  class="timeline-item"
                  :class="{
                    'is-meal': item.kind === 'meal',
                    'is-attraction': item.kind === 'attraction',
                    'is-transport': item.kind === 'transport'
                  }"
                >
                  <!-- 交通连接线 -->
                  <template v-if="item.kind === 'transport'">
                    <div class="timeline-time"></div>
                    <div class="timeline-dot transport-dot">
                      <span>{{ item.icon }}</span>
                    </div>
                    <div class="timeline-content transport-content">
                      <div class="transport-label">
                        <span class="transport-icon">{{ item.icon }}</span>
                        <span class="transport-text">{{ item.from }}</span>
                        <span class="transport-arrow">→</span>
                        <span class="transport-text">{{ item.to }}</span>
                      </div>
                      <div class="transport-mode">{{ item.name }}</div>
                    </div>
                  </template>

                  <!-- 景点/餐饮 -->
                  <template v-else>
                    <div class="timeline-time">{{ item.time }}</div>
                    <div class="timeline-dot">
                      <span v-if="item.kind === 'attraction'">🏛</span>
                      <span v-else-if="item.type === 'breakfast'">🌅</span>
                      <span v-else-if="item.type === 'lunch'">☀️</span>
                      <span v-else-if="item.type === 'dinner'">🌙</span>
                      <span v-else>🍽</span>
                    </div>
                    <div class="timeline-content">
                      <div class="timeline-title">{{ item.name }}</div>
                      <div class="timeline-meta">
                        <span v-if="item.kind === 'attraction'">
                          📍 {{ item.address }} · ⏱ {{ item.visit_duration }}分钟 · ¥{{ item.ticket_price }}
                        </span>
                        <span v-else>
                          {{ getMealLabel(item.type || '') }} · ¥{{ item.estimated_cost }}
                        </span>
                      </div>
                    </div>
                  </template>
                </div>
              </div>

              <!-- 景点卡片 -->
              <a-divider orientation="left">🎯 景点详情</a-divider>
              <a-list
                :data-source="day.attractions"
                :grid="{ gutter: 16, column: 2 }"
              >
                <template #renderItem="{ item, index: attrIndex }">
                  <a-list-item>
                    <a-card :title="item.name" size="small" class="attraction-card">
                      <template #extra v-if="editMode">
                        <a-space>
                          <a-button size="small" @click="moveAttraction(day.day_index, attrIndex, 'up')" :disabled="attrIndex === 0">↑</a-button>
                          <a-button size="small" @click="moveAttraction(day.day_index, attrIndex, 'down')" :disabled="attrIndex === day.attractions.length - 1">↓</a-button>
                          <a-button size="small" danger @click="deleteAttraction(day.day_index, attrIndex)">🗑️</a-button>
                        </a-space>
                      </template>

                      <div class="attraction-image-wrapper">
                        <img
                          :src="getAttractionImage(item.name, attrIndex)"
                          :alt="item.name"
                          class="attraction-image"
                          @error="handleImageError"
                        />
                        <div class="attraction-badge">
                          <span class="badge-number">{{ attrIndex + 1 }}</span>
                        </div>
                        <div v-if="item.time_start" class="time-badge">
                          🕐 {{ item.time_start }}
                        </div>
                        <div v-if="item.ticket_price" class="price-tag">
                          ¥{{ item.ticket_price }}
                        </div>
                      </div>

                      <div v-if="editMode">
                        <p><strong>开始时间:</strong></p>
                        <a-input v-model:value="item.time_start" size="small" placeholder="HH:MM" style="margin-bottom:8px" />
                        <p><strong>地址:</strong></p>
                        <a-input v-model:value="item.address" size="small" style="margin-bottom:8px" />
                        <p><strong>游览时长(分钟):</strong></p>
                        <a-input-number v-model:value="item.visit_duration" :min="10" :max="480" size="small" style="width:100%;margin-bottom:8px" />
                        <p><strong>描述:</strong></p>
                        <a-textarea v-model:value="item.description" :rows="2" size="small" style="margin-bottom:8px" />
                      </div>

                      <div v-else>
                        <p v-if="item.time_start"><strong>🕐 时间:</strong> {{ item.time_start }} 开始</p>
                        <p><strong>📍 地址:</strong> {{ item.address }}</p>
                        <p><strong>⏱ 游览:</strong> {{ item.visit_duration }}分钟</p>
                        <p><strong>📝 描述:</strong> {{ item.description }}</p>
                        <p v-if="item.rating"><strong>⭐ 评分:</strong> {{ item.rating }}</p>
                      </div>
                    </a-card>
                  </a-list-item>
                </template>
              </a-list>

              <!-- 酒店 -->
              <a-divider v-if="day.hotel" orientation="left">🏨 住宿推荐</a-divider>
              <a-card v-if="day.hotel" size="small" class="hotel-card">
                <template #title>
                  <span class="hotel-title">{{ day.hotel.name }}</span>
                </template>
                <a-descriptions :column="2" size="small">
                  <a-descriptions-item label="📍 地址">{{ day.hotel.address }}</a-descriptions-item>
                  <a-descriptions-item label="🏷 类型">{{ day.hotel.type }}</a-descriptions-item>
                  <a-descriptions-item label="💰 价格">{{ day.hotel.price_range }}</a-descriptions-item>
                  <a-descriptions-item label="⭐ 评分">{{ day.hotel.rating }}</a-descriptions-item>
                </a-descriptions>
              </a-card>

              <!-- 餐饮 -->
              <a-divider orientation="left">🍽️ 餐饮安排</a-divider>
              <div class="meals-grid">
                <a-card
                  v-for="meal in sortMeals(day.meals)"
                  :key="meal.type"
                  size="small"
                  class="meal-card"
                  :class="'meal-' + meal.type"
                >
                  <div class="meal-header">
                    <span class="meal-icon">
                      {{ meal.type === 'breakfast' ? '🌅' : meal.type === 'lunch' ? '☀️' : meal.type === 'dinner' ? '🌙' : '🍽' }}
                    </span>
                    <span class="meal-type">{{ getMealLabel(meal.type) }}</span>
                    <span v-if="meal.time_start" class="meal-time">🕐 {{ meal.time_start }}</span>
                  </div>
                  <div class="meal-name">{{ meal.name }}</div>
                  <div v-if="meal.address" class="meal-address">📍 {{ meal.address }}</div>
                  <div class="meal-footer">
                    <span v-if="meal.description" class="meal-desc">{{ meal.description }}</span>
                    <span class="meal-cost">¥{{ meal.estimated_cost || 0 }}</span>
                  </div>
                </a-card>
              </div>
            </a-collapse-panel>
          </a-collapse>
        </a-card>

        <!-- 天气 -->
        <a-card id="weather" v-if="tripPlan.weather_info?.length" title="🌤️ 天气信息" :bordered="false" style="margin-top:20px">
          <a-list :data-source="tripPlan.weather_info" :grid="{ gutter: 16, column: 3 }">
            <template #renderItem="{ item }">
              <a-list-item>
                <a-card size="small" class="weather-card">
                  <div class="weather-date">{{ item.date }}</div>
                  <div class="weather-info-row">
                    <span class="weather-icon">☀️</span>
                    <div>
                      <div class="weather-label">白天</div>
                      <div class="weather-value">{{ item.day_weather }} {{ item.day_temp }}°</div>
                    </div>
                  </div>
                  <div class="weather-info-row">
                    <span class="weather-icon">🌙</span>
                    <div>
                      <div class="weather-label">夜间</div>
                      <div class="weather-value">{{ item.night_weather }} {{ item.night_temp }}°</div>
                    </div>
                  </div>
                  <div class="weather-wind">💨 {{ item.wind_direction }} {{ item.wind_power }}</div>
                </a-card>
              </a-list-item>
            </template>
          </a-list>
        </a-card>
      </div>
    </div>

    <a-empty v-else description="没有找到旅行计划数据">
      <template #image><div style="font-size:80px">🗺️</div></template>
      <template #description><span style="color:#999">暂无旅行计划数据，请先创建行程</span></template>
      <a-button type="primary" @click="goBack">返回首页创建行程</a-button>
    </a-empty>

    <a-back-top :visibility-height="300">
      <div class="back-top-button">↑</div>
    </a-back-top>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { DownOutlined } from '@ant-design/icons-vue'
import AMapLoader from '@amap/amap-jsapi-loader'
import html2canvas from 'html2canvas'
import jsPDF from 'jspdf'
import { refinePlan, applyRefinement } from '@/services/api'
import type { TripPlan, DayPlan, Meal } from '@/types'

const router = useRouter()
const tripPlan = ref<TripPlan | null>(null)
const editMode = ref(false)
const originalPlan = ref<TripPlan | null>(null)
const attractionPhotos = ref<Record<string, string>>({})
const activeSection = ref('overview')
const activeDays = ref<number[]>([0])
let map: any = null

// --- AI 微调聊天 ---
const chatVisible = ref(false)
const chatMessage = ref('')
const chatLoading = ref(false)
interface ChatMessage {
  role: 'user' | 'ai'
  content: string
  changes?: string[]
  pending?: boolean      // 等待用户操作
  applying?: boolean     // 正在执行修改
  options?: string[]     // AI 给出的多个方案选项
  selectedOption?: number // 用户选择的方案索引
}

const chatMessages = ref<ChatMessage[]>([])
const currentPlanId = ref(sessionStorage.getItem('currentPlanId') || '')
const chatBodyRef = ref<HTMLElement | null>(null)

onMounted(async () => {
  const data = sessionStorage.getItem('tripPlan')
  if (data) {
    tripPlan.value = JSON.parse(data)
    await loadAttractionPhotos()
    await nextTick()
    initMap()
  }
})

const goBack = () => router.push('/')

const scrollToSection = ({ key }: { key: string }) => {
  activeSection.value = key
  const element = document.getElementById(key)
  if (element) element.scrollIntoView({ behavior: 'smooth', block: 'start' })
}

// --- 编辑模式 ---
const toggleEditMode = () => {
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info('进入编辑模式')
}
const saveChanges = () => {
  editMode.value = false
  if (tripPlan.value) sessionStorage.setItem('tripPlan', JSON.stringify(tripPlan.value))
  message.success('修改已保存')
  if (map) { map.destroy(); map = null }
  nextTick(() => initMap())
}
const cancelEdit = () => {
  if (originalPlan.value) tripPlan.value = JSON.parse(JSON.stringify(originalPlan.value))
  editMode.value = false
  message.info('已取消编辑')
}
const deleteAttraction = (dayIndex: number, attrIndex: number) => {
  if (!tripPlan.value) return
  const day = tripPlan.value.days[dayIndex]
  if (day.attractions.length <= 1) { message.warning('每天至少需要保留一个景点'); return }
  day.attractions.splice(attrIndex, 1)
  message.success('景点已删除')
}
const moveAttraction = (dayIndex: number, attrIndex: number, direction: 'up' | 'down') => {
  if (!tripPlan.value) return
  const attractions = tripPlan.value.days[dayIndex].attractions
  if (direction === 'up' && attrIndex > 0) {
    [attractions[attrIndex], attractions[attrIndex - 1]] = [attractions[attrIndex - 1], attractions[attrIndex]]
  } else if (direction === 'down' && attrIndex < attractions.length - 1) {
    [attractions[attrIndex], attractions[attrIndex + 1]] = [attractions[attrIndex + 1], attractions[attrIndex]]
  }
}

// --- 时间线 ---
interface TimelineItem {
  key: string
  kind: 'attraction' | 'meal' | 'transport'
  time: string
  name: string
  address?: string
  visit_duration?: number
  ticket_price?: number
  type?: string
  estimated_cost?: number
  icon?: string   // 交通方式图标
  from?: string   // 出发地
  to?: string     // 目的地
}

const TRANSPORT_ICONS: Record<string, string> = {
  '步行': '🚶', '自驾': '🚗', '开车': '🚗', '出租车': '🚕', '打车': '🚕', '网约车': '🚕',
  '公交': '🚌', '公交车': '🚌', '公共交通': '🚌', '地铁': '🚇', '轻轨': '🚈',
  '骑行': '🚲', '单车': '🚲', '共享单车': '🚲', '火车': '🚆', '高铁': '🚄',
}

/** 根据交通方式文本推断图标 */
const getTransportIcon = (transportText: string): string => {
  for (const [key, icon] of Object.entries(TRANSPORT_ICONS)) {
    if (transportText.includes(key)) return icon
  }
  return '🚶' // 默认步行
}

const getDayTimeline = (day: DayPlan): TimelineItem[] => {
  const items: TimelineItem[] = []
  day.attractions.forEach((a, i) => {
    items.push({
      key: `attr-${i}`, kind: 'attraction',
      time: a.time_start || '--:--', name: a.name,
      address: a.address, visit_duration: a.visit_duration,
      ticket_price: a.ticket_price || 0
    })
  })
  day.meals.forEach((m, i) => {
    items.push({
      key: `meal-${i}`, kind: 'meal',
      time: m.time_start || '--:--', name: m.name,
      type: m.type, estimated_cost: m.estimated_cost || 0
    })
  })
  items.sort((a, b) => a.time.localeCompare(b.time))

  // 在相邻项之间插入交通连接
  const withTransport: TimelineItem[] = []
  for (let i = 0; i < items.length; i++) {
    withTransport.push(items[i])
    if (i < items.length - 1) {
      const prev = items[i]
      const next = items[i + 1]
      withTransport.push({
        key: `transport-${i}`,
        kind: 'transport',
        time: '',
        name: day.transportation || '步行',
        icon: getTransportIcon(day.transportation || '步行'),
        from: prev.name,
        to: next.name,
      })
    }
  }

  return withTransport
}

const sortMeals = (meals: Meal[]): Meal[] => {
  const order: Record<string, number> = { breakfast: 0, lunch: 1, dinner: 2, snack: 3 }
  return [...meals].sort((a, b) => {
    if (a.time_start && b.time_start) return a.time_start.localeCompare(b.time_start)
    return (order[a.type] ?? 99) - (order[b.type] ?? 99)
  })
}

const getMealLabel = (type: string): string => {
  const labels: Record<string, string> = { breakfast: '早餐', lunch: '午餐', dinner: '晚餐', snack: '小吃' }
  return labels[type] || type
}

// --- AI 微调 ---

/** 解析 AI 回复中的多个方案选项 */
const parseOptions = (text: string): string[] => {
  const options: string[] = []

  // 匹配 ① ② ③ 等 Unicode 圆圈数字
  const circled = text.match(/[①-⑳]\s*.+?(?=[①-⑳]|需要我帮你|$)/gs)
  if (circled && circled.length >= 2) {
    return circled.map(o => o.replace(/^[①-⑳]\s*/, '').trim()).filter(o => o.length > 0)
  }

  // 匹配 "方案1/方案一" 开头的行
  const fangan = text.match(/(?:方案|方向|建议|选项)\s*[一二三四五六1-6][、.\s]*[^\n]+/g)
  if (fangan && fangan.length >= 2) {
    return fangan.map(o => o.trim()).filter(o => o.length > 0)
  }

  // 匹配编号列表行 "1. xxx" "2. xxx"
  const numbered = text.match(/^[1-6][.)、]\s*.+$/gm)
  if (numbered && numbered.length >= 2) {
    return numbered.map(o => o.replace(/^[1-6][.)、]\s*/, '').trim()).filter(o => o.length > 0)
  }

  return options
}

const handleChatSend = async () => {
  const msg = chatMessage.value.trim()
  if (!msg || chatLoading.value) return

  if (!currentPlanId.value) {
    message.warning('未找到 plan_id，请重新生成计划')
    return
  }

  chatMessages.value.push({ role: 'user', content: msg })
  chatMessage.value = ''
  chatLoading.value = true

  try {
    const result = await refinePlan(currentPlanId.value, msg)
    const reply = result.reply || '收到，我来看看你的计划...'
    const options = parseOptions(reply)

    chatMessages.value.push({
      role: 'ai',
      content: reply,
      changes: result.changes || [],
      options: options.length >= 2 ? options : undefined,
      pending: true
    })
  } catch (error: any) {
    chatMessages.value.push({
      role: 'ai',
      content: `❌ 请求失败: ${error.message || '未知错误'}`
    })
  } finally {
    chatLoading.value = false
    nextTick(() => {
      if (chatBodyRef.value) chatBodyRef.value.scrollTop = chatBodyRef.value.scrollHeight
    })
  }
}

// "帮我改" — 调用完整修改（FunctionCallAgent + 高德工具）
const handleApplyChanges = async (msgIndex: number) => {
  if (!currentPlanId.value) {
    message.warning('未找到 plan_id')
    return
  }

  const aiMsg = chatMessages.value[msgIndex]
  if (!aiMsg || aiMsg.applying) return

  // 构建发送给后端的消息：原始请求 + 选中的方案
  const userMsg = chatMessages.value.slice(0, msgIndex).reverse().find(m => m.role === 'user')
  if (!userMsg) { message.warning('找不到原始请求'); return }

  let refineMsg = userMsg.content
  if (aiMsg.options && aiMsg.selectedOption !== undefined) {
    const selected = aiMsg.options[aiMsg.selectedOption]
    refineMsg = `${userMsg.content}\n（用户选择了方案: ${selected}）`
  }

  // 进入 applying 状态（不隐藏按钮区，显示加载动画）
  aiMsg.applying = true

  try {
    const result = await applyRefinement(currentPlanId.value, refineMsg)

    // 更新为完成状态
    aiMsg.content = result.reply || '修改完成'
    aiMsg.changes = result.changes || []
    aiMsg.pending = false
    aiMsg.applying = false
    aiMsg.options = undefined

    // 应用修改后计划
    if (result.modified_plan) {
      tripPlan.value = result.modified_plan as unknown as TripPlan
      sessionStorage.setItem('tripPlan', JSON.stringify(result.modified_plan))

      if (map) { map.destroy(); map = null }
      await nextTick()
      initMap()
      message.success('✅ 计划已更新')
    } else {
      message.info('AI 已回复，但未返回完整计划修改')
    }
  } catch (error: any) {
    aiMsg.pending = false
    aiMsg.applying = false
    aiMsg.content = `❌ 修改失败: ${error.message || '未知错误'}，请重试`
    message.error('修改失败，请重试')
  }
}

// "自己编辑" — 进入编辑模式
const handleEditMyself = () => {
  // 关闭聊天面板
  chatVisible.value = false
  // 进入编辑模式
  editMode.value = true
  originalPlan.value = JSON.parse(JSON.stringify(tripPlan.value))
  message.info('已进入编辑模式，你可以自由修改行程')
}

// --- 景点图片 ---
const loadAttractionPhotos = async () => {
  if (!tripPlan.value) return
  const promises = tripPlan.value.days.flatMap(day =>
    day.attractions.map(attr =>
      fetch(`http://localhost:8000/api/poi/photo?name=${encodeURIComponent(attr.name)}`)
        .then(res => res.json())
        .then(data => { if (data.success && data.data.photo_url) attractionPhotos.value[attr.name] = data.data.photo_url })
        .catch(err => console.error(`获取${attr.name}图片失败:`, err))
    )
  )
  await Promise.all(promises)
}

const getAttractionImage = (name: string, index: number): string => {
  if (attractionPhotos.value[name]) return attractionPhotos.value[name]

  const colors = [
    { start: '#667eea', end: '#764ba2' },
    { start: '#f093fb', end: '#f5576c' },
    { start: '#4facfe', end: '#00f2fe' },
    { start: '#43e97b', end: '#38f9d7' },
    { start: '#fa709a', end: '#fee140' }
  ]
  const { start, end } = colors[index % colors.length]
  const svg = `<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240">
    <defs><linearGradient id="g${index}" x1="0%" y1="0%" x2="100%" y2="100%">
      <stop offset="0%" style="stop-color:${start};stop-opacity:1" />
      <stop offset="100%" style="stop-color:${end};stop-opacity:1" />
    </linearGradient></defs>
    <rect width="400" height="240" fill="url(#g${index})"/>
    <text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle"
          font-family="system-ui,sans-serif" font-size="22" font-weight="bold" fill="white">${name}</text>
  </svg>`
  // 使用 TextEncoder 替代废弃的 unescape
  const bytes = new TextEncoder().encode(svg)
  const binary = Array.from(bytes).map(b => String.fromCharCode(b)).join('')
  return `data:image/svg+xml;base64,${btoa(binary)}`
}

const handleImageError = (event: Event) => {
  (event.target as HTMLImageElement).src = 'data:image/svg+xml,' + encodeURIComponent(
    '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="240"><rect width="400" height="240" fill="#f0f0f0"/><text x="50%" y="50%" dominant-baseline="middle" text-anchor="middle" font-family="sans-serif" font-size="16" fill="#999">图片加载失败</text></svg>'
  )
}

// --- 地图 ---
const initMap = async () => {
  if (!tripPlan.value) return
  try {
    const AMap = await AMapLoader.load({
      key: import.meta.env.VITE_AMAP_WEB_JS_KEY,
      version: '2.0',
      plugins: ['AMap.Marker', 'AMap.Polyline', 'AMap.InfoWindow']
    })

    // 动态计算地图中心：使用第一个有坐标的景点位置
    let center: [number, number] = [116.397128, 39.916527] // 默认北京
    for (const day of tripPlan.value.days) {
      for (const attr of day.attractions) {
        if (attr.location?.longitude && attr.location?.latitude) {
          center = [attr.location.longitude, attr.location.latitude]
          break
        }
      }
      if (center[0] !== 116.397128) break
    }

    map = new AMap.Map('amap-container', {
      zoom: 12,
      center,
      viewMode: '3D'
    })

    addAttractionMarkers(AMap)
  } catch (error) {
    console.error('地图加载失败:', error)
  }
}

const addAttractionMarkers = (AMap: any) => {
  if (!tripPlan.value) return

  const markers: any[] = []
  const allAttractions: any[] = []

  tripPlan.value.days.forEach((day, dayIndex) => {
    day.attractions.forEach((attr, attrIndex) => {
      if (attr.location?.longitude && attr.location?.latitude) {
        allAttractions.push({ ...attr, dayIndex, attrIndex })
      }
    })
  })

  allAttractions.forEach((attr, index) => {
    const marker = new AMap.Marker({
      position: [attr.location.longitude, attr.location.latitude],
      title: attr.name,
      label: {
        content: `<div style="background:#4CAF50;color:white;padding:4px 8px;border-radius:4px;font-size:12px;font-weight:bold">${index + 1}</div>`,
        offset: new AMap.Pixel(0, -30)
      }
    })

    const infoWindow = new AMap.InfoWindow({
      content: `
        <div style="padding:10px;min-width:200px">
          <h4 style="margin:0 0 8px;color:#333">${attr.name}</h4>
          <p style="margin:4px 0;font-size:13px">📍 ${attr.address}</p>
          <p style="margin:4px 0;font-size:13px">⏱ ${attr.visit_duration}分钟 | ¥${attr.ticket_price || 0}</p>
          ${attr.time_start ? `<p style="margin:4px 0;font-size:13px">🕐 ${attr.time_start} 开始</p>` : ''}
          <p style="margin:4px 0;color:#667eea;font-size:12px">第${attr.dayIndex + 1}天 · 景点${attr.attrIndex + 1}</p>
        </div>`,
      offset: new AMap.Pixel(0, -30)
    })

    marker.on('click', () => infoWindow.open(map, marker.getPosition()))
    markers.push(marker)
  })

  map.add(markers)

  if (allAttractions.length > 0) {
    map.setFitView(markers)
  }

  // 路线
  drawRoutes(AMap, allAttractions)
}

const drawRoutes = (AMap: any, attractions: any[]) => {
  if (attractions.length < 2) return
  const dayGroups: Record<number, any[]> = {}
  attractions.forEach(attr => {
    if (!dayGroups[attr.dayIndex]) dayGroups[attr.dayIndex] = []
    dayGroups[attr.dayIndex].push(attr)
  })
  Object.values(dayGroups).forEach((dayAttrs: any[]) => {
    if (dayAttrs.length < 2) return
    const path = dayAttrs.map((a: any) => [a.location.longitude, a.location.latitude])
    map.add(new AMap.Polyline({
      path, strokeColor: '#1890ff', strokeWeight: 4,
      strokeOpacity: 0.8, strokeStyle: 'solid', showDir: true
    }))
  })
}

// --- 导出（保持原有逻辑，微调样式） ---
const prepareExportContainer = (element: HTMLElement): HTMLElement => {
  const container = document.createElement('div')
  container.style.cssText = `width:${element.offsetWidth}px;background:#f5f7fa;padding:20px;position:absolute;left:-9999px`
  container.innerHTML = element.innerHTML

  const mapContainer = document.getElementById('amap-container')
  if (mapContainer && map) {
    const canvas = mapContainer.querySelector('canvas')
    if (canvas) {
      const exportMap = container.querySelector('#amap-container')
      if (exportMap) exportMap.innerHTML = `<img src="${canvas.toDataURL('image/png')}" style="width:100%;height:100%;object-fit:cover" />`
    }
  }

  container.querySelectorAll('.ant-card').forEach(c => {
    const el = c as HTMLElement
    el.className = ''
    el.style.cssText = 'background:#fff;border-radius:12px;box-shadow:0 4px 12px rgba(0,0,0,.1);margin-bottom:20px;overflow:hidden'
  })
  container.querySelectorAll('.ant-card-head').forEach(h => {
    (h as HTMLElement).style.cssText = 'background:linear-gradient(135deg,#667eea,#764ba2);color:#fff;padding:16px 24px;font-size:18px;font-weight:600'
  })
  return container
}

const exportAsImage = async () => {
  try {
    message.loading({ content: '正在生成图片...', key: 'export', duration: 0 })
    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) throw new Error('未找到内容元素')

    const container = prepareExportContainer(element)
    document.body.appendChild(container)

    const canvas = await html2canvas(container, { backgroundColor: '#f5f7fa', scale: 2, logging: false, useCORS: true, allowTaint: true })
    document.body.removeChild(container)

    const link = document.createElement('a')
    link.download = `旅行计划_${tripPlan.value?.city}_${Date.now()}.png`
    link.href = canvas.toDataURL('image/png')
    link.click()
    message.success({ content: '图片导出成功!', key: 'export' })
  } catch (error: any) {
    message.error({ content: `导出失败: ${error.message}`, key: 'export' })
  }
}

const exportAsPDF = async () => {
  try {
    message.loading({ content: '正在生成PDF...', key: 'export', duration: 0 })
    const element = document.querySelector('.main-content') as HTMLElement
    if (!element) throw new Error('未找到内容元素')

    const container = prepareExportContainer(element)
    document.body.appendChild(container)

    const canvas = await html2canvas(container, { backgroundColor: '#f5f7fa', scale: 2, logging: false, useCORS: true, allowTaint: true })
    document.body.removeChild(container)

    const pdf = new jsPDF({ orientation: 'portrait', unit: 'mm', format: 'a4' })
    const imgWidth = 210
    const imgHeight = (canvas.height * imgWidth) / canvas.width
    let heightLeft = imgHeight
    pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, 0, imgWidth, imgHeight)
    heightLeft -= 297
    while (heightLeft > 0) {
      pdf.addPage()
      pdf.addImage(canvas.toDataURL('image/png'), 'PNG', 0, heightLeft - imgHeight, imgWidth, imgHeight)
      heightLeft -= 297
    }
    pdf.save(`旅行计划_${tripPlan.value?.city}_${Date.now()}.pdf`)
    message.success({ content: 'PDF导出成功!', key: 'export' })
  } catch (error: any) {
    message.error({ content: `导出失败: ${error.message}`, key: 'export' })
  }
}
</script>

<style scoped>
.result-container {
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
  padding: 40px 20px;
}

.page-header {
  max-width: 1300px;
  margin: 0 auto 30px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  animation: fadeInDown 0.6s ease-out;
}

.back-button { border-radius: 8px; font-weight: 500; }

.content-wrapper {
  max-width: 1300px;
  margin: 0 auto;
  display: flex;
  gap: 24px;
}

.side-nav { width: 220px; flex-shrink: 0; }
.side-nav :deep(.ant-menu) { border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,.08); background: white; }
.side-nav :deep(.ant-menu-item) { margin: 4px 8px; border-radius: 8px; transition: all 0.3s ease; }
.side-nav :deep(.ant-menu-item-selected) { background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; }
.side-nav :deep(.ant-menu-item:hover) { background: rgba(102,126,234,.1); }

.main-content { flex: 1; min-width: 0; }

/* 顶部布局 */
.top-info-section { display: flex; gap: 20px; margin-bottom: 20px; }
.left-info { flex: 0 0 380px; display: flex; flex-direction: column; gap: 20px; }
.right-map { flex: 1; }

.overview-card { height: fit-content; }
.overview-content { display: flex; flex-direction: column; gap: 12px; }
.info-item { display: flex; flex-direction: column; gap: 4px; }
.info-label { font-size: 14px; font-weight: 600; color: #666; }
.info-value { font-size: 15px; color: #333; line-height: 1.6; }

/* 预算 */
.budget-card { height: fit-content; }
.budget-grid { display: grid; grid-template-columns: 1fr 1fr; gap: 12px; margin-bottom: 16px; }
.budget-item { text-align: center; padding: 14px 8px; background: linear-gradient(135deg,#f5f7fa,#fff); border-radius: 10px; border: 1px solid #e8e8e8; }
.budget-icon { font-size: 22px; margin-bottom: 4px; }
.budget-label { font-size: 12px; color: #666; margin-bottom: 4px; }
.budget-value { font-size: 18px; font-weight: 700; color: #1890ff; }
.budget-total { display: flex; justify-content: space-between; align-items: center; padding: 16px; background: linear-gradient(135deg,#667eea,#764ba2); border-radius: 10px; color: white; }
.total-label { font-size: 16px; font-weight: 600; }
.total-value { font-size: 26px; font-weight: 700; }

/* 地图 */
.map-card { height: 100%; min-height: 460px; }
.map-card :deep(.ant-card-body) { height: calc(100% - 57px); padding: 0; }

/* 每日行程 */
.days-card { margin-top: 20px; }
.day-header { display: flex; align-items: center; width: 100%; }
.day-title { font-size: 18px; font-weight: 600; color: #333; margin-right: 12px; }
.day-date { font-size: 14px; color: #999; }
.day-info { margin-bottom: 20px; padding: 16px; background: linear-gradient(135deg,#f5f7fa,#fff); border-radius: 8px; border: 1px solid #e8e8e8; }
.info-row { display: flex; gap: 12px; margin-bottom: 8px; }
.info-row:last-child { margin-bottom: 0; }
.info-row .label { font-weight: 600; color: #666; min-width: 90px; }
.info-row .value { color: #333; flex: 1; }

/* ===== 时间线 ===== */
.timeline { position: relative; padding-left: 12px; }
.timeline::before {
  content: '';
  position: absolute;
  left: 56px;
  top: 0;
  bottom: 0;
  width: 3px;
  background: linear-gradient(180deg, #667eea 0%, #764ba2 100%);
  border-radius: 2px;
}
.timeline-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;
  margin-bottom: 20px;
  position: relative;
}
.timeline-time {
  width: 44px;
  text-align: right;
  font-size: 13px;
  font-weight: 700;
  color: #667eea;
  padding-top: 6px;
  flex-shrink: 0;
}
.timeline-dot {
  width: 36px;
  height: 36px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
  z-index: 1;
}
.is-attraction .timeline-dot { background: linear-gradient(135deg,#e3f2fd,#bbdefb); border: 3px solid #1976d2; }
.is-meal .timeline-dot { background: linear-gradient(135deg,#fff3e0,#ffe0b2); border: 3px solid #f57c00; }

/* 交通连接线 */
.is-transport { margin-bottom: 8px; }
.transport-dot {
  width: 28px !important;
  height: 28px !important;
  background: linear-gradient(135deg,#f5f5f5,#e8e8e8) !important;
  border: 2px dashed #bbb !important;
  font-size: 13px !important;
}
.transport-content {
  background: transparent !important;
  border: 1px dashed #d9d9d9 !important;
  padding: 6px 14px !important;
  border-radius: 8px !important;
}
.transport-label {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  flex-wrap: wrap;
}
.transport-icon { font-size: 16px; }
.transport-text {
  font-weight: 500;
  color: #555;
  max-width: 100px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}
.transport-arrow {
  color: #667eea;
  font-weight: 700;
  font-size: 14px;
}
.transport-mode {
  font-size: 11px;
  color: #999;
  margin-top: 2px;
}
.timeline-content {
  flex: 1;
  background: white;
  padding: 10px 16px;
  border-radius: 10px;
  border: 1px solid #e8e8e8;
  min-width: 0;
}
.timeline-title { font-size: 15px; font-weight: 600; color: #333; margin-bottom: 2px; }
.timeline-meta { font-size: 12px; color: #888; }

/* 景点卡片 */
.attraction-image-wrapper { position: relative; margin-bottom: 12px; border-radius: 8px; overflow: hidden; }
.attraction-image { width: 100%; height: 200px; object-fit: cover; transition: transform 0.3s ease; }
.attraction-image-wrapper:hover .attraction-image { transform: scale(1.05); }
.attraction-badge {
  position: absolute; top: 12px; left: 12px;
  background: linear-gradient(135deg,#667eea,#764ba2); color: white;
  width: 32px; height: 32px; border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
  font-weight: bold; box-shadow: 0 2px 8px rgba(0,0,0,.2);
}
.time-badge {
  position: absolute; top: 12px; left: 52px;
  background: rgba(25,118,210,.9); color: white;
  padding: 2px 10px; border-radius: 10px;
  font-size: 12px; font-weight: 600; z-index: 1;
}
.price-tag {
  position: absolute; top: 12px; right: 12px;
  background: rgba(255,77,79,.9); color: white;
  padding: 4px 12px; border-radius: 12px;
  font-weight: bold; font-size: 14px; box-shadow: 0 2px 8px rgba(0,0,0,.2);
}
.badge-number { font-size: 16px; }

/* 餐饮卡片 */
.meals-grid { display: flex; flex-direction: column; gap: 10px; }
.meal-card { border-radius: 10px; border: none !important; transition: all 0.3s ease; }
.meal-card:hover { transform: translateX(4px); }
.meal-breakfast { background: linear-gradient(135deg,#fff8e1,#ffecb3) !important; }
.meal-lunch { background: linear-gradient(135deg,#e8f5e9,#c8e6c9) !important; }
.meal-dinner { background: linear-gradient(135deg,#e3f2fd,#bbdefb) !important; }
.meal-header { display: flex; align-items: center; gap: 8px; margin-bottom: 6px; }
.meal-icon { font-size: 18px; }
.meal-type { font-size: 13px; font-weight: 600; color: #555; }
.meal-time { font-size: 12px; color: #888; margin-left: auto; }
.meal-name { font-size: 16px; font-weight: 600; color: #333; }
.meal-address { font-size: 12px; color: #888; margin-top: 2px; }
.meal-footer { display: flex; justify-content: space-between; align-items: center; margin-top: 6px; }
.meal-desc { font-size: 12px; color: #999; }
.meal-cost { font-size: 15px; font-weight: 700; color: #f57c00; }

/* 酒店 */
.hotel-card { background: linear-gradient(135deg,#e3f2fd,#bbdefb) !important; border: none !important; }
.hotel-card :deep(.ant-card-head) { background: linear-gradient(135deg,#1976d2,#1565c0); }
.hotel-title { color: white !important; font-weight: 600; }

/* 天气 */
.weather-card { background: linear-gradient(135deg,#e0f7fa,#b2ebf2); border: none !important; transition: all .3s ease; }
.weather-card:hover { transform: translateY(-4px); box-shadow: 0 8px 16px rgba(0,0,0,.15); }
.weather-date { font-size: 16px; font-weight: bold; color: #00796b; margin-bottom: 12px; text-align: center; }
.weather-info-row { display: flex; align-items: center; gap: 12px; margin-bottom: 8px; }
.weather-icon { font-size: 24px; }
.weather-label { font-size: 12px; color: #666; }
.weather-value { font-size: 16px; font-weight: 600; color: #00796b; }
.weather-wind { margin-top: 8px; padding-top: 8px; border-top: 1px solid rgba(0,121,107,.2); text-align: center; color: #00796b; font-size: 14px; }

.back-top-button {
  width: 48px; height: 48px; background: linear-gradient(135deg,#667eea,#764ba2); color: white;
  border-radius: 50%; display: flex; align-items: center; justify-content: center;
  font-size: 22px; font-weight: bold; box-shadow: 0 4px 12px rgba(0,0,0,.3);
  cursor: pointer; transition: all .3s ease;
}
.back-top-button:hover { transform: scale(1.1); box-shadow: 0 6px 16px rgba(0,0,0,.4); }

/* 全局卡片 */
:deep(.ant-card) { border-radius: 12px; box-shadow: 0 4px 12px rgba(0,0,0,.08); margin-bottom: 20px; animation: fadeInUp .6s ease-out; }
:deep(.ant-card-head) { background: linear-gradient(135deg,#667eea,#764ba2); color: white !important; border-radius: 12px 12px 0 0; font-weight: 600; }
:deep(.ant-card-head-title) { color: white !important; font-size: 17px; }
:deep(.ant-collapse) { border: none; background: transparent; }
:deep(.ant-collapse-item) { margin-bottom: 16px; border: 1px solid #e8e8e8; border-radius: 12px; overflow: hidden; }
:deep(.ant-collapse-header) { background: linear-gradient(135deg,#f5f7fa,#fff); padding: 16px 20px !important; font-weight: 600; }
:deep(.ant-collapse-content-box) { padding: 20px; }

/* ===== AI 微调聊天面板 ===== */
.chat-panel {
  max-width: 1300px;
  margin: 0 auto 24px;
  animation: fadeInDown 0.4s ease-out;
}
.chat-card {
  border: 2px solid #667eea !important;
  box-shadow: 0 8px 24px rgba(102,126,234,.15) !important;
}
.chat-card :deep(.ant-card-head) {
  background: linear-gradient(135deg,#667eea,#764ba2) !important;
  border-radius: 12px 12px 0 0 !important;
}
.chat-warning {
  text-align: center;
  padding: 20px;
  color: #ff7a45;
  font-size: 14px;
  background: #fff7e6;
  border-radius: 8px;
  margin-bottom: 12px;
}
.chat-body {
  max-height: 360px;
  overflow-y: auto;
  padding: 8px 4px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}
.chat-body::-webkit-scrollbar { width: 6px; }
.chat-body::-webkit-scrollbar-track { background: transparent; }
.chat-body::-webkit-scrollbar-thumb { background: #d9d9d9; border-radius: 3px; }
.chat-body::-webkit-scrollbar-thumb:hover { background: #bfbfbf; }

.chat-hint {
  font-size: 13px;
  color: #999;
  line-height: 2;
  padding: 12px 16px;
  background: #fafafa;
  border-radius: 10px;
  border: 1px dashed #e8e8e8;
}
.chat-msg {
  display: flex;
  animation: fadeInUp 0.3s ease-out;
}
.msg-user { justify-content: flex-end; }
.msg-ai { justify-content: flex-start; }

.msg-bubble {
  max-width: 80%;
  padding: 10px 16px;
  border-radius: 14px;
  font-size: 14px;
  line-height: 1.6;
}
.msg-user .msg-bubble {
  background: linear-gradient(135deg,#667eea,#764ba2);
  color: white;
  border-bottom-right-radius: 4px;
}
.msg-ai .msg-bubble {
  background: white;
  color: #333;
  border: 1px solid #e8e8e8;
  border-bottom-left-radius: 4px;
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}
.msg-text { white-space: pre-wrap; word-break: break-word; }
.msg-changes { margin-top: 8px; display: flex; flex-wrap: wrap; gap: 4px; }
.msg-actions {
  margin-top: 10px;
  display: flex;
  align-items: center;
  gap: 8px;
}
.applying-text {
  font-size: 13px;
  color: #667eea;
}

/* 方案选择器 */
.msg-options {
  margin-top: 10px;
  padding: 8px;
  background: #f6f8ff;
  border-radius: 8px;
  border: 1px solid #e0e5ff;
}
.options-label {
  font-size: 12px;
  color: #888;
  margin-bottom: 6px;
}
.options-list {
  display: flex;
  flex-wrap: wrap;
  gap: 6px;
}
.option-tag {
  cursor: pointer;
  transition: all 0.2s;
  font-size: 13px;
  padding: 4px 10px;
  border-radius: 6px;
}
.option-tag:hover {
  transform: translateY(-1px);
  box-shadow: 0 2px 6px rgba(102,126,234,.3);
}

.chat-loading {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 8px 16px;
  font-size: 13px;
  color: #999;
}
.chat-input {
  display: flex;
  gap: 10px;
  align-items: flex-end;
  margin-top: 12px;
  padding-top: 12px;
  border-top: 1px solid #f0f0f0;
}
.chat-input :deep(.ant-input) { border-radius: 10px; resize: none; }
.chat-send-btn {
  flex-shrink: 0;
  width: 40px;
  height: 40px;
  border-radius: 50% !important;
  display: flex !important;
  align-items: center;
  justify-content: center;
  font-size: 18px;
}
.chat-toggle-btn {
  background: linear-gradient(135deg,#667eea,#764ba2) !important;
  color: white !important;
  border: none !important;
  font-weight: 600;
  transition: all 0.3s ease;
}
.chat-toggle-btn:hover {
  transform: translateY(-2px);
  box-shadow: 0 6px 16px rgba(102,126,234,.4) !important;
}

@keyframes fadeInDown {
  from { opacity: 0; transform: translateY(-20px); }
  to { opacity: 1; transform: translateY(0); }
}
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

@media (max-width: 768px) {
  .result-container { padding: 20px 10px; }
  .page-header { flex-direction: column; gap: 16px; }
  .content-wrapper { flex-direction: column; }
  .side-nav { width: 100%; }
  .top-info-section { flex-direction: column; }
  .left-info { flex: 1; }
}
</style>
