<script setup>
import { ref, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { useTripsStore } from '../stores/trips'
import { useAuthStore } from '../stores/auth'
import AirportPicker from '../components/AirportPicker.vue'
import ClampText from '../components/ClampText.vue'
import Accordion from '../components/Accordion.vue'
import yhoshuaImg from '../assets/yhoshua.jpeg'

const props = defineProps({ id: { type: [String, Number], required: true } })
const store = useTripsStore()
const auth = useAuthStore()
const router = useRouter()

const trip = ref(null)
const members = ref([])
const pendingInvites = ref([])
const flights = ref([])
const accommodations = ref([])
const rentals = ref([])
const itinerary = ref([])
const pois = ref([])
const meals = ref([])
const grocery = ref([])
const loading = ref(true)
const notice = ref('')

const isOwner = computed(() => trip.value?.my_role === 'owner')

// Reveal a card/row's action buttons on tap (mobile). Desktop uses CSS hover.
// Only one card is "open" at a time; taps on links/buttons inside are ignored.
const activeTab = ref('logistics')
const TABS = [
  { k: 'logistics', label: 'Logistics' },
  { k: 'activities', label: 'Activities' },
  { k: 'yhoshua', label: "Picture of Y'hoshua" },
]

const activeCard = ref(null)
function toggleCard(key, event) {
  if (event.target.closest('a, button, input, textarea, label, select')) return
  activeCard.value = activeCard.value === key ? null : key
}

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
    rentals.value = await store.fetchRentals(props.id)
    itinerary.value = await store.fetchItinerary(props.id)
    pois.value = await store.fetchPois(props.id)
    meals.value = await store.fetchMeals(props.id)
    grocery.value = await store.fetchGrocery(props.id)
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

async function cancelInvite(inviteId) {
  if (!confirm('Cancel this invitation?')) return
  await store.cancelInvitation(props.id, inviteId)
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

// --- rental vehicles ---
const showRentalForm = ref(false)
const editingRentalId = ref(null)
const rentalError = ref('')
const rentalForm = ref(blankRentalForm())

function blankRentalForm() {
  return {
    rented_by: '',
    company: '',
    vehicle: '',
    confirmation_code: '',
    pickup_location: '',
    dropoff_location: '',
    pickup_time: '',
    dropoff_time: '',
    link: '',
    notes: '',
  }
}

function openAddRental() {
  rentalForm.value = blankRentalForm()
  editingRentalId.value = null
  rentalError.value = ''
  showRentalForm.value = true
}

function openEditRental(r) {
  rentalForm.value = {
    rented_by: r.rented_by ?? '',
    company: r.company || '',
    vehicle: r.vehicle || '',
    confirmation_code: r.confirmation_code || '',
    pickup_location: r.pickup_location || '',
    dropoff_location: r.dropoff_location || '',
    pickup_time: toLocalInput(r.pickup_time),
    dropoff_time: toLocalInput(r.dropoff_time),
    link: r.link || '',
    notes: r.notes || '',
  }
  editingRentalId.value = r.id
  rentalError.value = ''
  showRentalForm.value = true
}

function closeRentalForm() {
  showRentalForm.value = false
  editingRentalId.value = null
}

async function saveRental() {
  rentalError.value = ''
  const f = rentalForm.value
  const payload = {
    rented_by: f.rented_by || null,
    company: f.company,
    vehicle: f.vehicle,
    confirmation_code: f.confirmation_code,
    pickup_location: f.pickup_location,
    dropoff_location: f.dropoff_location,
    pickup_time: f.pickup_time ? new Date(f.pickup_time).toISOString() : null,
    dropoff_time: f.dropoff_time ? new Date(f.dropoff_time).toISOString() : null,
    link: f.link,
    notes: f.notes,
  }
  try {
    if (editingRentalId.value) {
      await store.updateRental(props.id, editingRentalId.value, payload)
    } else {
      await store.createRental(props.id, payload)
    }
    closeRentalForm()
    rentals.value = await store.fetchRentals(props.id)
  } catch (e) {
    rentalError.value = e.response?.data?.detail || 'Could not save rental.'
  }
}

async function removeRental(rentalId) {
  if (!confirm('Delete this rental?')) return
  await store.deleteRental(props.id, rentalId)
  rentals.value = await store.fetchRentals(props.id)
}

// --- itinerary ---
const showItinForm = ref(false)
const editingItinId = ref(null)
const itinError = ref('')
const itinForm = ref(blankItinForm())

function blankItinForm() {
  return { title: '', day: '', start_time: '', end_time: '', location: '', link: '', notes: '' }
}

// Backend returns items ordered by (day, start_time) with nulls last, so
// grouping in that order yields days ascending with Unscheduled last.
const itineraryByDay = computed(() => {
  const groups = []
  const byKey = new Map()
  for (const it of itinerary.value) {
    const key = it.day || 'unscheduled'
    if (!byKey.has(key)) {
      const g = { key, day: it.day || null, items: [] }
      byKey.set(key, g)
      groups.push(g)
    }
    byKey.get(key).items.push(it)
  }
  return groups
})

function openAddItin() {
  itinForm.value = blankItinForm()
  itinForm.value.day = trip.value?.start_date || ''
  editingItinId.value = null
  itinError.value = ''
  showItinForm.value = true
}

function openEditItin(it) {
  itinForm.value = {
    title: it.title || '',
    day: it.day || '',
    start_time: (it.start_time || '').slice(0, 5),
    end_time: (it.end_time || '').slice(0, 5),
    location: it.location || '',
    link: it.link || '',
    notes: it.notes || '',
  }
  editingItinId.value = it.id
  itinError.value = ''
  showItinForm.value = true
}

function closeItinForm() {
  showItinForm.value = false
  editingItinId.value = null
}

async function saveItin() {
  itinError.value = ''
  const f = itinForm.value
  const payload = {
    title: f.title,
    day: f.day || null,
    start_time: f.start_time || null,
    end_time: f.end_time || null,
    location: f.location,
    link: f.link,
    notes: f.notes,
  }
  try {
    if (editingItinId.value) {
      await store.updateItineraryItem(props.id, editingItinId.value, payload)
    } else {
      await store.createItineraryItem(props.id, payload)
    }
    closeItinForm()
    itinerary.value = await store.fetchItinerary(props.id)
  } catch (e) {
    const d = e.response?.data
    itinError.value = d?.title?.[0] || d?.detail || 'Could not save item.'
  }
}

async function removeItin(itemId) {
  if (!confirm('Delete this itinerary item?')) return
  await store.deleteItineraryItem(props.id, itemId)
  itinerary.value = await store.fetchItinerary(props.id)
}

function fmtDay(iso) {
  if (!iso) return 'Unscheduled'
  const [y, m, d] = iso.split('-').map(Number)
  return new Date(y, m - 1, d).toLocaleDateString([], {
    weekday: 'short',
    month: 'short',
    day: 'numeric',
  })
}
function fmtTime(t) {
  if (!t) return ''
  const [h, m] = t.split(':').map(Number)
  return new Date(2000, 0, 1, h, m).toLocaleTimeString([], { hour: 'numeric', minute: '2-digit' })
}
function itinTimeRange(it) {
  const s = fmtTime(it.start_time)
  const e = fmtTime(it.end_time)
  if (s && e) return `${s} – ${e}`
  return s || e || ''
}

// --- points of interest ---
const POI_CATEGORIES = [
  { v: 'restaurant', label: 'Restaurant' },
  { v: 'shopping', label: 'Shopping' },
  { v: 'activity', label: 'Activity' },
  { v: 'sightseeing', label: 'Sightseeing' },
  { v: 'outdoors', label: 'Outdoors' },
  { v: 'nightlife', label: 'Nightlife' },
  { v: 'other', label: 'Other' },
]
function poiCategoryLabel(v) {
  return POI_CATEGORIES.find((c) => c.v === v)?.label || v
}

const showPoiForm = ref(false)
const editingPoiId = ref(null)
const poiError = ref('')
const poiForm = ref(blankPoiForm())

function blankPoiForm() {
  return { name: '', category: 'other', address: '', link: '', notes: '' }
}

// Most-wanted spots float to the top.
const poisSorted = computed(() =>
  [...pois.value].sort((a, b) => b.interested_count - a.interested_count),
)

function openAddPoi() {
  poiForm.value = blankPoiForm()
  editingPoiId.value = null
  poiError.value = ''
  showPoiForm.value = true
}

function openEditPoi(p) {
  poiForm.value = {
    name: p.name || '',
    category: p.category || 'other',
    address: p.address || '',
    link: p.link || '',
    notes: p.notes || '',
  }
  editingPoiId.value = p.id
  poiError.value = ''
  showPoiForm.value = true
}

function closePoiForm() {
  showPoiForm.value = false
  editingPoiId.value = null
}

async function savePoi() {
  poiError.value = ''
  try {
    if (editingPoiId.value) {
      await store.updatePoi(props.id, editingPoiId.value, poiForm.value)
    } else {
      await store.createPoi(props.id, poiForm.value)
    }
    closePoiForm()
    pois.value = await store.fetchPois(props.id)
  } catch (e) {
    poiError.value = e.response?.data?.name?.[0] || e.response?.data?.detail || 'Could not save.'
  }
}

async function removePoi(poiId) {
  if (!confirm('Delete this place?')) return
  await store.deletePoi(props.id, poiId)
  pois.value = await store.fetchPois(props.id)
}

async function toggleInterest(poi) {
  const updated = await store.togglePoiInterest(props.id, poi.id)
  const idx = pois.value.findIndex((p) => p.id === poi.id)
  if (idx !== -1) pois.value[idx] = updated
}

// --- meals ---
const showMealForm = ref(false)
const editingMealId = ref(null)
const mealError = ref('')
const mealForm = ref(blankMealForm())
const newIngredient = ref('')

const MEAL_TYPES = [
  { v: 'breakfast', label: 'Breakfast' },
  { v: 'lunch', label: 'Lunch' },
  { v: 'dinner', label: 'Dinner' },
  { v: 'snack', label: 'Snack' },
]
const MEAL_ORDER = { breakfast: 0, lunch: 1, dinner: 2, snack: 3 }

function mealTypeLabel(v) {
  return MEAL_TYPES.find((t) => t.v === v)?.label || v
}

function blankMealForm() {
  return { title: '', day: '', meal_type: 'dinner', cookIds: [], ingredients: [], notes: '' }
}

const mealsByDay = computed(() => {
  const groups = []
  const byKey = new Map()
  for (const m of meals.value) {
    const key = m.day || 'unscheduled'
    if (!byKey.has(key)) {
      const g = { key, day: m.day || null, items: [] }
      byKey.set(key, g)
      groups.push(g)
    }
    byKey.get(key).items.push(m)
  }
  for (const g of groups) {
    g.items.sort((a, b) => (MEAL_ORDER[a.meal_type] ?? 9) - (MEAL_ORDER[b.meal_type] ?? 9))
  }
  return groups
})

// Dietary reference so whoever plans meals can see everyone's needs.
const dietaryNeeds = computed(() =>
  members.value
    .filter((m) => m.user.dietary_restrictions?.length)
    .map((m) => ({ name: m.user.name, items: m.user.dietary_restrictions })),
)

function openAddMeal() {
  mealForm.value = blankMealForm()
  mealForm.value.day = trip.value?.start_date || ''
  newIngredient.value = ''
  editingMealId.value = null
  mealError.value = ''
  showMealForm.value = true
}

function openEditMeal(m) {
  mealForm.value = {
    title: m.title || '',
    day: m.day || '',
    meal_type: m.meal_type || 'dinner',
    cookIds: (m.cooks || []).slice(),
    ingredients: (m.ingredients || []).slice(),
    notes: m.notes || '',
  }
  newIngredient.value = ''
  editingMealId.value = m.id
  mealError.value = ''
  showMealForm.value = true
}

function closeMealForm() {
  showMealForm.value = false
  editingMealId.value = null
}

function addIngredient() {
  const v = newIngredient.value.trim()
  if (v && !mealForm.value.ingredients.includes(v)) mealForm.value.ingredients.push(v)
  newIngredient.value = ''
}
function removeIngredient(i) {
  mealForm.value.ingredients.splice(i, 1)
}

async function saveMeal() {
  mealError.value = ''
  addIngredient() // fold in any half-typed ingredient
  const f = mealForm.value
  const payload = {
    title: f.title,
    day: f.day || null,
    meal_type: f.meal_type,
    cooks: f.cookIds,
    ingredients: f.ingredients,
    notes: f.notes,
  }
  try {
    if (editingMealId.value) {
      await store.updateMeal(props.id, editingMealId.value, payload)
    } else {
      await store.createMeal(props.id, payload)
    }
    closeMealForm()
    meals.value = await store.fetchMeals(props.id)
  } catch (e) {
    const d = e.response?.data
    mealError.value = d?.cooks?.[0] || d?.title?.[0] || d?.detail || 'Could not save meal.'
  }
}

async function removeMeal(mealId) {
  if (!confirm('Delete this meal?')) return
  await store.deleteMeal(props.id, mealId)
  meals.value = await store.fetchMeals(props.id)
}

// --- grocery list ---
const groceryForm = ref({ name: '', quantity: '', category: '' })

// Backend orders by category; keep that order but push Uncategorized last.
const groceryByCategory = computed(() => {
  const groups = []
  const byKey = new Map()
  for (const it of grocery.value) {
    const key = it.category || ''
    if (!byKey.has(key)) {
      const g = { key, label: it.category || 'Uncategorized', items: [] }
      byKey.set(key, g)
      groups.push(g)
    }
    byKey.get(key).items.push(it)
  }
  return groups.sort((a, b) => (a.key === '' ? 1 : b.key === '' ? -1 : 0))
})

const groceryProgress = computed(() => ({
  total: grocery.value.length,
  done: grocery.value.filter((i) => i.is_checked).length,
}))

async function addGrocery() {
  const name = groceryForm.value.name.trim()
  if (!name) return
  await store.createGroceryItem(props.id, {
    name,
    quantity: groceryForm.value.quantity.trim(),
    category: groceryForm.value.category.trim(),
  })
  groceryForm.value = { name: '', quantity: '', category: '' }
  grocery.value = await store.fetchGrocery(props.id)
}

async function toggleGrocery(item) {
  // item.is_checked is already updated by the checkbox v-model.
  try {
    await store.updateGroceryItem(props.id, item.id, { is_checked: item.is_checked })
  } catch {
    item.is_checked = !item.is_checked // revert on failure
  }
}

async function removeGrocery(itemId) {
  await store.deleteGroceryItem(props.id, itemId)
  grocery.value = await store.fetchGrocery(props.id)
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
    <section class="panel">
      <Accordion title="Members" :count="members.length">
        <div class="space-y-3">
      <ul class="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white">
        <li
          v-for="m in members"
          :key="m.id"
          class="group flex items-start justify-between gap-2 px-4 py-2"
          @click="toggleCard('member:' + m.id, $event)"
        >
          <div>
            <div class="text-sm">
              {{ m.user.name }}
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
            class="btn-icon-danger card-actions"
            :class="{ 'is-revealed': activeCard === 'member:' + m.id }"
            aria-label="Remove member"
            title="Remove member"
            @click="removeMember(m.user.id)"
          >
            ×
          </button>
        </li>
      </ul>

      <ul v-if="pendingInvites.length" class="space-y-1 text-sm text-stone-500">
        <li
          v-for="inv in pendingInvites"
          :key="inv.id"
          class="group flex items-center justify-between gap-2"
          @click="toggleCard('invite:' + inv.id, $event)"
        >
          <span>⏳ Invited: {{ inv.email }} (pending)</span>
          <button
            class="btn-icon-danger card-actions"
            :class="{ 'is-revealed': activeCard === 'invite:' + inv.id }"
            aria-label="Cancel invitation"
            title="Cancel invitation"
            @click="cancelInvite(inv.id)"
          >
            ×
          </button>
        </li>
      </ul>

      <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="invite">
        <input v-model="inviteEmail" type="email" class="input" placeholder="friend@example.com" required />
        <button type="submit" class="btn-primary whitespace-nowrap">Add member</button>
      </form>
      <p v-if="inviteMsg" class="text-sm text-stone-600">{{ inviteMsg }}</p>
        </div>
      </Accordion>
    </section>

    <!-- Section tabs -->
    <div class="flex gap-4 overflow-x-auto overflow-y-hidden border-b border-stone-200">
      <button
        v-for="tab in TABS"
        :key="tab.k"
        class="-mb-px whitespace-nowrap border-b-2 px-1 py-3 text-sm font-medium transition"
        :class="
          activeTab === tab.k
            ? 'border-forest-600 text-forest-700'
            : 'border-transparent text-stone-500 hover:text-stone-700'
        "
        @click="activeTab = tab.k"
      >
        {{ tab.label }}
      </button>
    </div>

    <!-- Activities -->
    <div v-show="activeTab === 'activities'" class="space-y-8">
    <!-- Itinerary -->
    <section class="panel space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Itinerary</h2>
        <button class="btn-secondary" @click="showItinForm ? closeItinForm() : openAddItin()">
          {{ showItinForm ? 'Cancel' : 'Add item' }}
        </button>
      </div>

      <div v-if="showItinForm" class="card">
        <h3 class="mb-4 font-medium">{{ editingItinId ? 'Edit item' : 'Add item' }}</h3>
        <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveItin">
          <div class="sm:col-span-2">
            <label class="label">Title</label>
            <input v-model="itinForm.title" class="input" required placeholder="Sunrise hike to Delicate Arch" />
          </div>
          <div>
            <label class="label">Day</label>
            <input v-model="itinForm.day" type="date" class="input" />
          </div>
          <div class="grid grid-cols-2 gap-2">
            <div>
              <label class="label">Start</label>
              <input v-model="itinForm.start_time" type="time" class="input" />
            </div>
            <div>
              <label class="label">End</label>
              <input v-model="itinForm.end_time" type="time" class="input" />
            </div>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Location</label>
            <input v-model="itinForm.location" class="input" placeholder="Arches National Park, UT" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Link (optional)</label>
            <input v-model="itinForm.link" type="url" class="input" placeholder="https://…" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Notes</label>
            <textarea v-model="itinForm.notes" rows="2" class="input"></textarea>
          </div>
          <p v-if="itinError" class="text-sm text-clay-600 sm:col-span-2">{{ itinError }}</p>
          <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row">
            <button type="submit" class="btn-primary">
              {{ editingItinId ? 'Save changes' : 'Add item' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeItinForm">Cancel</button>
          </div>
        </form>
      </div>

      <p v-if="!itinerary.length" class="text-stone-500">Nothing planned yet.</p>
      <div v-else class="space-y-5">
        <div v-for="group in itineraryByDay" :key="group.key">
          <h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
            {{ fmtDay(group.day) }}
          </h3>
          <ul class="space-y-3">
            <li
              v-for="it in group.items"
              :key="it.id"
              class="card group"
              @click="toggleCard('itin:' + it.id, $event)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p v-if="itinTimeRange(it)" class="text-xs font-medium text-forest-700">
                    {{ itinTimeRange(it) }}
                  </p>
                  <p class="font-medium">{{ it.title }}</p>
                  <a
                    v-if="it.location"
                    :href="mapsUrl(it.location)"
                    target="_blank"
                    rel="noopener"
                    class="block text-sm text-forest-600 hover:underline"
                    >📍 {{ it.location }} <span class="text-stone-400">(open in maps ↗)</span></a
                  >
                  <a
                    v-if="it.link"
                    :href="it.link"
                    target="_blank"
                    rel="noopener"
                    class="block text-sm text-forest-600 hover:underline"
                    >View link ↗</a
                  >
                  <ClampText v-if="it.notes" :text="it.notes" class="mt-1" />
                </div>
                <div
                  class="card-actions flex shrink-0 flex-col items-end gap-2"
                  :class="{ 'is-revealed': activeCard === 'itin:' + it.id }"
                >
                  <button class="btn-icon" aria-label="Edit item" title="Edit item" @click="openEditItin(it)">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="h-5 w-5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                    </svg>
                  </button>
                  <button class="btn-icon-danger" aria-label="Delete item" title="Delete item" @click="removeItin(it.id)">×</button>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Places of interest -->
    <section class="panel space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Places of interest</h2>
        <button class="btn-secondary" @click="showPoiForm ? closePoiForm() : openAddPoi()">
          {{ showPoiForm ? 'Cancel' : 'Add place' }}
        </button>
      </div>

      <div v-if="showPoiForm" class="card">
        <h3 class="mb-4 font-medium">{{ editingPoiId ? 'Edit place' : 'Add place' }}</h3>
        <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="savePoi">
          <div>
            <label class="label">Name</label>
            <input v-model="poiForm.name" class="input" required placeholder="Milt's Stop & Eat" />
          </div>
          <div>
            <label class="label">Category</label>
            <select v-model="poiForm.category" class="input">
              <option v-for="c in POI_CATEGORIES" :key="c.v" :value="c.v">{{ c.label }}</option>
            </select>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Address</label>
            <input v-model="poiForm.address" class="input" placeholder="Moab, UT" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Link (optional)</label>
            <input v-model="poiForm.link" type="url" class="input" placeholder="https://…" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Notes</label>
            <textarea v-model="poiForm.notes" rows="2" class="input"></textarea>
          </div>
          <p v-if="poiError" class="text-sm text-clay-600 sm:col-span-2">{{ poiError }}</p>
          <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row">
            <button type="submit" class="btn-primary">
              {{ editingPoiId ? 'Save changes' : 'Add place' }}
            </button>
            <button type="button" class="btn-secondary" @click="closePoiForm">Cancel</button>
          </div>
        </form>
      </div>

      <p v-if="!pois.length" class="text-stone-500">No places added yet.</p>
      <ul v-else class="space-y-3">
        <li
          v-for="p in poisSorted"
          :key="p.id"
          class="card group"
          @click="toggleCard('poi:' + p.id, $event)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <p class="font-medium">{{ p.name }}</p>
                <span class="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600">
                  {{ poiCategoryLabel(p.category) }}
                </span>
              </div>
              <a
                v-if="p.address"
                :href="mapsUrl(p.address)"
                target="_blank"
                rel="noopener"
                class="block text-sm text-forest-600 hover:underline"
                >📍 {{ p.address }} <span class="text-stone-400">(open in maps ↗)</span></a
              >
              <a
                v-if="p.link"
                :href="p.link"
                target="_blank"
                rel="noopener"
                class="block text-sm text-forest-600 hover:underline"
                >View link ↗</a
              >
              <ClampText v-if="p.notes" :text="p.notes" class="mt-1" />
              <div class="mt-2 flex flex-wrap items-center gap-2">
                <button
                  type="button"
                  class="inline-flex min-h-[36px] items-center gap-1 rounded-full px-3 text-sm font-medium transition"
                  :class="
                    p.is_interested
                      ? 'bg-forest-600 text-white hover:bg-forest-500'
                      : 'border border-stone-300 text-stone-600 hover:bg-stone-100'
                  "
                  @click="toggleInterest(p)"
                >
                  {{ p.is_interested ? 'Interested' : "I'm interested" }}
                  <span v-if="p.interested_count">· {{ p.interested_count }}</span>
                </button>
                <span v-if="p.interested_names.length" class="text-xs text-stone-500">
                  {{ p.interested_names.join(', ') }}
                </span>
              </div>
            </div>
            <div
              class="card-actions flex shrink-0 flex-col items-end gap-2"
              :class="{ 'is-revealed': activeCard === 'poi:' + p.id }"
            >
              <button class="btn-icon" aria-label="Edit place" title="Edit place" @click="openEditPoi(p)">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="h-5 w-5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                </svg>
              </button>
              <button class="btn-icon-danger" aria-label="Delete place" title="Delete place" @click="removePoi(p.id)">×</button>
            </div>
          </div>
        </li>
      </ul>
    </section>

    <!-- Meal plan -->
    <section class="panel space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Meal plan</h2>
        <button class="btn-secondary" @click="showMealForm ? closeMealForm() : openAddMeal()">
          {{ showMealForm ? 'Cancel' : 'Add meal' }}
        </button>
      </div>

      <div v-if="dietaryNeeds.length" class="rounded-md border border-clay-200 bg-clay-50 p-3 text-sm">
        <p class="mb-1 font-medium text-clay-700">Dietary needs to plan around</p>
        <ul class="space-y-0.5 text-clay-700">
          <li v-for="d in dietaryNeeds" :key="d.name">
            <span class="font-medium">{{ d.name }}:</span> {{ d.items.join(', ') }}
          </li>
        </ul>
      </div>

      <div v-if="showMealForm" class="card">
        <h3 class="mb-4 font-medium">{{ editingMealId ? 'Edit meal' : 'Add meal' }}</h3>
        <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveMeal">
          <div class="sm:col-span-2">
            <label class="label">Dish</label>
            <input v-model="mealForm.title" class="input" required placeholder="Chili & cornbread" />
          </div>
          <div>
            <label class="label">Day</label>
            <input v-model="mealForm.day" type="date" class="input" />
          </div>
          <div>
            <label class="label">Meal</label>
            <select v-model="mealForm.meal_type" class="input">
              <option v-for="t in MEAL_TYPES" :key="t.v" :value="t.v">{{ t.label }}</option>
            </select>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Cook(s)</label>
            <div class="flex flex-wrap gap-2">
              <label
                v-for="m in members"
                :key="m.id"
                class="flex min-h-[44px] cursor-pointer items-center gap-2 rounded-md border border-stone-200 px-3 text-sm"
              >
                <input type="checkbox" class="h-4 w-4" :value="m.user.id" v-model="mealForm.cookIds" />
                {{ m.user.name }}
              </label>
            </div>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Ingredients</label>
            <div v-if="mealForm.ingredients.length" class="mb-2 flex flex-wrap gap-2">
              <span
                v-for="(ing, i) in mealForm.ingredients"
                :key="i"
                class="inline-flex items-center gap-1 rounded-full bg-stone-100 px-2 py-1 text-sm text-stone-700"
              >
                {{ ing }}
                <button
                  type="button"
                  class="text-stone-500 hover:text-stone-700"
                  aria-label="Remove"
                  @click="removeIngredient(i)"
                >
                  ×
                </button>
              </span>
            </div>
            <div class="flex flex-col gap-2 sm:flex-row">
              <input
                v-model="newIngredient"
                class="input"
                placeholder="e.g. ground beef"
                @keydown.enter.prevent="addIngredient"
              />
              <button type="button" class="btn-secondary whitespace-nowrap" @click="addIngredient">
                Add
              </button>
            </div>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Notes</label>
            <textarea v-model="mealForm.notes" rows="2" class="input"></textarea>
          </div>
          <p v-if="mealError" class="text-sm text-clay-600 sm:col-span-2">{{ mealError }}</p>
          <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row">
            <button type="submit" class="btn-primary">
              {{ editingMealId ? 'Save changes' : 'Add meal' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeMealForm">Cancel</button>
          </div>
        </form>
      </div>

      <p v-if="!meals.length" class="text-stone-500">No meals planned yet.</p>
      <div v-else class="space-y-5">
        <div v-for="group in mealsByDay" :key="group.key">
          <h3 class="mb-2 text-sm font-semibold uppercase tracking-wide text-stone-500">
            {{ fmtDay(group.day) }}
          </h3>
          <ul class="space-y-3">
            <li
              v-for="m in group.items"
              :key="m.id"
              class="card group"
              @click="toggleCard('meal:' + m.id, $event)"
            >
              <div class="flex items-start justify-between gap-3">
                <div class="min-w-0">
                  <p class="text-xs font-medium uppercase tracking-wide text-forest-700">
                    {{ mealTypeLabel(m.meal_type) }}
                  </p>
                  <p class="font-medium">{{ m.title }}</p>
                  <p v-if="m.cook_details.length" class="text-sm text-stone-500">
                    Cook: {{ m.cook_details.map((c) => c.name).join(', ') }}
                  </p>
                  <div v-if="m.ingredients.length" class="mt-1 flex flex-wrap gap-1">
                    <span
                      v-for="(ing, i) in m.ingredients"
                      :key="i"
                      class="rounded-full bg-stone-100 px-2 py-0.5 text-xs text-stone-600"
                    >
                      {{ ing }}
                    </span>
                  </div>
                  <ClampText v-if="m.notes" :text="m.notes" class="mt-1" />
                </div>
                <div
                  class="card-actions flex shrink-0 flex-col items-end gap-2"
                  :class="{ 'is-revealed': activeCard === 'meal:' + m.id }"
                >
                  <button class="btn-icon" aria-label="Edit meal" title="Edit meal" @click="openEditMeal(m)">
                    <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="h-5 w-5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                    </svg>
                  </button>
                  <button class="btn-icon-danger" aria-label="Delete meal" title="Delete meal" @click="removeMeal(m.id)">×</button>
                </div>
              </div>
            </li>
          </ul>
        </div>
      </div>
    </section>

    <!-- Grocery list -->
    <section class="panel space-y-3 border-forest-200 bg-forest-50">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Grocery list</h2>
        <span v-if="groceryProgress.total" class="text-sm text-stone-500">
          {{ groceryProgress.done }} / {{ groceryProgress.total }} got
        </span>
      </div>

      <form class="flex flex-col gap-2 sm:flex-row" @submit.prevent="addGrocery">
        <input v-model="groceryForm.name" class="input sm:flex-1" placeholder="Item (e.g. eggs)" required />
        <input v-model="groceryForm.quantity" class="input sm:w-24" placeholder="Qty" />
        <input v-model="groceryForm.category" class="input sm:w-40" placeholder="Category" />
        <button type="submit" class="btn-primary whitespace-nowrap">Add</button>
      </form>

      <p v-if="!grocery.length" class="text-stone-500">List is empty.</p>
      <div v-else class="space-y-4">
        <div v-for="group in groceryByCategory" :key="group.key">
          <h3 class="mb-1 text-xs font-semibold uppercase tracking-wide text-stone-400">
            {{ group.label }}
          </h3>
          <ul class="divide-y divide-stone-100 rounded-lg border border-stone-200 bg-white">
            <li v-for="item in group.items" :key="item.id" class="flex items-center gap-3 px-3 py-2">
              <label class="flex min-h-[36px] flex-1 cursor-pointer items-center gap-3 text-sm">
                <input
                  type="checkbox"
                  class="h-4 w-4 shrink-0"
                  v-model="item.is_checked"
                  @change="toggleGrocery(item)"
                />
                <span :class="item.is_checked ? 'text-stone-400 line-through' : ''">
                  {{ item.name }}<span v-if="item.quantity" class="text-stone-400"> · {{ item.quantity }}</span>
                </span>
              </label>
              <button
                class="shrink-0 text-lg leading-none text-stone-300 transition hover:text-clay-600"
                aria-label="Delete item"
                title="Delete item"
                @click="removeGrocery(item.id)"
              >
                ×
              </button>
            </li>
          </ul>
        </div>
      </div>
    </section>
    </div>

    <!-- Logistics -->
    <div v-show="activeTab === 'logistics'" class="space-y-8">
    <!-- Accommodations -->
    <section class="panel space-y-3">
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
        <li
          v-for="a in accommodations"
          :key="a.id"
          class="card group"
          @click="toggleCard('acc:' + a.id, $event)"
        >
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
              <ClampText v-if="a.notes" :text="a.notes" class="mt-1" />
              </div>
            </div>
            <div
              class="card-actions flex shrink-0 flex-col items-end gap-2"
              :class="{ 'is-revealed': activeCard === 'acc:' + a.id }"
            >
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
    <section class="panel space-y-3">
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
        <Accordion
          v-for="group in flightGroups"
          :key="group.key"
          :title="group.label"
          title-class="text-sm font-semibold uppercase tracking-wide text-stone-500"
          :count="group.flights.length"
        >
          <ul class="space-y-3">
            <li
              v-for="f in group.flights"
              :key="f.id"
              class="card group"
              @click="toggleCard('flight:' + f.id, $event)"
            >
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
            <div
              class="card-actions flex shrink-0 flex-col items-end gap-2"
              :class="{ 'is-revealed': activeCard === 'flight:' + f.id }"
            >
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
        </Accordion>
      </div>
    </section>

    <!-- Rental vehicles -->
    <section class="panel space-y-3">
      <div class="flex items-center justify-between">
        <h2 class="text-lg font-medium">Rental vehicles</h2>
        <button class="btn-secondary" @click="showRentalForm ? closeRentalForm() : openAddRental()">
          {{ showRentalForm ? 'Cancel' : 'Add rental' }}
        </button>
      </div>

      <div v-if="showRentalForm" class="card">
        <h3 class="mb-4 font-medium">{{ editingRentalId ? 'Edit rental' : 'Add rental' }}</h3>
        <form class="grid gap-4 sm:grid-cols-2" @submit.prevent="saveRental">
          <div>
            <label class="label">Company</label>
            <input v-model="rentalForm.company" class="input" placeholder="Enterprise" />
          </div>
          <div>
            <label class="label">Vehicle</label>
            <input v-model="rentalForm.vehicle" class="input" placeholder="Jeep Wrangler" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Rented by</label>
            <select v-model="rentalForm.rented_by" class="input">
              <option value="">—</option>
              <option v-for="m in members" :key="m.id" :value="m.user.id">{{ m.user.name }}</option>
            </select>
          </div>
          <div class="sm:col-span-2">
            <label class="label">Confirmation #</label>
            <input v-model="rentalForm.confirmation_code" class="input" />
          </div>
          <div>
            <label class="label">Pickup location</label>
            <input v-model="rentalForm.pickup_location" class="input" placeholder="SLC Airport" />
          </div>
          <div>
            <label class="label">Pickup time</label>
            <input v-model="rentalForm.pickup_time" type="datetime-local" class="input" />
          </div>
          <div>
            <label class="label">Drop-off location</label>
            <input v-model="rentalForm.dropoff_location" class="input" />
          </div>
          <div>
            <label class="label">Drop-off time</label>
            <input v-model="rentalForm.dropoff_time" type="datetime-local" class="input" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Reservation link (optional)</label>
            <input v-model="rentalForm.link" type="url" class="input" placeholder="https://…" />
          </div>
          <div class="sm:col-span-2">
            <label class="label">Notes</label>
            <textarea v-model="rentalForm.notes" rows="2" class="input"></textarea>
          </div>
          <p v-if="rentalError" class="text-sm text-clay-600 sm:col-span-2">{{ rentalError }}</p>
          <div class="flex flex-col gap-2 sm:col-span-2 sm:flex-row">
            <button type="submit" class="btn-primary">
              {{ editingRentalId ? 'Save changes' : 'Add rental' }}
            </button>
            <button type="button" class="btn-secondary" @click="closeRentalForm">Cancel</button>
          </div>
        </form>
      </div>

      <p v-if="!rentals.length" class="text-stone-500">No rentals added yet.</p>
      <ul v-else class="space-y-3">
        <li
          v-for="r in rentals"
          :key="r.id"
          class="card group"
          @click="toggleCard('rental:' + r.id, $event)"
        >
          <div class="flex items-start justify-between gap-3">
            <div class="min-w-0">
              <p class="font-medium">
                {{ [r.company, r.vehicle].filter(Boolean).join(' · ') || 'Rental' }}
              </p>
              <p v-if="r.rented_by_detail" class="text-sm text-stone-500">
                Rented by {{ r.rented_by_detail.name }}
              </p>
              <p v-if="r.confirmation_code" class="text-sm text-stone-500">
                Conf: {{ r.confirmation_code }}
              </p>
              <p v-if="r.pickup_location || r.pickup_time" class="text-sm text-stone-600">
                Pickup:
                <a
                  v-if="r.pickup_location"
                  :href="mapsUrl(r.pickup_location)"
                  target="_blank"
                  rel="noopener"
                  class="text-forest-600 hover:underline"
                  >{{ r.pickup_location }}</a
                ><span v-if="r.pickup_time"> · {{ fmt(r.pickup_time) }}</span>
              </p>
              <p v-if="r.dropoff_location || r.dropoff_time" class="text-sm text-stone-600">
                Drop-off:
                <a
                  v-if="r.dropoff_location"
                  :href="mapsUrl(r.dropoff_location)"
                  target="_blank"
                  rel="noopener"
                  class="text-forest-600 hover:underline"
                  >{{ r.dropoff_location }}</a
                ><span v-if="r.dropoff_time"> · {{ fmt(r.dropoff_time) }}</span>
              </p>
              <a
                v-if="r.link"
                :href="r.link"
                target="_blank"
                rel="noopener"
                class="block text-sm text-forest-600 hover:underline"
                >Reservation ↗</a
              >
              <ClampText v-if="r.notes" :text="r.notes" class="mt-1" />
            </div>
            <div
              class="card-actions flex shrink-0 flex-col items-end gap-2"
              :class="{ 'is-revealed': activeCard === 'rental:' + r.id }"
            >
              <button class="btn-icon" aria-label="Edit rental" title="Edit rental" @click="openEditRental(r)">
                <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor" class="h-5 w-5">
                  <path stroke-linecap="round" stroke-linejoin="round" d="m16.862 4.487 1.687-1.688a1.875 1.875 0 1 1 2.652 2.652L10.582 16.07a4.5 4.5 0 0 1-1.897 1.13L6 18l.8-2.685a4.5 4.5 0 0 1 1.13-1.897l8.932-8.931Zm0 0L19.5 7.125M18 14v4.75A2.25 2.25 0 0 1 15.75 21H5.25A2.25 2.25 0 0 1 3 18.75V8.25A2.25 2.25 0 0 1 5.25 6H10" />
                </svg>
              </button>
              <button class="btn-icon-danger" aria-label="Delete rental" title="Delete rental" @click="removeRental(r.id)">×</button>
            </div>
          </div>
        </li>
      </ul>
    </section>
    </div>

    <!-- Picture of Y'hoshua -->
    <Transition name="fade" appear>
      <img
        v-if="activeTab === 'yhoshua'"
        :src="yhoshuaImg"
        alt="Y'hoshua"
        class="mx-auto max-h-[70vh] w-auto rounded-lg shadow-sm"
      />
    </Transition>
  </div>
</template>
