/**
 * 认证API
 */
import apiClient from './client'

/**
 * 用户注册
 */
export const register = (userData) => {
  return apiClient.post('/auth/register', userData)
}

/**
 * 用户登录
 */
export const login = (loginData) => {
  return apiClient.post('/auth/login', loginData)
}

/**
 * 获取当前用户信息
 */
export const getCurrentUser = () => {
  return apiClient.get('/auth/me')
}

/**
 * 刷新Token
 */
export const refreshToken = () => {
  return apiClient.post('/auth/refresh', {})
}

/**
 * 用户登出
 */
export const logout = () => {
  apiClient.setToken(null)
}

/**
 * 获取用户列表
 */
export const getUsers = (skip = 0, limit = 10) => {
  return apiClient.get(`/users?skip=${skip}&limit=${limit}`)
}

/**
 * 获取特定用户
 */
export const getUser = (userId) => {
  return apiClient.get(`/users/${userId}`)
}

/**
 * 更新用户信息
 */
export const updateUser = (userId, userData) => {
  return apiClient.put(`/users/${userId}`, userData)
}

/**
 * 删除用户
 */
export const deleteUser = (userId) => {
  return apiClient.delete(`/users/${userId}`)
}
