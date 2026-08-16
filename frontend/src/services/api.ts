import axios from 'axios'
import type {
  TripFormData, TripPlanResponse, UserProfile,
  PlanHistoryResponse, RefineRequest, RefineResponse
} from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000'

const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 360000, // 6分钟超时（后端 Planner 可能需要120s+）
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    console.log('发送请求:', config.method?.toUpperCase(), config.url)
    return config
  },
  (error) => {
    console.error('请求错误:', error)
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => {
    console.log('收到响应:', response.status, response.config.url)
    return response
  },
  (error) => {
    console.error('响应错误:', error.response?.status, error.message)
    return Promise.reject(error)
  }
)

/**
 * 生成旅行计划（同步）
 */
export async function generateTripPlan(formData: TripFormData): Promise<TripPlanResponse> {
  try {
    const response = await apiClient.post<TripPlanResponse>('/api/trip/plan', formData)
    return response.data
  } catch (error: any) {
    console.error('生成旅行计划失败:', error)
    throw new Error(error.response?.data?.detail || error.message || '生成旅行计划失败')
  }
}

/**
 * SSE 流式生成旅行计划
 *
 * 事件类型:
 * - query_start: 开始并行查询景点/天气/酒店/餐厅
 * - query_complete: 外部查询完成，开始清洗数据
 * - planning_start: AI 规划行程中
 * - plan_complete: 规划完成，携带完整 TripPlan
 * - error: 发生错误
 *
 * @param formData 旅行请求
 * @param onEvent 事件回调（eventType, data）
 * @param onError 错误回调
 * @returns Promise<void>
 */
export async function generateTripPlanStream(
  formData: TripFormData,
  onEvent: (eventType: string, data: any) => void,
  onError: (error: string) => void
): Promise<void> {
  try {
    const response = await fetch(`${API_BASE_URL}/api/trip/plan/stream`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(formData)
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    const reader = response.body?.getReader()
    if (!reader) {
      throw new Error('Response body 不可读')
    }

    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
      const { done, value } = await reader.read()
      if (done) break

      buffer += decoder.decode(value, { stream: true })

      // 解析 SSE 事件（格式: "event: xxx\ndata: {...}\n\n"）
      const lines = buffer.split('\n\n')
      buffer = lines.pop() || '' // 保留未完成的部分

      for (const chunk of lines) {
        if (!chunk.trim()) continue

        let eventType = ''
        let dataStr = ''

        for (const line of chunk.split('\n')) {
          if (line.startsWith('event: ')) {
            eventType = line.slice(7).trim()
          } else if (line.startsWith('data: ')) {
            dataStr = line.slice(6).trim()
          }
        }

        if (eventType && dataStr) {
          try {
            const data = JSON.parse(dataStr)
            if (eventType === 'error') {
              onError(data.message || '未知错误')
              return
            }
            onEvent(eventType, data)
          } catch {
            console.warn('SSE 解析失败:', chunk)
          }
        }
      }
    }
  } catch (error: any) {
    onError(error.message || 'SSE 连接失败')
  }
}

/**
 * 获取用户偏好
 */
export async function getUserProfile(userId: string): Promise<UserProfile | null> {
  try {
    const response = await apiClient.get(`/api/user/profile/${userId}`)
    return response.data
  } catch {
    return null
  }
}

/**
 * 健康检查
 */
export async function healthCheck(): Promise<any> {
  try {
    const response = await apiClient.get('/health')
    return response.data
  } catch (error: any) {
    console.error('健康检查失败:', error)
    throw new Error(error.message || '健康检查失败')
  }
}

/**
 * 获取用户历史计划列表
 */
export async function getPlanHistory(userId: string): Promise<PlanHistoryResponse> {
  const response = await apiClient.get<PlanHistoryResponse>('/api/trip/plans', {
    params: { user_id: userId }
  })
  return response.data
}

/**
 * AI 微调建议（快速 — 仅建议，不修改计划）
 */
export async function refinePlan(
  planId: string,
  message: string,
  userId?: string
): Promise<RefineResponse> {
  const request: RefineRequest = { plan_id: planId, message, user_id: userId }
  const response = await apiClient.post<RefineResponse>(
    `/api/trip/plan/${planId}/refine`,
    request
  )
  return response.data
}

/**
 * 应用微调修改（完整 — 调用高德工具 + 修改计划）
 */
export async function applyRefinement(
  planId: string,
  message: string,
  userId?: string
): Promise<RefineResponse> {
  const request: RefineRequest = { plan_id: planId, message, user_id: userId }
  const response = await apiClient.post<RefineResponse>(
    `/api/trip/plan/${planId}/apply`,
    request
  )
  return response.data
}

export default apiClient
