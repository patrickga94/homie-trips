<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: { type: String, default: '' },
  titleClass: { type: String, default: 'text-lg font-medium' },
  count: { type: [Number, String], default: null },
  open: { type: Boolean, default: false },
})

const isOpen = ref(props.open)
</script>

<template>
  <div>
    <button
      type="button"
      class="flex w-full items-center justify-between gap-2 py-1 text-left"
      :aria-expanded="isOpen"
      @click="isOpen = !isOpen"
    >
      <span class="flex items-center gap-2">
        <span :class="titleClass">{{ title }}</span>
        <span
          v-if="count !== null"
          class="rounded-full bg-stone-100 px-2 py-0.5 text-xs font-normal text-stone-600"
        >
          {{ count }}
        </span>
      </span>
      <svg
        class="h-5 w-5 shrink-0 text-stone-400 transition-transform"
        :class="{ 'rotate-180': isOpen }"
        viewBox="0 0 20 20"
        fill="currentColor"
        aria-hidden="true"
      >
        <path
          fill-rule="evenodd"
          d="M5.22 8.22a.75.75 0 0 1 1.06 0L10 11.94l3.72-3.72a.75.75 0 1 1 1.06 1.06l-4.25 4.25a.75.75 0 0 1-1.06 0L5.22 9.28a.75.75 0 0 1 0-1.06Z"
          clip-rule="evenodd"
        />
      </svg>
    </button>
    <div v-show="isOpen" class="pt-2">
      <slot />
    </div>
  </div>
</template>
