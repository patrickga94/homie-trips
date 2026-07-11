<script setup>
import { ref } from 'vue'
import { useRouter, RouterLink } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()
const router = useRouter()

const email = ref('')
const displayName = ref('')
const password = ref('')
const errors = ref([])
const submitting = ref(false)

function flattenErrors(data) {
  if (!data) return ['Registration failed.']
  if (typeof data === 'string') return [data]
  return Object.entries(data).flatMap(([field, msgs]) =>
    (Array.isArray(msgs) ? msgs : [msgs]).map((m) => `${field}: ${m}`),
  )
}

async function submit() {
  errors.value = []
  submitting.value = true
  try {
    await auth.register(email.value, password.value, displayName.value)
    router.push({ name: 'trips' })
  } catch (e) {
    errors.value = flattenErrors(e.response?.data)
  } finally {
    submitting.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-sm">
    <div class="card">
      <h1 class="mb-4 text-xl font-semibold">Create account</h1>
      <form class="space-y-4" @submit.prevent="submit">
        <div>
          <label class="label">Email</label>
          <input v-model="email" type="email" class="input" required autocomplete="email" />
        </div>
        <div>
          <label class="label">Display name (optional)</label>
          <input v-model="displayName" type="text" class="input" autocomplete="name" />
        </div>
        <div>
          <label class="label">Password</label>
          <input v-model="password" type="password" class="input" required autocomplete="new-password" />
        </div>
        <ul v-if="errors.length" class="space-y-1 text-sm text-red-600">
          <li v-for="(msg, i) in errors" :key="i">{{ msg }}</li>
        </ul>
        <button type="submit" class="btn-primary w-full" :disabled="submitting">
          {{ submitting ? 'Creating…' : 'Create account' }}
        </button>
      </form>
      <p class="mt-4 text-center text-sm text-gray-500">
        Have an account?
        <RouterLink to="/login" class="text-indigo-600 hover:underline">Log in</RouterLink>
      </p>
    </div>
  </div>
</template>
