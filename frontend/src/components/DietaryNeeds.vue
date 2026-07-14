<script setup>
// Trip members' dietary restrictions, shown where meals/groceries are planned.
defineProps({
  needs: { type: Array, default: () => [] }, // [{ name, items: [] }]
})
</script>

<template>
  <div
    v-if="needs.length"
    class="rounded-md border border-clay-200 bg-clay-50 p-3 text-sm"
  >
    <p class="mb-1 font-medium text-clay-700">Dietary needs to plan around</p>
    <ul class="space-y-0.5 text-clay-700">
      <li v-for="d in needs" :key="d.name">
        <span class="font-medium">{{ d.name }}:</span> {{ d.items.join(', ') }}
      </li>
    </ul>
  </div>
</template>
