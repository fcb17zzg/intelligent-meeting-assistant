import { createApp } from 'vue'
import { createPinia } from 'pinia'
import ElementPlus from 'element-plus'
import 'element-plus/dist/index.css'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/authStore'
import '@/styles/main.scss'

const app = createApp(App)
const pinia = createPinia()

app.use(pinia)
app.use(router)
app.use(ElementPlus)

async function bootstrap() {
	// 初始化认证状态（失败时不中断页面挂载）
	const authStore = useAuthStore()
	try {
		await authStore.initAuth()
	} catch (error) {
		console.error('初始化认证状态失败:', error)
	}

	app.mount('#app')
}

bootstrap()

