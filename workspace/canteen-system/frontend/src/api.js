import axios from 'axios'
import { message } from 'antd'

const api = axios.create({ baseURL: '/api', timeout: 10000 })

api.interceptors.response.use(
  (res) => res.data,
  (err) => {
    const detail = err.response?.data?.detail
    message.error(typeof detail === 'string' ? detail : '请求失败，请检查后端服务')
    return Promise.reject(err)
  },
)

export default api
