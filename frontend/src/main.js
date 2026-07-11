import { createApp } from 'vue'
import { createPinia } from 'pinia'
import App from './App.vue'
import router from './router'
import { useAuthStore } from './stores/auth'
import './style.css'

const app = createApp(App)
app.use(createPinia())
app.use(router)

// Restore any existing session before the first render, so guarded routes
// resolve correctly on a hard refresh.
const auth = useAuthStore()
auth.init().finally(() => {
  app.mount('#app')
})
