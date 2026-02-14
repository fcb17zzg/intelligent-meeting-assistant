<template>
  <template v-if="hasPermission">
    <slot />
  </template>
</template>

<script setup>
import { computed } from 'vue'
import { useAuthStore } from '@/stores/authStore'

const props = defineProps({
  /**
   * 所需角色
   * 可以是单个字符串或字符串数组
   */
  role: {
    type: [String, Array],
    default: null,
  },
  /**
   * 需要成为管理员
   */
  admin: {
    type: Boolean,
    default: false,
  },
  /**
   * 需要认证
   */
  auth: {
    type: Boolean,
    default: false,
  },
})

const authStore = useAuthStore()

/**
 * 是否有权限显示
 */
const hasPermission = computed(() => {
  // 如果需要认证但未认证
  if (props.auth && !authStore.isAuthenticated) {
    return false
  }

  // 如果需要管理员权限
  if (props.admin && !authStore.isAdmin) {
    return false
  }

  // 如果指定了角色
  if (props.role) {
    return authStore.hasRole(props.role)
  }

  return true
})
</script>
