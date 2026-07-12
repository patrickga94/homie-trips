<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTripsStore } from '../stores/trips'
import { useAuthStore } from '../stores/auth'
import AirportPicker from '../components/AirportPicker.vue'

const props = defineProps({ id: { type: [String, Number], required: true } })
const store = useTripsStore()
const auth = useAuthStore()
const router = useRouter()

const trip = ref(null)
const members = ref([])
const pendingInvites = ref([])
const flights = ref([])
const accommodations = ref([])
const loading = ref(true)
const notice = ref('')

const isOwner = computed(() => trip.value?.my_role === 'owner')

// --- edit trip ---
const editing = ref(false)
const editForm = ref({})
const editError = ref('')

function startEdit() {
  editForm.value = {
    name: trip.value.name,
    destination: trip.value.destination || '',
    description: trip.value.description || '',
    start_date: trip.value.start_date || '',
    end_date: trip.value.end_date || '',
  }
  editError.value = ''
  editing.value = true
}

async function saveEdit() {
  editError.value = ''
  const payload = { ...editForm.value }
  // Clear optional dates with null rather than an empty string.
  payload.start_date = payload.start_date || null
  payload.end_date = payload.end_date || null
  try {
    trip.value = await store.updateTrip(props.id, payload)
    editing.value = false
  } catch (e) {
    editError.value = e.response?.data?.name?.[0] || 'Could not save changes.'
  }
}

