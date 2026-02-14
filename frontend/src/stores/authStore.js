/**
 * 用户认证状态管理 (Pinia Store)
 */
import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import * as authAPI from '@/api/auth'
import apiClient from '@/api/client'

export const useAuthStore = defineStore('auth', () => {
  // 状态
  const user = ref(null)
  const token = ref(localStorage.getItem('access_token'))
  const loading = ref(false)
  const error = ref(null)

  // 计算属性
  const isAuthenticated = computed(() => !!token.value && !!user.value)
  const userRole = computed(() => user.value?.role || null)
  const isAdmin = computed(() => userRole.value === 'admin')
  const isManager = computed(() => ['admin', 'manager'].includes(userRole.value))

  /**
   * 注册新用户
   */
  const register = async (userData) => {
    loading.value = true
    error.value = null

    try {
      const response = await authAPI.register(userData)
      user.value = response
      return response
    } catch (err) {
      error.value = err.message || '注册失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 登录
   */
  const login = async (loginData) => {
    loading.value = true
    error.value = null

    try {
      const response = await authAPI.login(loginData)
      
      // 保存token和用户信息
      token.value = response.access_token
      user.value = response.user
      apiClient.setToken(token.value)

      return response
    } catch (err) {
      error.value = err.message || '登录失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 获取当前用户信息
   */
  const fetchCurrentUser = async () => {
    if (!token.value) return null

    loading.value = true
    error.value = null

    try {
      const response = await authAPI.getCurrentUser()
      user.value = response
      return response
    } catch (err) {
      error.value = err.message || '获取用户信息失败'
      // 如果获取失败，清除token
      if (err.status === 401) {
        logout()
      }
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 刷新Token
   */
  const refresh = async () => {
    if (!token.value) return null

    try {
      const response = await authAPI.refreshToken()
      token.value = response.access_token
      user.value = response.user
      apiClient.setToken(token.value)
      return response
    } catch (err) {
      error.value = err.message || 'Token刷新失败'
      logout()
      throw err
    }
  }

  /**
   * 登出
   */
  const logout = () => {
    token.value = null
    user.value = null
    error.value = null
    apiClient.setToken(null)
  }

  /**
   * 更新用户信息
   */
  const updateUserInfo = async (userId, userData) => {
    loading.value = true
    error.value = null

    try {
      const response = await authAPI.updateUser(userId, userData)
      
      // 如果更新的是当前用户，更新store中的用户信息
      if (userId === user.value?.id) {
        user.value = response
      }

      return response
    } catch (err) {
      error.value = err.message || '更新用户信息失败'
      throw err
    } finally {
      loading.value = false
    }
  }

  /**
   * 检查权限
   */
  const hasRole = (role) => {
    if (typeof role === 'string') {
      return userRole.value === role
    }
    return role.includes(userRole.value)
  }

  /**
   * 初始化认证状态
   */
  const initAuth = async () => {
    if (token.value) {
      apiClient.setToken(token.value)
      try {
        await fetchCurrentUser()
      } catch (err) {
        console.warn('初始化认证失败', err)
        logout()
      }
    }
  }

  return {
    // 状态
    user,
    token,
    loading,
    error,
    
    // 计算属性
    isAuthenticated,
    userRole,
    isAdmin,
    isManager,
    
    // 方法
    register,
    login,
    fetchCurrentUser,
    refresh,
    logout,
    updateUserInfo,
    hasRole,
    initAuth,
  }
})
