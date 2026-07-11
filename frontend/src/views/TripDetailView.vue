<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTripsStore } from '../stores/trips'
import { useAuthStore } from '../stores/auth'

const props = defineProps({ id: { type: [String, Number], required: true } })
const store = useTripsStore()
const auth = useAuthStore()
const router = useRouter()

const trip = ref(null)
const members = ref([])
const pendingInvites = ref([])
const flights = ref([])
const loading = ref(true)
const notice = ref('')

const isOwner = computed(() => trip.value?.my_role === 'owner')

async function loadAll() {
  loading.value = true
  try {
    trip.value = await store.fetchTrip(props.id)
    const memberData = await store.fetchMembers(props.id)
    members.value = memberData.members
    pendingInvites.value = memberData.pending_invitations
    flights.value = await store.fetchFlights(props.id)
  } finally {
    loading.value = false
  }
}

onMounted(loadAll)

// --- invite ---
const inviteEmail = ref('')
const inviteMsg = ref('')
async function invite() {
  inviteMsg.value = ''
  try {
    const res = await store.addMember(props.id, inviteEmail.value)
    inviteMsg.value = res.added
      ? `${res.added.user.email} added to the trip.`
      : `Invitation sent to ${res.invited.email}. They'll join when they register.`
    inviteEmail.value = ''
    await loadAll()
  } catch (e) {
    inviteMsg.value = e.response?.data?.email?.[0] || 'Could not add member.'
  }
}

async function removeMember(userId) {
  if (!confirm('Remove this member from the trip?')) return
  await store.removeMember(props.id, userId)
  await loadAll()
}

// --- flights ---
const showFlightForm = ref(false)
const flightForm = ref(newFlightForm())
function newFlightForm() {
  return {
    airline: '',
    flight_number: '',
    departure_airport: '',
    arrival_airport: '',
    departure_time: '',
    arrival_time: '',
    notes: '',
    travelerIds: [],
  }
}

const flightError = ref('')
async function addFlight() {
  flightError.value = ''
  const f = flightForm.value
  const payload = {
    airline: f.airline,
    flight_number: f.flight_number,
    departure_airport: f.departure_airport,
    arrival_airport: f.arrival_airport,
    notes: f.notes,
    travelers: f.travelerIds.map((uid) => ({ user: uid })),
  }
  if (f.departure_time) payload.departure_time = new Date(f.departure_time).toISOString()
  if (f.arrival_time) payload.arrival_time = new Date(f.arrival_time).toISOString()
  try {
    await store.createFlight(props.id, payload)
    flightForm.value = newFlightForm()
    showFlightForm.value = false
    flights.value = await store.fetchFlights(props.id)
  } catch (e) {
    flightError.value =
      e.response?.data?.travelers?.[0] || e.response?.data?.detail || 'Could not add flight.'
  }
}

async function removeFlight(flightId) {
  if (!confirm('Delete this flight?')) return
  await store.deleteFlight(props.id, flightId)
  flights.value = await store.fetchFlights(props.id)
}

async function deleteTrip() {
  if (!confirm('Delete this entire trip? This cannot be undone.')) return
  await store.deleteTrip(props.id)
  router.push({ name: 'trips' })
}

function fmt(dt) {
  if (!dt) return '—'
  return new Date(dt).toLocaleString([], {
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  })
}
</script>

