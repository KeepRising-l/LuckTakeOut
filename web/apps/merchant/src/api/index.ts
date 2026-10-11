import { createRequest, storage, ORDER_STATUS } from '@takeout/shared'
import type { AxiosInstance } from 'axios'
import router from '@/router'
import { useAuthStore } from '@/stores/auth'

export const http: AxiosInstance = createRequest({
  baseURL: '/api',
  getToken: () => storage.get('merchantToken'),
  onUnauthorized: () => {
    useAuthStore().logout()
    router.push('/login')
  },
})

// ---- 认证 ----
export interface LoginResult {
  token: string
  merchantId: number
  merchantName: string
  avatar: string
  /** 入驻审核状态：10 待审核 / 20 已通过 / 30 已驳回 */
  status: number
}

export interface RegisterPayload {
  username: string
  password: string
  name: string
  phone: string
  address: string
  description?: string
}

export const login = (data: { username: string; password: string }) =>
  http.post<never, LoginResult>('/merchant/login', data)
export const register = (data: RegisterPayload) =>
  http.post<never, LoginResult>('/merchant/register', data)
export const fetchCurrent = () => http.get<never, MerchantCurrent>('/merchant/current')
export const updateMerchantInfo = (data: Partial<{ name: string; description: string; phone: string; address: string; logo: string }>) =>
  http.put<never, MerchantCurrent>('/merchant/info', data)
export const updateMerchantStatus = (open: boolean) =>
  http.put<never, { status: unknown }>('/merchant/status', { open })
export const uploadAvatar = (file: File) => {
  const fd = new FormData()
  fd.append('file', file)
  return http.post<never, { logo: string }>('/merchant/avatar', fd)
}

export interface MerchantCurrent {
  id: number
  name: string
  logo?: string
  avatar?: string
  description: string
  phone: string
  address: string
  /** 入驻审核状态：10 待审核 / 20 已通过 / 30 已驳回 */
  status: number
  open?: boolean
  openTime?: string
  closeTime?: string
}

// ---- 菜品 ----
export interface Product {
  id: number
  name: string
  description: string
  image: string
  price: number
  stock: number
  status: 'ACTIVE' | 'INACTIVE'
  categoryId: number | null
  categoryName: string
  createTime: string
}
export interface PageData<T> { items: T[]; total: number; page: number; size: number }
export const fetchProducts = (params: { page: number; size: number }) =>
  http.get<never, PageData<Product>>('/product/merchant', { params })
export const createProduct = (data: { name: string; description: string; price: number; stock: number; categoryId: number | null; image?: string }) =>
  http.post<never, Product>('/product', data)
export const updateProduct = (id: number, data: Record<string, unknown>) =>
  http.put<never, Product>(`/product/${id}`, data)
export const deleteProduct = (id: number) => http.delete<never, unknown>(`/product/${id}`)
export const updateProductStatus = (id: number, status: 'ACTIVE' | 'INACTIVE') =>
  http.put<never, unknown>(`/product/${id}/status`, { status })
export const updateProductStock = (id: number, stock: number) =>
  http.put<never, unknown>(`/product/${id}/stock`, { stock })

// ---- 分类 ----
export interface Category {
  id: number
  name: string
  description: string
  sortOrder: number
  productCount: number
  createTime: string
}
export const fetchCategories = () => http.get<never, Category[]>('/product/categories')
export const createCategory = (data: { name: string; description?: string; sortOrder?: number }) =>
  http.post<never, Category>('/product/category', data)
export const updateCategory = (id: number, data: { name?: string; description?: string; sortOrder?: number }) =>
  http.put<never, Category>(`/product/category/${id}`, data)
export const deleteCategory = (id: number) => http.delete<never, unknown>(`/product/category/${id}`)

// ---- 订单 ----
/** 订单状态：与后端整数枚举一致（10–60），商户端覆盖 30 的措辞 */
export type OrderStatus = number
export interface OrderItem {
  productName: string
  price: number
  quantity: number
  amount: number
}
export interface Order {
  id: number
  orderNumber: string
  customerName: string
  customerPhone: string
  deliveryAddress: string
  items: OrderItem[]
  productAmount: number
  deliveryFee: number
  totalAmount: number
  paymentMethod: string
  remark: string
  status: OrderStatus
  createTime: string
}
export interface OrderPage extends PageData<Order> {
  stats: { pending: number; preparing: number; today: number }
}
export const fetchOrders = (params: { page: number; size: number; status?: number }) =>
  http.get<never, OrderPage>('/order/merchant', { params })
export const fetchOrder = (id: number) => http.get<never, Order>(`/order/${id}`)
export const acceptOrder = (id: number) =>
  http.put<never, Order>(`/order/${id}/status`, { status: 30 })
export const cancelOrder = (id: number) => http.put<never, Order>(`/order/${id}/cancel`)

/** 商户端状态文案：取值与三端一致，30 按商户视角呈现为「已接单，待骑手取餐」 */
export const ORDER_STATUS_TEXT: Record<number, string> = {
  ...ORDER_STATUS,
  30: '已接单，待骑手取餐',
}
export const ORDER_STATUS_TAG: Record<number, string> = {
  10: 'warning',
  20: 'warning',
  30: 'primary',
  40: 'warning',
  50: 'success',
  60: 'info',
}

// ---- 统计 ----
export interface Overview {
  todayOrders: number
  todayRevenue: number
  totalOrders: number
  totalRevenue: number
  pendingCount: number
}
export const fetchOverview = () => http.get<never, Overview>('/stats/overview')
export const fetchRecentOrders = () => http.get<never, Order[]>('/stats/recent-orders')
export const fetchOrderStatusStats = () => http.get<never, { status: number; count: number }[]>('/stats/order-status')
export const fetchSales = () => http.get<never, { date: string; count: number }[]>('/stats/sales')
export const fetchRevenueTrend = () => http.get<never, { date: string; revenue: number }[]>('/stats/revenue-trend')
export const fetchTopProducts = () => http.get<never, { name: string; count: number }[]>('/stats/top-products')
