<script setup>
import { ref } from 'vue'
import { useRouter, useRoute, RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

const email = ref('')
const password = ref('')
const error = ref('')
const submitting = ref(false)

async function submit() {
  error.value = ''
  submitting.value = true
  try {
    await auth.login(email.value, password.value)
    router.push(route.query.next || { name: 'trips' })
  } catch (e) {
    error.value = e.response?.data?.detail || 'Invalid email or password.'
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-sm">
    <div class="card">
      <h1 class="mb-4 text-xl font-semibold">Log in</h1>
      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="label">Email</label>
          <input v-model="email" type="email" class="input" required autocomplete="email" />
        </div>
        <div>
          <label class="label">Password</label>
          <input v-model="password" type="password" class="input" required autocomplete="current-password" />
        </div>
        <p v-if="error" class="text-sm text-clay-600">{{ error }}</p>
        <button type="submit" class="btn-primary w-full" :disabled="submitting">
          {{ submitting ? 'Logging in…' : 'Log in' }}
        </button>
      </form>
      <p class="mt-4 text-center text-sm text-stone-500">
        No account?
        <RouterLink to="/register" class="text-forest-600 hover:underline">Register</RouterLink>
      </p>
    </div>
  </div>
</template>
