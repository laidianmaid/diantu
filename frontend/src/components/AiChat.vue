<template>
  <div class="bg-white/90 backdrop-blur rounded-xl shadow-md overflow-visible relative">
    <div class="flex items-center gap-2 px-3 py-2 border-b border-gray-100">
      <span class="text-base">☕</span>
      <span class="text-sm font-medium text-gray-700">AI 妹抖店助手</span>
    </div>
    <div v-if="reply" class="px-3 py-2 text-sm text-gray-700 max-h-32 overflow-y-auto border-b border-gray-100">{{ reply }}</div>

    <!-- Input row -->
    <div class="flex items-center gap-2 px-3 py-2 relative">
      <input
        ref="inputRef"
        v-model="message"
        @input="onInput"
        @keyup.enter="handleEnter"
        @keydown.down.prevent="moveSuggestion(1)"
        @keydown.up.prevent="moveSuggestion(-1)"
        @keydown.esc="closeSuggestions"
        @blur="onBlur"
        @focus="onInput"
        :disabled="loading"
        placeholder="搜索店铺 或 问 AI 助手…"
        class="flex-1 text-sm outline-none bg-transparent placeholder-gray-400"
        autocomplete="off"
      />
      <button
        @click="sendAi"
        :disabled="loading || !message.trim()"
        class="text-sm font-medium text-amber-600 disabled:opacity-40 hover:text-amber-700 transition flex-shrink-0"
      >
        {{ loading ? '…' : 'AI' }}
      </button>
    </div>

    <!-- Suggestions dropdown -->
    <Teleport to="body">
      <div
        v-if="suggestions.length > 0"
        class="fixed z-50 bg-white rounded-xl shadow-xl border border-gray-100 py-1 overflow-hidden"
        :style="dropdownStyle"
      >
        <button
          v-for="(s, i) in suggestions"
          :key="s.id"
          @mousedown.prevent="selectSuggestion(s)"
          class="w-full text-left px-3 py-2 text-sm flex items-center gap-2 transition"
          :class="i === activeIdx ? 'bg-amber-50 text-amber-700' : 'text-gray-700 hover:bg-gray-50'"
        >
          <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="`background:${COLOR_HEX[s.color] || '#6b7280'}`" />
          <span class="flex-1 truncate">{{ s.name }}</span>
          <span class="text-xs text-gray-400 flex-shrink-0">{{ COLOR_LABEL[s.color] }}</span>
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup>
import { ref, computed, nextTick } from 'vue'
import { aiApi } from '../api'
import { useShopsStore } from '../stores/shops'
import { match } from 'pinyin-pro'

const shopsStore = useShopsStore()
const inputRef = ref(null)
const message = ref('')
const reply = ref('')
const loading = ref(false)
const suggestions = ref([])
const activeIdx = ref(-1)
const dropdownStyle = ref({})

const COLOR_HEX = {
  sagegreen: '#8FBC8F', olivedrab: '#6B8E23', seagreen: '#2E8B57',
  salmon: '#FA8072', hotpink: '#FF69B4',
}
const COLOR_LABEL = {
  sagegreen: '纯素', olivedrab: '半绿半素', seagreen: '纯绿',
  salmon: '半荤半绿', hotpink: '纯荤',
}

function matchShop(shop, query) {
  if (!query) return false
  const q = query.trim().toLowerCase()
  if (!q) return false
  // Direct substring match
  if (shop.name.toLowerCase().includes(q)) return true
  // Pinyin match (supports partial pinyin)
  const result = match(shop.name, q, { precision: 'start' })
  return result !== null
}

function onInput() {
  const q = message.value.trim()
  activeIdx.value = -1
  if (!q) {
    suggestions.value = []
    return
  }
  suggestions.value = shopsStore.shops
    .filter(s => matchShop(s, q))
    .slice(0, 8)

  if (suggestions.value.length > 0) {
    nextTick(updateDropdownPos)
  }
}

function updateDropdownPos() {
  const el = inputRef.value
  if (!el) return
  const rect = el.closest('.bg-white\\/90').getBoundingClientRect()
  dropdownStyle.value = {
    top: rect.bottom + 4 + 'px',
    left: rect.left + 'px',
    width: rect.width + 'px',
    maxHeight: '260px',
    overflowY: 'auto',
  }
}

function moveSuggestion(dir) {
  if (!suggestions.value.length) return
  activeIdx.value = (activeIdx.value + dir + suggestions.value.length + 1) % (suggestions.value.length + 1) - 1
  if (activeIdx.value < -1) activeIdx.value = suggestions.value.length - 1
}

function selectSuggestion(shop) {
  message.value = ''
  suggestions.value = []
  shopsStore.selectShop(shop.id)
}

function closeSuggestions() {
  suggestions.value = []
  activeIdx.value = -1
}

function onBlur() {
  // slight delay so mousedown on suggestion fires first
  setTimeout(closeSuggestions, 150)
}

function handleEnter() {
  if (activeIdx.value >= 0 && suggestions.value[activeIdx.value]) {
    selectSuggestion(suggestions.value[activeIdx.value])
  } else if (suggestions.value.length === 1) {
    selectSuggestion(suggestions.value[0])
  } else {
    sendAi()
  }
}

async function sendAi() {
  if (!message.value.trim() || loading.value) return
  closeSuggestions()
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
