import axios, { AxiosInstance } from 'axios'
import { createRequest, storage } from '@takeout/shared'
import { money, datetime } from '@takeout/shared'
import router from '@/router'

export { money, datetime }

/** 业务请求实例：自动带 token、解包 data、401 跳登录 */
export const http: AxiosInstance = createRequest({
  baseURL: '/api/v1',
  getToken: () => storage.get('customerToken'),
  onUnauthorized: () => {
    storage.remove('customerToken')
    storage.remove('customerInfo')
    router.push('/login')
  },
})

/** AI 接口无鉴权，独立实例（不触发 401 跳转） */
export const aiHttp: AxiosInstance = axios.create({ baseURL: '/api/v1', timeout: 30000 })

export interface UserInfo {
  id?: number
  userId?: number
  nickname: string
  phone: string
  avatar: string
  gender?: number
}

export interface LoginResult {
  accessToken: string
  refreshToken: string
  user: UserInfo
}

export interface Address {
  id: number
  name: string
  phone: string
  detail: string
  province: string
  city: string
  district: string
  tag?: string
  isDefault: boolean
}

export interface Merchant {
  id: number
  name: string
  avatar: string
  logo?: string
  description: string
  rating: number
  monthlySales: number
  tags: string[]
  deliveryFee: number
  deliveryTime: number
  distance: number
  address: string
}

export interface Category {
  id: number
  name: string
}

export interface Product {
  id: number
  name: string
  description: string
  image: string
  mainImage?: string
  productImage?: string
  price: number
  stock: number
  categoryId: number
  categoryName: string
  tags: string[]
}

export interface OrderItem {
  productId: number
  productName: string
  skuName?: string
  price: number
  quantity: number
  amount: number
}

export interface Order {
  id: number
  orderNo: string
  merchantId: number
  merchantName: string
  status: number
  productAmount: number
  deliveryFee: number
  discountAmount: number
  actualAmount: number
  address: string
  remark: string
  createTime: string
  items: OrderItem[]
}

export interface ReviewPage {
  list: Array<{ id: number; content: string; rating: number; createTime?: string; nickname?: string }>
  total: number
  avgRating: number
}

export interface AiDraft {
  draftId: string | number
  merchantName: string
  items: Array<{ name: string; quantity: number; price?: number }>
  address: string
  total: number
}

export interface AiSession {
  sessionId: string
  customerId: number | string
  customerName: string
}

export const authApi = {
  sendCode: (phone: string) => http.post<never, { phone: string; code: string }>('/auth/code', { phone }),
  login: (phone: string, code: string) => http.post<never, LoginResult>('/auth/login', { phone, code }),
}

export const userApi = {
  profile: () => http.get<never, UserInfo>('/users/profile'),
}

export const addressApi = {
  list: () => http.get<never, Address[]>('/addresses'),
  create: (data: Partial<Address>) => http.post<never, Address>('/addresses', data),
  remove: (id: number) => http.delete(`/addresses/${id}`),
  update: (id: number, data: Partial<Address>) => http.post<never, Address>('/addresses', { id, ...data }),
}

export const merchantApi = {
  nearby: (params: { page?: number; size?: number; keyword?: string; category?: string }) =>
    http.get<never, Merchant[]>('/merchants/nearby', { params }),
  detail: (id: number | string) => http.get<never, Merchant>(`/merchants/${id}`),
  categories: (id: number | string) => http.get<never, Category[]>(`/merchants/${id}/categories`),
  products: (id: number | string, params: { page?: number; size?: number; categoryId?: number }) =>
    http.get<never, Product[]>(`/merchants/${id}/products`, { params }),
  reviews: (id: number | string) => http.get<never, ReviewPage>(`/merchants/${id}/reviews`),
}

export const productApi = {
  search: (keyword: string) => http.get<never, Product[]>('/products/search', { params: { keyword } }),
  detail: (id: number | string) => http.get<never, Product>(`/products/${id}`),
}

export const orderApi = {
  create: (data: {
    merchantId: number
    items: Array<{ productId: number; quantity: number }>
    deliveryFee: number
    remark: string
    addressId: number
  }) => http.post<never, { id: number; orderNo: string; actualAmount: number }>('/orders', data),
  list: () => http.get<never, Order[]>('/orders/user'),
  detail: (id: number | string) => http.get<never, Order>(`/orders/${id}`),
  pay: (id: number | string) => http.post(`/orders/${id}/pay`),
  cancel: (id: number | string) => http.post(`/orders/${id}/cancel`),
  review: (id: number | string, data: { rating: number; content: string }) =>
    http.post(`/orders/${id}/review`, data),
}

export const aiApi = {
  createSession: () => aiHttp.post<never, { code: string; data: AiSession }>('/ai/session', {}),
  chat: (sessionId: string, message: string) =>
    aiHttp.post<never, { code: string; data: { reply: string; draft?: AiDraft } }>('/ai/chat', {
      sessionId,
      message,
    }),
  confirmDraft: (draftId: string | number) =>
    aiHttp.post<never, { code: string; data: { orderId: number; orderNo: string; actualAmount: number } }>(
      `/ai/drafts/${draftId}/confirm`,
    ),
}

/** 状态码 → 文案 */
export const ORDER_STATUS: Record<number, string> = {
  1: '待支付',
  2: '已支付',
  3: '待接单',
  5: '配送中',
  8: '已完成',
  9: '已取消',
}

/** 商品图兜底：后端可能用 image/mainImage/productImage 任意字段 */
export function pickImage(obj: { image?: string; mainImage?: string; productImage?: string; avatar?: string; logo?: string }): string {
  return obj.image || obj.mainImage || obj.productImage || obj.avatar || obj.logo || ''
}
