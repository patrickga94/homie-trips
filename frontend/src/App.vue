<script setup>
import { RouterView, RouterLink, useRouter } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen bg-gray-50 text-gray-900">
    <header class="border-b border-gray-200 bg-white">
      <div class="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <RouterLink to="/" class="text-lg font-semibold text-indigo-600">✈️ Trip App</RouterLink>
        <nav v-if="auth.isAuthenticated" class="flex items-center gap-4 text-sm">
          <span class="text-gray-500">{{ auth.user?.name }}</span>
          <button class="btn-secondary" @click="handleLogout">Log out</button>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-4xl px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>
