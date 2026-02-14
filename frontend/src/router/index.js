import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/authStore'
import MeetingList from '@/pages/MeetingList.vue'
import MeetingDetail from '@/pages/MeetingDetail.vue'
import CreateMeeting from '@/pages/CreateMeeting.vue'
import Login from '@/pages/Login.vue'
import Register from '@/pages/Register.vue'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: Login,
    meta: { requiresAuth: false },
  },
  {
    path: '/register',
    name: 'Register',
    component: Register,
    meta: { requiresAuth: false },
  },
  {
    path: '/',
    redirect: '/meetings',
  },
  {
    path: '/meetings',
    name: 'MeetingList',
    component: MeetingList,
    meta: { requiresAuth: true },
  },
  {
    path: '/meetings/create',
    name: 'CreateMeeting',
    component: CreateMeeting,
    meta: { requiresAuth: true },
  },
  {
    path: '/meetings/:id',
    name: 'MeetingDetail',
    component: MeetingDetail,
    props: true,
    meta: { requiresAuth: true },
  },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

// 路由守卫
router.beforeEach(async (to, from, next) => {
  const authStore = useAuthStore()
  
  // 初始化认证状态（如果还未初始化）
  if (!authStore.user && authStore.token) {
    try {
      await authStore.fetchCurrentUser()
    } catch (error) {
      console.error('初始化认证失败:', error)
      authStore.logout()
    }
  }

  const requiresAuth = to.meta.requiresAuth !== false
  const isAuthenticated = authStore.isAuthenticated

  if (requiresAuth && !isAuthenticated) {
    // 需要认证但未登录，重定向到登录页面
    next({
      name: 'Login',
      query: { redirect: to.fullPath },
    })
  } else if (!requiresAuth && isAuthenticated && (to.name === 'Login' || to.name === 'Register')) {
    // 已登录且试图访问登录/注册页面，重定向到首页
    next({ path: '/meetings' })
  } else {
    next()
  }
})

export default router
