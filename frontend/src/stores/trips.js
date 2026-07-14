import { defineStore } from 'pinia'
import { ref } from 'vue'
import client from '../api/client'

export const useTripsStore = defineStore('trips', () => {
  const trips = ref([])
  const loading = ref(false)

  async function fetchTrips() {
    loading.value = true
    try {
      const { data } = await client.get('/trips/')
      // DRF pagination is off by default; handle both shapes just in case.
      trips.value = Array.isArray(data) ? data : data.results
    } finally {
      loading.value = false
    }
  }

  async function createTrip(payload) {
    const { data } = await client.post('/trips/', payload)
    return data
  }

  async function fetchTrip(id) {
    const { data } = await client.get(`/trips/${id}/`)
    return data
  }

  async function updateTrip(id, payload) {
    const { data } = await client.patch(`/trips/${id}/`, payload)
    return data
  }

  async function deleteTrip(id) {
    await client.delete(`/trips/${id}/`)
  }

  // --- members ---
  async function fetchMembers(tripId) {
    const { data } = await client.get(`/trips/${tripId}/members/`)
    return data
  }

  async function addMember(tripId, email) {
    const { data } = await client.post(`/trips/${tripId}/members/`, { email })
    return data
  }

  async function removeMember(tripId, userId) {
    await client.delete(`/trips/${tripId}/members/${userId}/`)
  }

  async function cancelInvitation(tripId, inviteId) {
    await client.delete(`/trips/${tripId}/invitations/${inviteId}/`)
  }

  // --- flights ---
  async function fetchFlights(tripId) {
    const { data } = await client.get(`/trips/${tripId}/flights/`)
    return Array.isArray(data) ? data : data.results
  }

  async function createFlight(tripId, payload) {
    const { data } = await client.post(`/trips/${tripId}/flights/`, payload)
    return data
  }

  async function updateFlight(tripId, flightId, payload) {
    const { data } = await client.patch(`/trips/${tripId}/flights/${flightId}/`, payload)
    return data
  }

  async function deleteFlight(tripId, flightId) {
    await client.delete(`/trips/${tripId}/flights/${flightId}/`)
  }

  // --- accommodations ---
  async function fetchAccommodations(tripId) {
    const { data } = await client.get(`/trips/${tripId}/accommodations/`)
    return Array.isArray(data) ? data : data.results
  }

  async function createAccommodation(tripId, payload) {
    const { data } = await client.post(`/trips/${tripId}/accommodations/`, payload)
    return data
  }

  async function updateAccommodation(tripId, accId, payload) {
    const { data } = await client.patch(`/trips/${tripId}/accommodations/${accId}/`, payload)
    return data
  }

  async function deleteAccommodation(tripId, accId) {
    await client.delete(`/trips/${tripId}/accommodations/${accId}/`)
  }

  // --- itinerary ---
  async function fetchItinerary(tripId) {
    const { data } = await client.get(`/trips/${tripId}/itinerary/`)
    return Array.isArray(data) ? data : data.results
  }

  async function createItineraryItem(tripId, payload) {
    const { data } = await client.post(`/trips/${tripId}/itinerary/`, payload)
    return data
  }

  async function updateItineraryItem(tripId, itemId, payload) {
    const { data } = await client.patch(`/trips/${tripId}/itinerary/${itemId}/`, payload)
    return data
  }

  async function deleteItineraryItem(tripId, itemId) {
    await client.delete(`/trips/${tripId}/itinerary/${itemId}/`)
  }

  // --- meals ---
  async function fetchMeals(tripId) {
    const { data } = await client.get(`/trips/${tripId}/meals/`)
    return Array.isArray(data) ? data : data.results
  }

  async function createMeal(tripId, payload) {
    const { data } = await client.post(`/trips/${tripId}/meals/`, payload)
    return data
  }

  async function updateMeal(tripId, mealId, payload) {
    const { data } = await client.patch(`/trips/${tripId}/meals/${mealId}/`, payload)
    return data
  }

  async function deleteMeal(tripId, mealId) {
    await client.delete(`/trips/${tripId}/meals/${mealId}/`)
  }

  // --- rental vehicles ---
  async function fetchRentals(tripId) {
    const { data } = await client.get(`/trips/${tripId}/rentals/`)
    return Array.isArray(data) ? data : data.results
  }

  async function createRental(tripId, payload) {
    const { data } = await client.post(`/trips/${tripId}/rentals/`, payload)
    return data
  }

  async function updateRental(tripId, rentalId, payload) {
    const { data } = await client.patch(`/trips/${tripId}/rentals/${rentalId}/`, payload)
    return data
  }

  async function deleteRental(tripId, rentalId) {
    await client.delete(`/trips/${tripId}/rentals/${rentalId}/`)
  }

  // --- grocery list ---
  async function fetchGrocery(tripId) {
    const { data } = await client.get(`/trips/${tripId}/grocery/`)
    return Array.isArray(data) ? data : data.results
  }

  async function createGroceryItem(tripId, payload) {
    const { data } = await client.post(`/trips/${tripId}/grocery/`, payload)
    return data
  }

  async function updateGroceryItem(tripId, itemId, payload) {
    const { data } = await client.patch(`/trips/${tripId}/grocery/${itemId}/`, payload)
    return data
  }

  async function deleteGroceryItem(tripId, itemId) {
    await client.delete(`/trips/${tripId}/grocery/${itemId}/`)
  }

  // --- points of interest ---
  async function fetchPois(tripId) {
    const { data } = await client.get(`/trips/${tripId}/pois/`)
    return Array.isArray(data) ? data : data.results
  }

  async function createPoi(tripId, payload) {
    const { data } = await client.post(`/trips/${tripId}/pois/`, payload)
    return data
  }

  async function updatePoi(tripId, poiId, payload) {
    const { data } = await client.patch(`/trips/${tripId}/pois/${poiId}/`, payload)
    return data
  }

  async function deletePoi(tripId, poiId) {
    await client.delete(`/trips/${tripId}/pois/${poiId}/`)
  }

  async function togglePoiInterest(tripId, poiId) {
    const { data } = await client.post(`/trips/${tripId}/pois/${poiId}/toggle_interest/`)
    return data
  }

  // --- points of interest: comments (read via the nested POI list) ---
  async function createPoiComment(tripId, poiId, payload) {
    const { data } = await client.post(`/trips/${tripId}/pois/${poiId}/comments/`, payload)
    return data
  }

  async function updatePoiComment(tripId, poiId, commentId, payload) {
    const { data } = await client.patch(
      `/trips/${tripId}/pois/${poiId}/comments/${commentId}/`,
      payload,
    )
    return data
  }

  async function deletePoiComment(tripId, poiId, commentId) {
    await client.delete(`/trips/${tripId}/pois/${poiId}/comments/${commentId}/`)
  }

  return {
    trips,
    loading,
    fetchTrips,
    createTrip,
    fetchTrip,
    updateTrip,
    deleteTrip,
    fetchMembers,
    addMember,
    removeMember,
    cancelInvitation,
    fetchFlights,
    createFlight,
    updateFlight,
    deleteFlight,
    fetchAccommodations,
    createAccommodation,
    updateAccommodation,
    deleteAccommodation,
    fetchItinerary,
    createItineraryItem,
    updateItineraryItem,
    deleteItineraryItem,
    fetchMeals,
    createMeal,
    updateMeal,
    deleteMeal,
    fetchRentals,
    createRental,
    updateRental,
    deleteRental,
    fetchGrocery,
    createGroceryItem,
    updateGroceryItem,
    deleteGroceryItem,
    fetchPois,
    createPoi,
    updatePoi,
    deletePoi,
    togglePoiInterest,
    createPoiComment,
    updatePoiComment,
    deletePoiComment,
  }
})
