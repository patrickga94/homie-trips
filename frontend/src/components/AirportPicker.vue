<script setup>
import { ref, computed, watch } from 'vue'
import airports from '../data/airports.json'

const props = defineProps({
  modelValue: { type: String, default: '' },
  placeholder: { type: String, default: 'Search by code or city…' },
})
const emit = defineEmits(['update:modelValue'])

const query = ref('')
const open = ref(false)
const activeIndex = ref(-1)

const byCode = new Map(airports.map((a) => [a.code, a]))

function labelFor(code) {
  const a = byCode.get(code)
  return a ? `${a.code} — ${a.city}` : code
}

// Keep the text field in sync when the bound value changes from outside
// (e.g. the parent resets the flight form after saving).
watch(
  () => props.modelValue,
  (v) => {
    if (!open.value) query.value = v ? labelFor(v) : ''
  },
  { immediate: true },
)

const results = computed(() => {
  const q = query.value.trim().toLowerCase()
  const list = q
    ? airports.filter(
        (a) =>
          a.code.toLowerCase().includes(q) ||
          a.city.toLowerCase().includes(q) ||
          a.name.toLowerCase().includes(q),
      )
    : airports
  return list.slice(0, 50)
})

function onFocus() {
  query.value = '' // start a fresh search; blur restores the label if unchanged
  open.value = true
  activeIndex.value = -1
}

function onInput() {
  open.value = true
  activeIndex.value = -1
  emit('update:modelValue', '') // typing invalidates any prior selection
}

function onBlur() {
  // Restore the selected label if the user didn't pick a new option.
  setTimeout(() => {
    open.value = false
    query.value = props.modelValue ? labelFor(props.modelValue) : ''
  }, 120)
}

function select(a) {
  emit('update:modelValue', a.code)
  open.value = false
  query.value = `${a.code} — ${a.city}`
}

function move(dir) {
  open.value = true
  const max = results.value.length - 1
  activeIndex.value = Math.min(Math.max(activeIndex.value + dir, 0), max)
}

function enter() {
  const list = results.value
  if (list.length) select(list[activeIndex.value >= 0 ? activeIndex.value : 0])
}
</script>

<template>
  <div class="relative">
    <input
      v-model="query"
      class="input"
      :placeholder="placeholder"
      autocomplete="off"
      @focus="onFocus"
      @blur="onBlur"
      @input="onInput"
      @keydown.down.prevent="move(1)"
      @keydown.up.prevent="move(-1)"
      @keydown.enter.prevent="enter"
      @keydown.esc="open = false"
    />
    <ul
      v-if="open && results.length"
      class="absolute z-20 mt-1 max-h-60 w-full overflow-auto rounded-md border border-stone-200 bg-white shadow-lg"
    >
      <li
        v-for="(a, i) in results"
        :key="a.code"
        :class="[
          'cursor-pointer px-3 py-2 text-sm',
          i === activeIndex ? 'bg-forest-50 text-forest-800' : 'hover:bg-stone-50',
        ]"
        @mousedown.prevent="select(a)"
      >
        <span class="font-medium">{{ a.code }}</span>
        <span class="text-stone-500"> — {{ a.city }}</span>
        <span class="block truncate text-xs text-stone-400">{{ a.name }}</span>
      </li>
    </ul>
  </div>
</template>
