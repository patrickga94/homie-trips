<script setup>
import { ref, computed } from 'vue'
import { useTripsStore } from '../stores/trips'

const props = defineProps({
  tripId: { type: [String, Number], required: true },
  poiId: { type: [String, Number], required: true },
  // Top-level comments (each with its replies nested), supplied by the parent
  // POI list — no separate fetch on mount.
  comments: { type: Array, default: () => [] },
})

// Emitted after any create/edit/delete so the parent can refresh the POI list.
const emit = defineEmits(['changed'])

const store = useTripsStore()

// Comments are the discussion space, so start expanded — but still collapsible.
const open = ref(true)
const newBody = ref('')
const replyingTo = ref(null)
const replyBody = ref('')
const editingId = ref(null)
const editBody = ref('')

const totalCount = computed(() =>
  props.comments.reduce((n, c) => n + 1 + (c.replies?.length || 0), 0),
)

async function addComment() {
  const body = newBody.value.trim()
  if (!body) return
  await store.createPoiComment(props.tripId, props.poiId, { body })
  newBody.value = ''
  emit('changed')
}

function startReply(c) {
  replyingTo.value = c.id
  replyBody.value = ''
  editingId.value = null
}

function cancelReply() {
  replyingTo.value = null
  replyBody.value = ''
}

async function addReply(parent) {
  const body = replyBody.value.trim()
  if (!body) return
  await store.createPoiComment(props.tripId, props.poiId, {
    body,
    parent: parent.id,
  })
  cancelReply()
  emit('changed')
}

function startEdit(c) {
  editingId.value = c.id
  editBody.value = c.body
  replyingTo.value = null
}

function cancelEdit() {
  editingId.value = null
  editBody.value = ''
}

async function saveEdit(c) {
  const body = editBody.value.trim()
  if (!body) return
  await store.updatePoiComment(props.tripId, props.poiId, c.id, { body })
  cancelEdit()
  emit('changed')
}

async function remove(c) {
  if (!confirm('Delete this comment?')) return
  await store.deletePoiComment(props.tripId, props.poiId, c.id)
  emit('changed')
}

function formatTs(c) {
  const stamp = new Date(c.created_at).toLocaleString(undefined, {
    month: 'short',
    day: 'numeric',
    hour: 'numeric',
    minute: '2-digit',
  })
  const edited = c.updated_at && c.updated_at !== c.created_at
  return edited ? `${stamp} · edited` : stamp
}
</script>

<template>
  <!-- Stop clicks bubbling to the POI card (which toggles its action reveal). -->
  <div class="mt-3 space-y-3 border-t border-stone-200 pt-3" @click.stop>
    <button
      type="button"
      class="flex min-h-[36px] items-center gap-1 text-sm font-medium text-stone-500 hover:text-stone-700"
      @click="open = !open"
    >
      <svg
        xmlns="http://www.w3.org/2000/svg"
        viewBox="0 0 20 20"
        fill="currentColor"
        class="h-4 w-4 transition-transform"
        :class="{ '-rotate-90': !open }"
      >
        <path fill-rule="evenodd" d="M5.23 7.21a.75.75 0 0 1 1.06.02L10 11.168l3.71-3.938a.75.75 0 1 1 1.08 1.04l-4.25 4.5a.75.75 0 0 1-1.08 0l-4.25-4.5a.75.75 0 0 1 .02-1.06Z" clip-rule="evenodd" />
      </svg>
      Discussion
      <span v-if="totalCount">· {{ totalCount }}</span>
    </button>

    <ul v-if="open && comments.length" class="space-y-3">
      <li v-for="c in comments" :key="c.id" class="space-y-2">
        <!-- Top-level comment -->
        <div class="rounded-md bg-white p-2 ring-1 ring-stone-200">
          <div class="flex items-baseline justify-between gap-2">
            <span class="text-sm font-medium text-stone-700">{{ c.author_name }}</span>
            <span class="shrink-0 text-xs text-stone-400">{{ formatTs(c) }}</span>
          </div>

          <template v-if="editingId === c.id">
            <textarea v-model="editBody" rows="2" class="input mt-1"></textarea>
            <div class="mt-1 flex gap-2">
              <button class="btn-secondary" :disabled="!editBody.trim()" @click="saveEdit(c)">
                Save
              </button>
              <button class="btn-secondary" @click="cancelEdit">Cancel</button>
            </div>
          </template>
          <template v-else>
            <p class="whitespace-pre-wrap break-words text-sm text-stone-700">{{ c.body }}</p>
            <div class="mt-1 flex gap-3 text-xs">
              <button class="text-stone-500 hover:text-stone-700" @click="startReply(c)">
                Reply
              </button>
              <button
                v-if="c.is_mine"
                class="text-stone-500 hover:text-stone-700"
                @click="startEdit(c)"
              >
                Edit
              </button>
              <button
                v-if="c.is_mine"
                class="text-clay-600 hover:text-clay-700"
                @click="remove(c)"
              >
                Delete
              </button>
            </div>
          </template>
        </div>

        <!-- Replies -->
        <ul v-if="c.replies?.length" class="space-y-2 border-l border-stone-200 pl-4">
          <li
            v-for="r in c.replies"
            :key="r.id"
            class="rounded-md bg-white p-2 ring-1 ring-stone-200"
          >
            <div class="flex items-baseline justify-between gap-2">
              <span class="text-sm font-medium text-stone-700">{{ r.author_name }}</span>
              <span class="shrink-0 text-xs text-stone-400">{{ formatTs(r) }}</span>
            </div>

            <template v-if="editingId === r.id">
              <textarea v-model="editBody" rows="2" class="input mt-1"></textarea>
              <div class="mt-1 flex gap-2">
                <button class="btn-secondary" :disabled="!editBody.trim()" @click="saveEdit(r)">
                  Save
                </button>
                <button class="btn-secondary" @click="cancelEdit">Cancel</button>
              </div>
            </template>
            <template v-else>
              <p class="whitespace-pre-wrap break-words text-sm text-stone-700">{{ r.body }}</p>
              <div v-if="r.is_mine" class="mt-1 flex gap-3 text-xs">
                <button class="text-stone-500 hover:text-stone-700" @click="startEdit(r)">
                  Edit
                </button>
                <button class="text-clay-600 hover:text-clay-700" @click="remove(r)">
                  Delete
                </button>
              </div>
            </template>
          </li>
        </ul>

        <!-- Reply composer -->
        <form
          v-if="replyingTo === c.id"
          class="flex flex-col gap-2 pl-4"
          @submit.prevent="addReply(c)"
        >
          <textarea
            v-model="replyBody"
            rows="2"
            class="input"
            placeholder="Write a reply…"
          ></textarea>
          <div class="flex gap-2">
            <button type="submit" class="btn-secondary" :disabled="!replyBody.trim()">
              Reply
            </button>
            <button type="button" class="btn-secondary" @click="cancelReply">Cancel</button>
          </div>
        </form>
      </li>
    </ul>

    <!-- New comment -->
    <form v-if="open" class="flex flex-col gap-2" @submit.prevent="addComment">
      <textarea
        v-model="newBody"
        rows="2"
        class="input"
        placeholder="Add a comment…"
      ></textarea>
      <div>
        <button type="submit" class="btn-secondary" :disabled="!newBody.trim()">Post</button>
      </div>
    </form>
  </div>
</template>
