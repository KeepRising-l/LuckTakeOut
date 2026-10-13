import { createRequest, storage } from '@takeout/shared'
import router from '@/router'

export const http = createRequest({
  baseURL: '/api/v1',
  getToken: () => storage.get('riderToken'),
  onUnauthorized: () => {
    storage.remove('riderToken')
    storage.remove('riderInfo')
    if (router.currentRoute.value.path !== '/login') router.replace('/login')
  },
})

export interface RiderInfo {
  riderId: number
  name: string
  phone: string
}

export interface RiderDetail {
  id: number
  name: string
  phone: string
  todayDeliveryCount: number
  /** 1 在线 2 离线 */
  workStatus: number
}

export interface OrderItem {
  name: string
  quantity: number
  price: number
}

export type TaskStatus = 'pending' | 'accepted' | 'delivering' | 'completed'

export interface DeliveryTask {
  id: number
  orderId: number
  orderNo: string
  merchantName: string
  deliveryAddress: string
  contactName: string
  contactPhone: string
  deliveryFee: number
  totalAmount: number
  status: TaskStatus
  createTime: string
  items: OrderItem[]
}

export interface TaskPage {
  list: DeliveryTask[]
  total: number
}

export interface Statistics {
  todayDeliveryCount: number
  totalDeliveryCount: number
}

export interface LoginResult {
  token: string
  riderId: number
  name: string
  phone: string
}

export const api = {
  login: (username: string, password: string) =>
    http.post<unknown, LoginResult>('/delivery/login', { username, password }),
  getRider: (riderId: number | string) =>
    http.get<unknown, RiderDetail>(`/delivery/riders/${riderId}`),
  setStatus: (riderId: number | string, workStatus: number) =>
    http.post<unknown, unknown>(`/delivery/riders/${riderId}/status?workStatus=${workStatus}`),
  getTasks: (riderId: number | string) =>
    http.get<unknown, TaskPage>(`/delivery/riders/${riderId}/tasks`),
  getPending: () => http.get<unknown, TaskPage>('/delivery/tasks/pending'),
  getTask: (id: number | string) => http.get<unknown, DeliveryTask>(`/delivery/tasks/${id}`),
  acceptTask: (id: number | string) => http.post<unknown, unknown>(`/delivery/tasks/${id}/accept`),
  /** status: 6 已送达（接单即进入配送中，本期不设中间态） */
  updateStatus: (id: number | string, status: number) =>
    http.post<unknown, unknown>(`/delivery/tasks/${id}/status`, { status }),
  getStatistics: () => http.get<unknown, Statistics>('/delivery/statistics'),
}
