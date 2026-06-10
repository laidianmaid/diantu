<template>
  <div>
    <div v-if="authStore.user" class="mb-4">
      <div class="flex gap-2 mb-2">
        <span class="text-sm text-gray-600">打分：</span>
        <button
          v-for="n in 5"
          :key="n"
          @click="newScore = n"
          class="text-lg leading-none"
          :class="n <= newScore ? 'text-amber-400' : 'text-gray-300'"
        >★</button>
      </div>
      <div class="flex gap-2">
        <input
          v-model="newContent"
          placeholder="写下你的感受..."
          class="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-400"
        />
        <button
          @click="submit"
          :disabled="!newContent.trim()"
          class="px-4 py-2 bg-amber-500 text-white text-sm rounded-lg disabled:opacity-40 hover:bg-amber-600 transition"
        >发布</button>
      </div>
    </div>

    <div v-if="!reviews.length" class="text-center text-gray-400 text-sm py-6">暂无评论</div>
    <div v-for="r in reviews" :key="r.id" class="mb-4">
      <div class="flex items-start gap-2">
        <div class="w-8 h-8 rounded-full bg-amber-100 flex items-center justify-center text-amber-700 font-bold text-xs flex-shrink-0">
          {{ r.username[0]?.toUpperCase() || '?' }}
        </div>
        <div class="flex-1 min-w-0">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="font-medium text-sm text-gray-800">{{ r.username }}</span>
            <span v-if="r.score" class="text-xs text-amber-500">{{ '★'.repeat(Math.round(r.score)) }}</span>
            <span class="text-xs text-gray-400">{{ formatDate(r.created_at) }}</span>
          </div>
          <p class="text-sm text-gray-700 mt-1 break-words">{{ r.content }}</p>
          <div class="flex items-center gap-3 mt-1">
            <button @click="react(r.id, 'like')" class="text-xs text-gray-400 hover:text-green-500 transition">
              👍 {{ r.likes }}
            </button>
            <button @click="react(r.id, 'dislike')" class="text-xs text-gray-400 hover:text-red-400 transition">
              👎 {{ r.dislikes }}
            </button>
            <button v-if="authStore.user?.id === r.user_id" @click="del(r.id)" class="text-xs text-gray-300 hover:text-red-400 transition ml-auto">
              删除
            </button>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { reviewApi } from '../api'
import { useAuthStore } from '../stores/auth'

const props = defineProps({ shopId: Number })
const authStore = useAuthStore()
const reviews = ref([])
const newContent = ref('')
const newScore = ref(0)

async function load() {
  if (!props.shopId) return
  const { data } = await reviewApi.list(props.shopId)
  reviews.value = data
}

async function submit() {
  await reviewApi.create(props.shopId, { content: newContent.value, score: newScore.value || null })
  newContent.value = ''
  newScore.value = 0
  await load()
}

async function react(id, type) {
  if (!authStore.user) return
  await reviewApi.react(id, type)
  await load()
}

async function del(id) {
  await reviewApi.delete(id)
  await load()
}

function formatDate(iso) {
  return new Date(iso).toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' })
}

watch(() => props.shopId, load, { immediate: true })
</script>