async function loadAll() {
  loading.value = true
  try {
    trip.value = await store.fetchTrip(props.id)
    const memberData = await store.fetchMembers(props.id)
    members.value = memberData.members
    pendingInvites.value = memberData.pending_invitations
    flights.value = await store.fetchFlights(props.id)
    accommodations.value = await store.fetchAccommodations(props.id)
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
const editingFlightId = ref(null)
const flightError = ref('')
const flightForm = ref(blankFlightForm())
const travelerRows = ref([])

const flightGroups = computed(() =>
  [
    { key: 'arrival', label: 'Arrival', flights: flights.value.filter((f) => f.direction === 'arrival') },
    { key: 'departure', label: 'Departure', flights: flights.value.filter((f) => f.direction === 'departure') },
  ].filter((g) => g.flights.length),
)

// Per-person view: each member's arrival + departure flights (for "who's
// flying when"), sorted by soonest arrival. Members with no flights still
// appear, showing "—", and fall to the bottom.
const flightSummary = computed(() => {
  const rows = members.value.map((m) => {
    const mine = flights.value.filter((f) => f.travelers?.some((t) => t.user === m.user.id))
    return {
      userId: m.user.id,
      name: m.user.name,
      arrivals: mine.filter((f) => f.direction === 'arrival'),
      departures: mine.filter((f) => f.direction === 'departure'),
    }
  })
  const arrivalKey = (p) => {
    const times = p.arrivals
      .map((f) => f.departure_time)
      .filter(Boolean)
      .map((t) => new Date(t).getTime())
    return times.length ? Math.min(...times) : Infinity
  }
  // Array.sort is stable, so people without arrivals keep membership order.
  return rows.sort((a, b) => arrivalKey(a) - arrivalKey(b))
})

function blankFlightForm() {
  return {
    direction: 'arrival',
    airline: '',
    flight_number: '',
    departure_airport: '',
    arrival_airport: '',
    departure_time: '',
    arrival_time: '',
    notes: '',
  }
}

// One editable row per trip member, pre-filled from an existing flight's
// travelers when editing (so confirmation codes / seats aren't lost on save).
function buildTravelerRows(existing = []) {
  const byUser = new Map(existing.map((t) => [t.user, t]))
  return members.value.map((m) => {
    const t = byUser.get(m.user.id)
    return {
      userId: m.user.id,
      name: m.user.name,
      selected: !!t,
      confirmation_code: t?.confirmation_code || '',
      seat: t?.seat || '',
    }
  })
}

// Convert a UTC ISO string to the local "YYYY-MM-DDTHH:mm" datetime-local needs.
function toLocalInput(iso) {
  if (!iso) return ''
  const d = new Date(iso)
  const pad = (n) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}T${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function openAddFlight() {
  flightForm.value = blankFlightForm()
  travelerRows.value = buildTravelerRows([])
  editingFlightId.value = null
  flightError.value = ''
  showFlightForm.value = true
}

function openEditFlight(f) {
  flightForm.value = {
    direction: f.direction || 'arrival',
    airline: f.airline || '',
    flight_number: f.flight_number || '',
    departure_airport: f.departure_airport || '',
    arrival_airport: f.arrival_airport || '',
    departure_time: toLocalInput(f.departure_time),
    arrival_time: toLocalInput(f.arrival_time),
    notes: f.notes || '',
  }
  travelerRows.value = buildTravelerRows(f.travelers || [])
  editingFlightId.value = f.id
  flightError.value = ''
  showFlightForm.value = true
}

function closeFlightForm() {
  showFlightForm.value = false
  editingFlightId.value = null
}

async function saveFlight() {
  flightError.value = ''
  const f = flightForm.value
  const payload = {
    direction: f.direction,
    airline: f.airline,
    flight_number: f.flight_number,
    departure_airport: f.departure_airport,
    arrival_airport: f.arrival_airport,
    notes: f.notes,
    departure_time: f.departure_time ? new Date(f.departure_time).toISOString() : null,
    arrival_time: f.arrival_time ? new Date(f.arrival_time).toISOString() : null,
    travelers: travelerRows.value
      .filter((r) => r.selected)
      .map((r) => ({ user: r.userId, confirmation_code: r.confirmation_code, seat: r.seat })),
  }
  try {
    if (editingFlightId.value) {
      await store.updateFlight(props.id, editingFlightId.value, payload)
    } else {
      await store.createFlight(props.id, payload)
    }
    closeFlightForm()
    flights.value = await store.fetchFlights(props.id)
  } catch (e) {
    flightError.value =
      e.response?.data?.travelers?.[0] || e.response?.data?.detail || 'Could not save flight.'
  }
}

async function removeFlight(flightId) {
  if (!confirm('Delete this flight?')) return
  await store.deleteFlight(props.id, flightId)
  flights.value = await store.fetchFlights(props.id)
}

// --- accommodations ---
const showAccForm = ref(false)
const editingAccId = ref(null)
const accError = ref('')
const accForm = ref(blankAccForm())

function blankAccForm() {
  return {
    name: '',
    address: '',
    beds: null,
    link: '',
    image_url: '',
    check_in: '',
    check_out: '',
    notes: '',
  }
}

function openAddAcc() {
  accForm.value = blankAccForm()
  // Auto-fill the stay to the trip's dates; the user can still adjust them.
  accForm.value.check_in = trip.value?.start_date || ''
  accForm.value.check_out = trip.value?.end_date || ''
  editingAccId.value = null
  accError.value = ''
  showAccForm.value = true
}

function openEditAcc(a) {
  accForm.value = {
    name: a.name || '',
    address: a.address || '',
    beds: a.beds,
    link: a.link || '',
    image_url: a.image_url || '',
    check_in: a.check_in || '',
    check_out: a.check_out || '',
    notes: a.notes || '',
  }
  editingAccId.value = a.id
  accError.value = ''
  showAccForm.value = true
}

function closeAccForm() {
  showAccForm.value = false
  editingAccId.value = null
}

async function saveAcc() {
  accError.value = ''
  const a = accForm.value
  const payload = {
    name: a.name,
    address: a.address,
    beds: a.beds === '' ? null : a.beds,
    link: a.link,
    image_url: a.image_url,
    check_in: a.check_in || null,
    check_out: a.check_out || null,
    notes: a.notes,
  }
  try {
    if (editingAccId.value) {
      await store.updateAccommodation(props.id, editingAccId.value, payload)
    } else {
      await store.createAccommodation(props.id, payload)
    }
    closeAccForm()
    accommodations.value = await store.fetchAccommodations(props.id)
  } catch (e) {
    const d = e.response?.data
    accError.value = d?.link?.[0] || d?.name?.[0] || d?.detail || 'Could not save accommodation.'
  }
}

async function removeAcc(accId) {
  if (!confirm('Delete this accommodation?')) return
  await store.deleteAccommodation(props.id, accId)
  accommodations.value = await store.fetchAccommodations(props.id)
}

async function deleteTrip() {
  if (!confirm('Delete this entire trip? This cannot be undone.')) return
  await store.deleteTrip(props.id)
  router.push({ name: 'trips' })
}

function mapsUrl(address) {
  // Universal Google Maps search URL; on mobile this hands off to the maps app.
  return `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(address)}`
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

function flightLabel(f) {
  const airline = [f.airline, f.flight_number].filter(Boolean).join(' ')
  const route =
    f.departure_airport && f.arrival_airport
      ? `${f.departure_airport}→${f.arrival_airport}`
      : ''
  const when = f.departure_time ? fmt(f.departure_time) : ''
  return [airline, route, when].filter(Boolean).join(' · ') || 'flight added'
}
</script>

<template>
  <div v-if="loading" class="text-stone-500">Loading…</div>
  <div v-else-if="trip" class="space-y-8">
    <!-- Header -->
    <div v-if="!editing" class="flex items-start justify-between gap-3">
      <div>
        <h1 class="text-2xl font-semibold">{{ trip.name }}</h1>
        <p v-if="trip.destination" class="text-stone-600">📍 {{ trip.destination }}</p>
        <p v-if="trip.start_date" class="text-sm text-stone-500">
          {{ trip.start_date }} <span v-if="trip.end_date">→ {{ trip.end_date }}</span>
        </p>
        <p v-if="trip.description" class="mt-2 max-w-prose text-sm text-stone-700">
          {{ trip.description }}
        </p>
      </div>
      <div class="flex shrink-0 flex-col items-end gap-2">
        <button class="btn-icon" aria-label="Edit trip" title="Edit trip" @click="startEdit">
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="h-5 w-5">
            <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
          </svg>
        </button>
        <button
          v-if="isOwner"
          class="btn-icon-danger"
          aria-label="Delete trip"
          title="Delete trip"
          @click="deleteTrip"
        >
          ×
        </button>
      </div>
    </div>

    <!-- Edit form -->
    <div v-else class="card">
      <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveEdit">
        <div class="sm:col-span-2">
          <label class="label">Trip name</label>
          <input v-model="editForm.name" class="input" required />
        </div>
        <div class="sm:col-span-2">
          <label class="label">Destination</label>
          <input v-model="editForm.destination" class="input" />
        </div>
        <div>
          <label class="label">Start date</label>
          <input v-model="editForm.start_date" type="date" class="input" />
        </div>
        <div>
          <label class="label">End date</label>
          <input v-model="editForm.end_date" type="date" class="input" />
        </div>
        <div class="sm:col-span-2">
          <label class="label">Description</label>
          <textarea v-model="editForm.description" rows="3" class="input"></textarea>
        </div>
        <p v-if="editError" class="text-sm text-clay-600 sm:col-span-2">{{ editError }}</p>
        <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row">
          <button type="submit" class="btn-primary">Save changes</button>
          <button type="button" class="btn-secondary" @click="editing = false">Cancel</button>
        </div>
      </form>
    </div>

    <!-- Members -->
    <section class="space-y-3">
      <h2 class="text-lg font-medium">Members</h2>
      <ul class="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white">
        <li v-for="m in members" :key="m.id" class="flex items-start justify-between gap-2 px-4 py-2">
          <div>
            <div class="text-sm">
              {{ m.user.name }} <span class="text-stone-400">({{ m.user.email }})</span>
              <span class="ml-1 rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">{{ m.role }}</span>
            </div>
            <div
              v-if="m.user.dietary_restrictions?.length"
              class="mt-1 flex flex-wrap gap-1"
            >
              <span
                v-for="(d, i) in m.user.dietary_restrictions"
                :key="i"
                class="rounded-full bg-clay-50 px-2 py-0.5 text-xs text-clay-700"
              >
                {{ d }}
              </span>
            </div>
          </div>
          <button
            v-if="isOwner || m.user.id === auth.user?.id"
            class="btn-icon-danger"
            aria-label="Remove member"
            title="Remove member"
            @click="removeMember(m.user.id)"
          >
            ×
          </button>
        </li>
      </ul>

      <ul v-if="pendingInvites.length" class="space-y-1 text-sm text-stone-500">
        <li v-for="inv in pendingInvites" :key="inv.id">⏳ Invited: {{ inv.email }} (pending)</li>
      </ul>

      <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="invite">
        <input v-model="inviteEmail" type="email" class="input" placeholder="friend@example.com" required />
        <button type="submit" class="btn-primary whitespace-nowrap">Add member</button>
      </form>
      <p v-if="inviteMsg" class="text-sm text-stone-600">{{ inviteMsg }}</p>
    </section>

    <!-- Accommodations -->
    <section class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Accommodations</h2>
        <button class="btn-secondary" @click="showAccForm ? closeAccForm() : openAddAcc()">
          {{ showAccForm ? 'Cancel' : 'Add place' }}
        </button>
      </div>

      <div v-if="showAccForm" class="card">
        <h3 class="mb-4 font-medium">
          {{ editingAccId ? 'Edit accommodation' : 'Add accommodation' }}
        </h3>
        <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveAcc">
          <div class="sm:col-span-2">
            <label class="label">Name</label>
            <input v-model="accForm.name" class="input" required placeholder="Lakeside Cabin" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Address</label>
            <input v-model="accForm.address" class="input" placeholder="123 Pine Rd, Estes Park, CO" />
          </div>
          <div>
            <label class="label">Beds</label>
            <input v-model.number="accForm.beds" type="number" min="0" class="input" placeholder="4" />
          </div>
          <div>
            <label class="label">Listing link</label>
            <input v-model="accForm.link" type="url" class="input" placeholder="https://airbnb.com/…" />
          </div>
          <div>
            <label class="label">Check-in</label>
            <input v-model="accForm.check_in" type="date" class="input" />
          </div>
          <div>
            <label class="label">Check-out</label>
            <input v-model="accForm.check_out" type="date" class="input" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Photo URL (optional)</label>
            <input
              v-model="accForm.image_url"
              type="url"
              class="input"
              placeholder="Auto-filled from the link when possible"
            />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Notes</label>
            <textarea v-model="accForm.notes" rows="2" class="input"></textarea>
          </div>
          <p v-if="accError" class="text-sm text-clay-600 sm:col-span-2">{{ accError }}</p>
          <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row">
            <button type="submit" class="btn-primary">
              {{ editingAccId ? 'Save changes' : 'Add accommodation' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeAccForm">Cancel</button>
          </div>
        </form>
      </div>

      <p v-if="!accommodations.length" class="text-stone-500">No accommodations added yet.</p>
      <ul v-else class="space-y-3">
        <li v-for="a in accommodations" :key="a.id" class="card">
          <div class="flex items-start justify-between gap-3">
            <div class="flex min-w-0 gap-3">
              <img
                v-if="a.image_url"
                :src="a.image_url"
                alt=""
                class="h-16 w-16 shrink-0 rounded-md object-cover sm:h-20 sm:w-20"
                @error="$event.target.style.display = 'none'"
              />
              <div class="min-w-0">
              <p class="font-medium">{{ a.name }}</p>
              <a
                v-if="a.address"
                :href="mapsUrl(a.address)"
                target="_blank"
                rel="noopener"
                class="block text-sm text-forest-600 hover:underline"
                >📍 {{ a.address }} <span class="text-stone-400">(open in maps ↗)</span></a
              >
              <p v-if="a.check_in || a.check_out" class="text-sm text-stone-500">
                {{ a.check_in || '?' }} → {{ a.check_out || '?' }}
              </p>
              <p class="mt-1 flex flex-wrap items-center gap-x-3 text-sm text-stone-500">
                <span v-if="a.beds != null">🛏️ {{ a.beds }} bed(s)</span>
                <a
                  v-if="a.link"
                  :href="a.link"
                  target="_blank"
                  rel="noopener"
                  class="text-forest-600 hover:underline"
                  >View listing ↗</a
                >
              </p>
              <p v-if="a.notes" class="mt-1 text-sm text-stone-500">{{ a.notes }}</p>
              </div>
            </div>
            <div class="flex shrink-0 flex-col items-end gap-2">
              <button class="btn-icon" aria-label="Edit accommodation" title="Edit accommodation" @click="openEditAcc(a)">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="h-5 w-5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                </svg>
              </button>
              <button
                class="btn-icon-danger"
                aria-label="Delete accommodation"
                title="Delete accommodation"
                @click="removeAcc(a.id)"
              >
                ×
              </button>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <!-- Flights -->
    <section class="space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Flights</h2>
        <button class="btn-secondary" @click="showFlightForm ? closeFlightForm() : openAddFlight()">
          {{ showFlightForm ? 'Cancel' : 'Add flight' }}
        </button>
      </div>

      <div v-if="showFlightForm" class="card">
        <h3 class="mb-4 font-medium">{{ editingFlightId ? 'Edit flight' : 'Add flight' }}</h3>
        <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveFlight">
          <div class="sm:col-span-2">
            <label class="label">Type</label>
            <div class="flex gap-2">
              <label
                v-for="opt in [
                  { v: 'arrival', label: 'Arrival' },
                  { v: 'departure', label: 'Departure' },
                ]"
                :key="opt.v"
                class="flex min-h-[44px] flex-1 cursor-pointer items-center justify-center rounded-md border text-sm"
                :class="
                  flightForm.direction === opt.v
                    ? 'border-forest-500 bg-forest-50 font-medium text-forest-800'
                    : 'border-stone-300 text-stone-600'
                "
              >
                <input v-model="flightForm.direction" type="radio" class="sr-only" :value="opt.v" />
                {{ opt.label }}
              </label>
            </div>
          </div>
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
            <AirportPicker v-model="flightForm.departure_airport" />
          </div>
          <div>
            <label class="label">To (airport)</label>
            <AirportPicker v-model="flightForm.arrival_airport" />
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
            <div class="space-y-2">
              <div
                v-for="row in travelerRows"
                :key="row.userId"
                class="rounded-md border border-stone-200 p-2"
              >
                <label class="flex min-h-[36px] cursor-pointer items-center gap-2 text-sm">
                  <input type="checkbox" class="h-4 w-4" v-model="row.selected" />
                  {{ row.name }}
                </label>
                <div v-if="row.selected" class="mt-2 grid grid-cols-2 gap-2">
                  <input v-model="row.confirmation_code" class="input" placeholder="Confirmation #" />
                  <input v-model="row.seat" class="input" placeholder="Seat" />
                </div>
              </div>
            </div>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Notes</label>
            <input v-model="flightForm.notes" class="input" />
          </div>
          <p v-if="flightError" class="text-sm text-clay-600 sm:col-span-2">{{ flightError }}</p>
          <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row">
            <button type="submit" class="btn-primary">
              {{ editingFlightId ? 'Save changes' : 'Add flight' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeFlightForm">Cancel</button>
          </div>
        </form>
      </div>

      <div v-if="flights.length" class="card">
        <h3 class="mb-3 font-medium">Who's flying when</h3>
        <ul class="space-y-3">
          <li v-for="p in flightSummary" :key="p.userId">
            <p class="text-sm font-medium">{{ p.name }}</p>
            <div class="mt-0.5 space-y-0.5 text-sm text-stone-600">
              <p>
                <span class="text-stone-400">Arrival:</span>
                <span v-if="p.arrivals.length"> {{ p.arrivals.map(flightLabel).join('; ') }}</span>
                <span v-else class="text-stone-400"> —</span>
              </p>
              <p>
                <span class="text-stone-400">Departure:</span>
                <span v-if="p.departures.length"> {{ p.departures.map(flightLabel).join('; ') }}</span>
                <span v-else class="text-stone-400"> —</span>
              </p>
            </div>
          </li>
        </ul>
      </div>

      <p v-if="!flights.length" class="text-stone-500">No flights added yet.</p>
      <div v-else class="space-y-5">
        <div v-for="group in flightGroups" :key="group.key">
          <h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
            {{ group.label }}
          </h3>
          <ul class="space-y-3">
            <li v-for="f in group.flights" :key="f.id" class="card">
          <div class="flex items-start justify-between">
            <div>
              <p class="font-medium">
                {{ f.airline }} {{ f.flight_number }}
                <span class="text-stone-500">{{ f.departure_airport }} → {{ f.arrival_airport }}</span>
              </p>
              <p class="text-sm text-stone-600">
                Departs {{ fmt(f.departure_time) }} · Arrives {{ fmt(f.arrival_time) }}
              </p>
              <p v-if="f.notes" class="mt-1 text-sm text-stone-500">{{ f.notes }}</p>
              <div class="mt-2 flex flex-wrap gap-2">
                <span
                  v-for="t in f.travelers"
                  :key="t.id"
                  class="rounded-full bg-forest-50 px-2 py-0.5 text-xs text-forest-700"
                >
                  {{ t.user_detail.name }}<span v-if="t.seat"> · {{ t.seat }}</span>
                </span>
              </div>
            </div>
            <div class="flex shrink-0 flex-col items-end gap-2">
              <button class="btn-icon" aria-label="Edit flight" title="Edit flight" @click="openEditFlight(f)">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="h-5 w-5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                </svg>
              </button>
              <button
                class="btn-icon-danger"
                aria-label="Delete flight"
                title="Delete flight"
                @click="removeFlight(f.id)"
              >
                ×
              </button>
            </div>
          </div>
            </li>
          </ul>
        </div>
      </div>
    </section>
  </div>
</template>
