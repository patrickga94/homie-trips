<script setup>
import { ref, onMounted, onBeforeUnmount, nextTick, watch } from 'vue'

const props = defineProps({
  text: { type: String, default: '' },
})

const el = ref(null)
const expanded = ref(false)
const overflowing = ref(false)

async function check() {
  await nextTick()
  const node = el.value
  if (!node) return
  // While clamped, a taller scrollHeight than clientHeight means it's truncated.
  // Once expanded we can't measure the clamp, so keep the toggle visible.
  if (!expanded.value) {
    overflowing.value = node.scrollHeight > node.clientHeight + 1
  }
}

onMounted(() => {
  check()
  window.addEventListener('resize', check)
})
onBeforeUnmount(() => window.removeEventListener('resize', check))
watch(
  () => props.text,
  () => {
    expanded.value = false
    check()
  },
)
</script>

<template>
  <div>
    <p
      ref="el"
      :class="['whitespace-pre-line text-sm text-stone-500', expanded ? '' : 'line-clamp-4']"
    >{{ text }}</p>
    <button
      v-if="overflowing"
      type="button"
      class="mt-0.5 text-xs font-medium text-forest-600 hover:underline"
      @click="expanded = !expanded"
    >
      {{ expanded ? 'Show less' : 'Show more' }}
    </button>
  </div>
</template>
