import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000/api'

const client = axios.create({
  baseURL: API_BASE_URL,
  timeout: 30000,
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
client.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('access_token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => Promise.reject(error)
)

// 响应拦截器
client.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const data = error.response?.data
    
    // 处理401未授权
    if (status === 401) {
      localStorage.removeItem('access_token')
      localStorage.removeItem('user')
      // 导航到登录页面
      if (window.location.pathname !== '/login') {
        window.location.href = '/login?redirect=' + encodeURIComponent(window.location.pathname)
      }
    }
    
    // 处理403禁止访问
    if (status === 403) {
      console.warn('权限不足:', data?.detail)
    }
    
    return Promise.reject(data || error.message)
  }
)

/**
 * 设置认证令牌
 * @param {string} token - JWT令牌
 */
const setToken = (token) => {
  if (token) {
    client.defaults.headers.common['Authorization'] = `Bearer ${token}`
    localStorage.setItem('access_token', token)
  } else {
    delete client.defaults.headers.common['Authorization']
    localStorage.removeItem('access_token')
  }
}

/**
 * 清除认证令牌
 */
const clearToken = () => {
  delete client.defaults.headers.common['Authorization']
  localStorage.removeItem('access_token')
}

// 将方法添加到client对象
client.setToken = setToken
client.clearToken = clearToken

export default client
