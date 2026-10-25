import type { AxiosInstance } from 'axios'
import { createRequest, storage } from '@takeout/shared'
import { money, datetime } from '@takeout/shared'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

export { money, datetime }

/** 业务请求实例：自动带 token、解包 data、401 跳登录 */
export const http: AxiosInstance = createRequest({
  baseURL: '/api/v1',
  getToken: () => storage.get('customerToken'),
  onUnauthorized: () => {
    // 同时清 Pinia 内存态与本地存储，避免 isLogin 残留
    useAuthStore().logout()
    router.push('/login')
  },
})

/** AI 助手接口需登录：与其它请求共用令牌与 401 处理；推理模型多轮工具调用较慢，超时放宽到 180s */
const AI_TIMEOUT = { timeout: 180000 }

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
  rating: number | null
  deliveryFee: number
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
  merchantId: number
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
  /** 最近一笔退款申请：10 待审核 / 20 已同意 / 30 已拒绝，无申请时为 null */
  refundStatus?: number | null
  refundReason?: string
  refundRemark?: string
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
  refundApply: (id: number | string, reason: string) =>
    http.post<never, { refundId: number; refundAmount: number }>(`/orders/${id}/refund`, { reason }),
  review: (id: number | string, data: { rating: number; content: string }) =>
    http.post(`/orders/${id}/review`, data),
}

export interface TasteProfile {
  orderCount: number
  avgAmount: number
  totalSpend: number
  favoriteSlot: string
  topMerchants: { merchantId: number; name: string; orders: number }[]
  topDishes: { productId: number; name: string; merchantName: string; times: number }[]
}

export interface RecommendedDish {
  productId: number
  name: string
  image: string
  price: number
  merchantId: number
  merchantName: string
  reason: string
}

export const aiApi = {
  createSession: () => http.post<never, AiSession>('/ai/session', {}, AI_TIMEOUT),
  chat: (sessionId: string, message: string) =>
    http.post<never, { reply: string; draft?: AiDraft }>('/ai/chat', { sessionId, message }, AI_TIMEOUT),
  confirmDraft: (draftId: string | number) =>
    http.post<never, { orderId: number; orderNo: string; actualAmount: number }>(
      `/ai/drafts/${draftId}/confirm`,
      {},
      AI_TIMEOUT,
    ),
  /** 首页「猜你想吃」：口味画像 + 推荐菜品 */
  recommend: () => http.get<never, { profile: TasteProfile; dishes: RecommendedDish[] }>('/ai/recommend'),
  /** 一键复购：按最近订单生成待确认草稿 */
  reorder: () =>
    http.post<never, {
      draftId: number
      merchantName: string
      sourceOrderNo: string
      total: number
      address: string
      items: { name: string; quantity: number; price: number }[]
      skipped: string[]
    }>('/ai/reorder', {}, AI_TIMEOUT),
}

/** 状态文案：与三端共用的取值口径一致 */
export { ORDER_STATUS } from '@takeout/shared'

/** 商品图兜底：后端可能用 image/mainImage/productImage 任意字段 */
export function pickImage(obj: { image?: string; mainImage?: string; productImage?: string; avatar?: string; logo?: string }): string {
  return obj.image || obj.mainImage || obj.productImage || obj.avatar || obj.logo || ''
}
