import { createRequest, storage } from '@takeout/shared'
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
export function login(data: { username: string; password: string }) {
  return http.post<never, {
    token: string; merchantId: number; merchantName: string; avatar: string
  }>('/merchant/login', data)
}
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
export type OrderStatus = 'PENDING' | 'CONFIRMED' | 'READY' | 'DELIVERING' | 'COMPLETED' | 'CANCELLED'
export interface OrderItem {
  productName: string
  skuName: string
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
  totalAmount: number
  paymentMethod: string
  remark: string
  status: OrderStatus
  createTime: string
}
export interface OrderPage extends PageData<Order> {
  stats: { pending: number; preparing: number; today: number }
}
export const fetchOrders = (params: { page: number; size: number; status?: string }) =>
  http.get<never, OrderPage>('/order/merchant', { params })
export const fetchOrder = (id: number) => http.get<never, Order>(`/order/${id}`)
export const acceptOrder = (id: number) =>
  http.put<never, Order>(`/order/${id}/status`, { status: 'CONFIRMED' })
export const cancelOrder = (id: number) => http.put<never, Order>(`/order/${id}/cancel`)

export const ORDER_STATUS_TEXT: Record<string, string> = {
  PENDING: '待接单',
  CONFIRMED: '备餐中',
  READY: '待取餐',
  DELIVERING: '配送中',
  COMPLETED: '已完成',
  CANCELLED: '已取消',
}
export const ORDER_STATUS_TAG: Record<string, string> = {
  PENDING: 'warning',
  CONFIRMED: 'primary',
  READY: 'primary',
  DELIVERING: 'warning',
  COMPLETED: 'success',
  CANCELLED: 'info',
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
export const fetchOrderStatusStats = () => http.get<never, { status: string; count: number }[]>('/stats/order-status')
export const fetchSales = () => http.get<never, { date: string; count: number }[]>('/stats/sales')
export const fetchRevenueTrend = () => http.get<never, { date: string; revenue: number }[]>('/stats/revenue-trend')
export const fetchTopProducts = () => http.get<never, { name: string; count: number }[]>('/stats/top-products')
