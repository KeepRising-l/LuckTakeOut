import axios, { AxiosInstance } from 'axios'

/** ResultAPI 统一响应结构 */
export interface Result<T = unknown> {
  code: string
  info: string
  data: T
}

export interface RequestFactoryOptions {
  baseURL: string
  getToken: () => string | null
  onUnauthorized: () => void
  /** 业务失败时是否弹提示（默认由调用方处理） */
  silent?: boolean
}

/**
 * 创建统一的 axios 实例：
 * - 自动附带 Bearer token
 * - 自动解包 ResultAPI：resolve 时直接得到 data
 * - code !== '00000' 时 reject Error(info)
 * - 401 时回调 onUnauthorized（跳登录页）
 */
export function createRequest(options: RequestFactoryOptions): AxiosInstance {
  const http = axios.create({ baseURL: options.baseURL, timeout: 15000 })

  http.interceptors.request.use((config) => {
    const token = options.getToken()
    if (token) config.headers.Authorization = `Bearer ${token}`
    return config
  })

  http.interceptors.response.use(
    // 运行时返回解包后的业务数据；axios 内置类型要求返回 AxiosResponse，此处放宽签名
    (resp): any => {
      const body = resp.data as Result
      if (resp.status === 401 || body?.code === 'A0401') {
        options.onUnauthorized()
        return Promise.reject(new Error(body?.info || '未登录或登录已过期'))
      }
      if (body?.code !== '00000') {
        return Promise.reject(new Error(body?.info || '请求失败'))
      }
      return body.data
    },
    (err) => {
      if (err.response?.status === 401) options.onUnauthorized()
      const info = err.response?.data?.info || err.message || '网络异常'
      return Promise.reject(new Error(info))
    },
  )

  return http
}
