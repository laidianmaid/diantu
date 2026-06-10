<template>
  <div class="bg-white/90 backdrop-blur rounded-xl shadow-md overflow-hidden">
    <div class="flex items-center gap-2 px-3 py-2 border-b border-gray-100">
      <span class="text-base">☕</span>
      <span class="text-sm font-medium text-gray-700">AI 妹抖店助手</span>
    </div>
    <div v-if="reply" class="px-3 py-2 text-sm text-gray-700 max-h-32 overflow-y-auto">{{ reply }}</div>
    <div class="flex items-center gap-2 px-3 py-2">
      <input
        v-model="message"
        @keyup.enter="send"
        :disabled="loading"
        placeholder="想要什么风格的妹抖？"
        class="flex-1 text-sm outline-none bg-transparent placeholder-gray-400"
      />
      <button
        @click="send"
        :disabled="loading || !message.trim()"
        class="text-sm font-medium text-amber-600 disabled:opacity-40 hover:text-amber-700 transition"
      >
        {{ loading ? '...' : '发送' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { aiApi } from '../api'
import { useShopsStore } from '../stores/shops'

const shopsStore = useShopsStore()
const message = ref('')
const reply = ref('')
const loading = ref(false)

async function send() {
  if (!message.value.trim() || loading.value) return
  loading.value = true
  try {
    const { data } = await aiApi.chat(message.value)
    reply.value = data.reply
    shopsStore.setHighlight(data.highlighted_shop_ids || [])
    message.value = ''
  } catch {
    reply.value = '连接 AI 失败，请稍后再试。'
  } finally {
    loading.value = false
  }
}
</script>
