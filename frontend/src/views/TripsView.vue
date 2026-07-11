<script setup>
import { ref, onMounted } from 'vue'
import { RouterLink } from 'vue-router'
import { useTripsStore } from '../stores/trips'

const store = useTripsStore()

const showForm = ref(false)
const form = ref({ name: '', destination: '', start_date: '', end_date: '' })
const saving = ref(false)
const error = ref('')

onMounted(() => store.fetchTrips())

function resetForm() {
  form.value = { name: '', destination: '', start_date: '', end_date: '' }
}

async function createTrip() {
  error.value = ''
  saving.value = true
  try {
    const payload = { ...form.value }
    // Drop empty date strings so DRF doesn't reject them.
    if (!payload.start_date) delete payload.start_date
    if (!payload.end_date) delete payload.end_date
    await store.createTrip(payload)
    await store.fetchTrips()
    resetForm()
    showForm.value = false
  } catch (e) {
    error.value = e.response?.data?.name?.[0] || 'Could not create trip.'
  } finally {
    saving.value = false
  }
}
</script>

<template>
  <div class="space-y-6">
    <div class="flex items-center justify-between">
      <h1 class="text-2xl font-semibold">Your trips</h1>
      <button class="btn-primary" @click="showForm = !showForm">
        {{ showForm ? 'Cancel' : 'New trip' }}
      </button>
    </div>

    <div v-if="showForm" class="card">
      <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="createTrip">
        <div class="sm:col-span-2">
          <label class="label">Trip name</label>
          <input v-model="form.name" class="input" required placeholder="Summer in Portugal" />
        </div>
        <div class="sm:col-span-2">
          <label class="label">Destination</label>
          <input v-model="form.destination" class="input" placeholder="Lisbon" />
        </div>
        <div>
          <label class="label">Start date</label>
          <input v-model="form.start_date" type="date" class="input" />
        </div>
        <div>
          <label class="label">End date</label>
          <input v-model="form.end_date" type="date" class="input" />
        </div>
        <div class="sm:col-span-2">
          <p v-if="error" class="mb-2 text-sm text-red-600">{{ error }}</p>
          <button type="submit" class="btn-primary" :disabled="saving">
            {{ saving ? 'Saving…' : 'Create trip' }}
          </button>
        </div>
      </form>
    </div>

    <p v-if="store.loading" class="text-gray-500">Loading…</p>
    <p v-else-if="!store.trips.length" class="text-gray-500">
      No trips yet. Create your first one!
    </p>

    <div v-else class="grid gap-4 sm:grid-cols-2">
      <RouterLink
        v-for="trip in store.trips"
        :key="trip.id"
        :to="{ name: 'trip-detail', params: { id: trip.id } }"
        class="card block transition hover:border-indigo-300 hover:shadow"
      >
        <div class="flex items-start justify-between">
          <h2 class="text-lg font-medium">{{ trip.name }}</h2>
          <span class="rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700">
            {{ trip.my_role }}
          </span>
        </div>
        <p v-if="trip.destination" class="text-sm text-gray-600">📍 {{ trip.destination }}</p>
        <p v-if="trip.start_date" class="text-sm text-gray-500">
          {{ trip.start_date }} <span v-if="trip.end_date">→ {{ trip.end_date }}</span>
        </p>
        <p class="mt-2 text-xs text-gray-400">{{ trip.member_count }} member(s)</p>
      </RouterLink>
    </div>
  </div>
</template>
