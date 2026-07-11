import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import client from '../api/client'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const ready = ref(false)

  const isAuthenticated = computed(() => user.value !== null)

  // Fetch the CSRF cookie, then try to restore the current session.
  async function init() {
    try {
      await client.get('/auth/csrf/')
    } catch {
      /* non-fatal */
    }
    try {
      const { data } = await client.get('/auth/me/')
      user.value = data
    } catch {
      user.value = null
    } finally {
      ready.value = true
    }
  }

  async function login(email, password) {
    const { data } = await client.post('/auth/login/', { email, password })
    user.value = data
    return data
  }

  async function register(email, password, displayName) {
    const { data } = await client.post('/auth/register/', {
      email,
      password,
      display_name: displayName || '',
    })
    user.value = data
    return data
  }

  async function logout() {
    await client.post('/auth/logout/')
    user.value = null
  }

  return { user, ready, isAuthenticated, init, login, register, logout }
})
