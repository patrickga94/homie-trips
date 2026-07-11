<script setup>
import { RouterView, RouterLink, useRouter, useRoute } from 'vue-router'
import { useAuthStore } from './stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()

function goBack() {
  // Return to the previous page, or fall back to the trips list on a deep link.
  if (window.history.state?.back) router.back()
  else router.push({ name: 'trips' })
}

async function handleLogout() {
  await auth.logout()
  router.push({ name: 'login' })
}
</script>

<template>
  <div class="min-h-screen bg-sand-50 text-stone-900">
    <header class="bg-forest-700 text-white shadow-sm">
      <div class="mx-auto flex max-w-4xl items-center justify-between px-4 py-3">
        <div class="flex items-center gap-1">
          <button
            v-if="auth.isAuthenticated && route.name !== 'trips'"
            class="inline-flex h-10 w-10 items-center justify-center rounded-md text-white/90 hover:bg-white/10"
            aria-label="Go back"
            @click="goBack"
          >
            <svg viewBox="0 0 20 20" fill="currentColor" class="h-6 w-6">
              <path
                fill-rule="evenodd"
                d="M11.78 5.22a.75.75 0 0 1 0 1.06L8.06 10l3.72 3.72a.75.75 0 1 1-1.06 1.06l-4.25-4.25a.75.75 0 0 1 0-1.06l4.25-4.25a.75.75 0 0 1 1.06 0Z"
                clip-rule="evenodd"
              />
            </svg>
          </button>
          <RouterLink to="/" class="text-lg font-semibold text-white">Homie Trips</RouterLink>
        </div>
        <nav v-if="auth.isAuthenticated" class="flex items-center gap-3 text-sm">
          <RouterLink
            :to="{ name: 'profile' }"
            class="max-w-[40vw] truncate text-forest-50 hover:underline"
            >{{ auth.user?.name }}</RouterLink
          >
          <button
            class="inline-flex min-h-[40px] items-center rounded-md border border-white/25 px-3 text-white hover:bg-white/10"
            @click="handleLogout"
          >
            Log out
          </button>
        </nav>
      </div>
    </header>
    <main class="mx-auto max-w-4xl px-4 py-6">
      <RouterView />
    </main>
  </div>
</template>
