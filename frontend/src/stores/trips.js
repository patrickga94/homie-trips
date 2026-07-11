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
    fetchFlights,
    createFlight,
    updateFlight,
    deleteFlight,
    fetchAccommodations,
    createAccommodation,
    updateAccommodation,
    deleteAccommodation,
  }
})