<template>
  <div v-if="loading" class="text-gray-500">Loading…</div>
  <div v-else-if="trip" class="space-y-8">
    <!-- Header -->
    <div class="flex items-start justify-between">
      <div>
        <h1 class="text-2xl font-semibold">{{ trip.name }}</h1>
        <p v-if="trip.destination" class="text-gray-600">📍 {{ trip.destination }}</p>
        <p v-if="trip.start_date" class="text-sm text-gray-500">
          {{ trip.start_date }} <span v-if="trip.end_date">→ {{ trip.end_date }}</span>
        </p>
        <p v-if="trip.description" class="mt-2 max-w-prose text-sm text-gray-700">
          {{ trip.description }}
        </p>
      </div>
      <button v-if="isOwner" class="btn-danger" @click="deleteTrip">Delete trip</button>
    </div>

    <!-- Members -->
    <section class="space-y-3">
      <h2 class="text-lg font-medium">Members</h2>
      <ul class="divide-y divide-gray-100 rounded-lg border border-gray-200 bg-white">
        <li v-for="m in members" :key="m.id" class="flex items-center justify-between px-4 py-2">
          <span>
            {{ m.user.name }} <span class="text-gray-400">({{ m.user.email }})</span>
            <span class="ml-2 rounded-full bg-gray-100 px-2 py-0.5 text-xs text-gray-600">{{ m.role }}</span>
          </span>
          <button
            v-if="isOwner || m.user.id === auth.user?.id"
            class="btn-danger text-xs"
            @click="removeMember(m.user.id)"
          >
            Remove
          </button>
        </li>
      </ul>

      <ul v-if="pendingInvites.length" class="space-y-1 text-sm text-gray-500">
        <li v-for="inv in pendingInvites" :key="inv.id">⏳ Invited: {{ inv.email }} (pending)</li>
      </ul>

      <form class="flex gap-2" @submit.prevent="invite">
        <input v-model="inviteEmail" type="email" class="input" placeholder="friend@example.com" required />
        <button type="submit" class="btn-primary whitespace-nowrap">Add member</button>
      </form>
      <p v-if="inviteMsg" class="text-sm text-gray-600">{{ inviteMsg }}</p>
    </section>

    <!-- Flights -->
    <section class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Flights</h2>
        <button class="btn-secondary" @click="showFlightForm = !showFlightForm">
          {{ showFlightForm ? 'Cancel' : 'Add flight' }}
        </button>
      </div>

      <div v-if="showFlightForm" class="card">
        <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="addFlight">
          <div>
            <label class="label">Airline</label>
            <input v-model="flightForm.airline" class="input" placeholder="United" />
          </div>
          <div>
            <label class="label">Flight number</label>
            <input v-model="flightForm.flight_number" class="input" placeholder="UA123" />
          </div>
          <div>
            <label class="label">From (airport)</label>
            <input v-model="flightForm.departure_airport" class="input" placeholder="SFO" />
          </div>
          <div>
            <label class="label">To (airport)</label>
            <input v-model="flightForm.arrival_airport" class="input" placeholder="LIS" />
          </div>
          <div>
            <label class="label">Departure</label>
            <input v-model="flightForm.departure_time" type="datetime-local" class="input" />
          </div>
          <div>
            <label class="label">Arrival</label>
            <input v-model="flightForm.arrival_time" type="datetime-local" class="input" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Who's on this flight?</label>
            <div class="flex flex-wrap gap-3">
              <label v-for="m in members" :key="m.id" class="flex items-center gap-2 text-sm">
                <input type="checkbox" :value="m.user.id" v-model="flightForm.travelerIds" />
                {{ m.user.name }}
              </label>
            </div>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Notes</label>
            <input v-model="flightForm.notes" class="input" />
          </div>
          <div class="sm:col-span-2">
            <p v-if="flightError" class="mb-2 text-sm text-red-600">{{ flightError }}</p>
            <button type="submit" class="btn-primary">Save flight</button>
          </div>
        </form>
      </div>

      <p v-if="!flights.length" class="text-gray-500">No flights added yet.</p>
      <ul v-else class="space-y-3">
        <li v-for="f in flights" :key="f.id" class="card">
          <div class="flex items-start justify-between">
            <div>
              <p class="font-medium">
                {{ f.airline }} {{ f.flight_number }}
                <span class="text-gray-500">{{ f.departure_airport }} → {{ f.arrival_airport }}</span>
              </p>
              <p class="text-sm text-gray-600">
                Departs {{ fmt(f.departure_time) }} · Arrives {{ fmt(f.arrival_time) }}
              </p>
              <p v-if="f.notes" class="mt-1 text-sm text-gray-500">{{ f.notes }}</p>
              <div class="mt-2 flex flex-wrap gap-2">
                <span
                  v-for="t in f.travelers"
                  :key="t.id"
                  class="rounded-full bg-indigo-50 px-2 py-0.5 text-xs text-indigo-700"
                >
                  {{ t.user_detail.name }}<span v-if="t.seat"> · {{ t.seat }}</span>
                </span>
              </div>
            </div>
            <button class="btn-danger text-xs" @click="removeFlight(f.id)">Delete</button>
          </div>
        </li>
      </ul>
    </section>
  </div>
</template>
