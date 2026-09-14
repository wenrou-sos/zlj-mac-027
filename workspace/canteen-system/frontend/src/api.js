import axios from 'axios'
import { message } from 'antd'
import { clearAuth, getToken } from './auth'

const api = axios.create({ baseURL: '/api', timeout: 10000 })

api.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  return config
})

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const isLoginRequest = err.config?.url?.includes('/auth/login')
    if (err.response?.status === 401 && !isLoginRequest) {
      // 已登录会话过期：清登录态并回登录页
      clearAuth()
      message.warning('登录已过期，请重新登录')
      setTimeout(() => window.location.reload(), 600)
    } else {
      // 登录失败（密码错误）及其他错误：只提示，不刷新页面
      const detail = err.response?.data?.detail
      message.error(typeof detail === 'string' ? detail : '请求失败，请检查后端服务')
    }
    return Promise.reject(err)
  },
)

export default api
