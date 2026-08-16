// 类型定义（与后端 schemas.py 严格对齐）

export interface Location {
  longitude: number
  latitude: number
}

export interface Attraction {
  name: string
  address: string
  location: Location
  visit_duration: number
  description: string
  category?: string
  rating?: number
  time_start?: string    // 🆕 开始时间 HH:MM（后端 I3 产出）
  photos?: string[]       // 🆕 景点图片URL列表
  poi_id?: string         // 🆕 高德POI ID
  image_url?: string
  ticket_price?: number
}

export interface Meal {
  type: 'breakfast' | 'lunch' | 'dinner' | 'snack'
  name: string
  address?: string
  location?: Location
  description?: string
  time_start?: string     // 🆕 用餐时间 HH:MM
  estimated_cost?: number
}

export interface Hotel {
  name: string
  address: string
  location?: Location
  price_range: string
  rating: string
  distance: string
  type: string
  estimated_cost?: number
}

export interface Budget {
  total_attractions: number
  total_hotels: number
  total_meals: number
  total_transportation: number
  total: number
}

export interface DayPlan {
  date: string
  day_index: number
  description: string
  transportation: string
  accommodation: string
  hotel?: Hotel
  attractions: Attraction[]
  meals: Meal[]
}

export interface WeatherInfo {
  date: string
  day_weather: string
  night_weather: string
  day_temp: number
  night_temp: number
  wind_direction: string
  wind_power: string
}

export interface TripPlan {
  city: string
  start_date: string
  end_date: string
  days: DayPlan[]
  weather_info: WeatherInfo[]
  overall_suggestions: string
  budget?: Budget
}

export interface TripFormData {
  city: string
  start_date: string
  end_date: string
  travel_days: number
  transportation: string
  accommodation: string
  preferences: string[]
  free_text_input: string
  user_id?: string         // 🆕 用户ID，用于偏好记忆
}

export interface TripPlanResponse {
  success: boolean
  message: string
  data?: TripPlan
  plan_id?: string        // 🆕 计划ID，用于微调和历史查询
}

/** SSE 事件类型 */
export type SSEEventType = 'query_start' | 'query_complete' | 'planning_start' | 'plan_complete' | 'error'

/** SSE 事件数据 */
export interface SSEEvent {
  event: SSEEventType
  data: {
    status?: string
    city?: string
    message?: string
    plan?: TripPlan
    plan_id?: string      // 🆕 SSE 完成事件携带 plan_id
  }
}

/** 用户偏好（对应后端 UserProfile） */
export interface UserProfile {
  user_id: string
  dietary_restrictions: string[]
  travel_style: string
  budget_level: string
  visited_cities: string[]
  preferred_activities: string[]
  accommodation_preference: string
}

// ============ 🆕 计划历史 ============

export interface PlanSummary {
  plan_id: string
  city: string
  travel_days: number
  start_date: string
  end_date: string
  preferences: string[]
  created_at: string
}

export interface PlanHistoryResponse {
  success: boolean
  plans: PlanSummary[]
  total: number
}

// ============ 🆕 AI 微调 ============

export interface RefineRequest {
  plan_id: string
  message: string
  user_id?: string
}

export interface RefineResponse {
  success: boolean
  reply: string
  changes: string[]
  modified_plan?: TripPlan
}
