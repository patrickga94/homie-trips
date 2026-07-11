<script setup>
import { ref, onMounted } from 'vue'
import { useAuthStore } from '../stores/auth'

const auth = useAuthStore()

const form = ref({ first_name: '', last_name: '', preferred_name: '' })
const restrictions = ref([])
const newRestriction = ref('')
const saving = ref(false)
const savedMsg = ref('')
const error = ref('')

function loadFromUser() {
  const u = auth.user || {}
  form.value = {
    first_name: u.first_name || '',
    last_name: u.last_name || '',
    preferred_name: u.preferred_name || '',
  }
  restrictions.value = [...(u.dietary_restrictions || [])]
}
onMounted(loadFromUser)

function addRestriction() {
  const v = newRestriction.value.trim()
  if (v && !restrictions.value.includes(v)) restrictions.value.push(v)
  newRestriction.value = ''
}
function removeRestriction(i) {
  restrictions.value.splice(i, 1)
}

async function save() {
  error.value = ''
  savedMsg.value = ''
  saving.value = true
  try {
    // Fold any half-typed entry in before saving.
    addRestriction()
    await auth.updateProfile({ ...form.value, dietary_restrictions: restrictions.value })
    savedMsg.value = 'Profile saved.'
  } catch (e) {
    error.value = e.response?.data?.detail || 'Could not save profile.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="mx-auto max-w-lg space-y-6">
    <h1 class="text-2xl font-semibold">Your profile</h1>
    <div class="card">
      <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="save">
        <div>
          <label class="label">First name</label>
          <input v-model="form.first_name" class="input" autocomplete="given-name" />
        </div>
        <div>
          <label class="label">Last name</label>
          <input v-model="form.last_name" class="input" autocomplete="family-name" />
        </div>
        <div class="sm:col-span-2">
          <label class="label">Preferred name</label>
          <input
            v-model="form.preferred_name"
            class="input"
            autocomplete="nickname"
            placeholder="What should we call you?"
          />
        </div>

        <div class="sm:col-span-2">
          <label class="label">Allergies &amp; dietary restrictions</label>
          <div v-if="restrictions.length" class="mb-2 flex flex-wrap gap-2">
            <span
              v-for="(r, i) in restrictions"
              :key="i"
              class="inline-flex items-center gap-1 rounded-full bg-clay-50 px-2 py-1 text-sm text-clay-700"
            >
              {{ r }}
              <button
                type="button"
                class="text-clay-500 hover:text-clay-700"
                aria-label="Remove"
                @click="removeRestriction(i)"
              >
                ×
              </button>
            </span>
          </div>
          <div class="flex flex-col gap-2 sm:flex-row">
            <input
              v-model="newRestriction"
              class="input"
              placeholder="e.g. vegetarian, peanut allergy"
              @keydown.enter.prevent="addRestriction"
            />
            <button type="button" class="btn-secondary whitespace-nowrap" @click="addRestriction">
              Add
            </button>
          </div>
          <p class="mt-1 text-xs text-stone-400">Press Enter or tap Add for each item.</p>
        </div>

        <div class="flex flex-wrap items-center gap-3 sm:col-span-2">
          <button type="submit" class="btn-primary" :disabled="saving">
            {{ saving ? 'Saving…' : 'Save profile' }}
          </button>
          <span v-if="savedMsg" class="text-sm text-forest-700">{{ savedMsg }}</span>
          <span v-if="error" class="text-sm text-clay-600">{{ error }}</span>
        </div>
      </form>
    </div>
  </div>
</template>
