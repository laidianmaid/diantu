<template>
  <div v-if="shop" class="h-full flex flex-col bg-white overflow-hidden">
    <!-- Header -->
    <div class="flex items-center gap-2 px-4 py-3 border-b border-gray-100 flex-shrink-0">
      <button @click="$emit('close')" class="text-gray-400 hover:text-gray-600 mr-1">←</button>
      <h2 class="font-semibold text-gray-900 flex-1 truncate">{{ shop.name }}</h2>
      <span class="text-sm font-medium text-amber-500">{{ shop.score ? shop.score.toFixed(1) : '—' }}</span>
      <span class="text-xs px-2 py-0.5 rounded-full" :class="statusClass">{{ statusLabel }}</span>
    </div>

    <div class="flex-1 overflow-y-auto">
      <!-- Photos -->
      <div v-if="shop.photo_urls?.length" class="flex gap-2 p-3 overflow-x-auto">
        <img v-for="(url, i) in shop.photo_urls" :key="i" :src="url" class="h-36 w-auto rounded-lg object-cover flex-shrink-0" />
      </div>
      <div v-else class="h-32 bg-gradient-to-br from-amber-50 to-orange-100 flex items-center justify-center text-4xl">☕</div>

      <div class="px-4 py-3 space-y-4">
        <!-- Description -->
        <p v-if="shop.description" class="text-sm text-gray-600 leading-relaxed">{{ shop.description }}</p>

        <!-- Tags -->
        <div class="flex flex-wrap gap-2">
          <span v-if="shop.style" class="text-xs bg-amber-50 text-amber-700 px-2 py-1 rounded-full">{{ shop.style }}</span>
          <span v-if="shop.type" class="text-xs bg-blue-50 text-blue-700 px-2 py-1 rounded-full">{{ shop.type }}</span>
          <span
            class="text-xs px-2 py-1 rounded-full font-medium"
            :style="`background:${colorHex}28; color:${colorHex}`"
          >
            {{ colorLabel }}
          </span>
        </div>

        <!-- Address -->
        <div>
          <p class="text-sm text-gray-500 mb-1">📍 {{ shop.address }}</p>
          <div class="flex flex-wrap gap-2">
            <a
              :href="`https://uri.amap.com/navigation?to=${shop.lng},${shop.lat},${shop.name}&mode=car&src=diantu`"
              target="_blank"
              class="text-xs px-3 py-1 rounded-full border border-blue-200 text-blue-600 hover:bg-blue-50 transition"
            >高德导航</a>
            <a
              :href="`http://api.map.baidu.com/direction?destination=latlng:${shop.lat},${shop.lng}|name:${shop.name}&mode=driving&output=html`"
              target="_blank"
              class="text-xs px-3 py-1 rounded-full border border-blue-200 text-blue-600 hover:bg-blue-50 transition"
            >百度导航</a>
            <a
              :href="`didiuxing://passenger/select-destination?destInfo=${encodeURIComponent(JSON.stringify({name:shop.name,latitude:shop.lat,longitude:shop.lng}))}`"
              class="text-xs px-3 py-1 rounded-full border border-orange-200 text-orange-600 hover:bg-orange-50 transition"
            >滴滴打车</a>
          </div>
        </div>

        <!-- Hours -->
        <div v-if="shop.hours" class="text-sm text-gray-500">
          🕐 {{ formatHours(shop.hours) }}
        </div>

        <!-- Stats -->
        <div class="flex gap-4 text-sm text-gray-500">
          <span>❤️ {{ shop.favorite_count }} 收藏</span>
          <span>📍 {{ shop.checkin_count }} 打卡</span>
        </div>

        <!-- Actions -->
        <div v-if="authStore.user" class="flex gap-2">
          <button
            @click="favorite"
            class="flex-1 py-2 rounded-lg border text-sm transition"
            :class="shop.is_favorited
              ? 'border-rose-300 bg-rose-50 text-rose-600 hover:bg-rose-100'
              : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
          >{{ shop.is_favorited ? '❤️ 已收藏' : '收藏' }}</button>
          <button
            @click="checkin"
            class="flex-1 py-2 rounded-lg border text-sm transition"
            :class="shop.is_checked_in
              ? 'border-amber-300 bg-amber-50 text-amber-600 hover:bg-amber-100'
              : 'border-amber-200 text-amber-600 hover:bg-amber-50'"
          >{{ shop.is_checked_in ? '📍 已打卡' : '打卡' }}</button>
        </div>

        <!-- Reviews -->
        <div>
          <h3 class="font-medium text-gray-800 mb-3">用户评论</h3>
          <ReviewSection :shopId="shop.id" />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { shopApi } from '../api'
import { useAuthStore } from '../stores/auth'
import { useShopsStore } from '../stores/shops'
import ReviewSection from './ReviewSection.vue'

const props = defineProps({ shop: Object })
defineEmits(['close'])

const authStore = useAuthStore()
const shopsStore = useShopsStore()

const STATUS_MAP = {
  open: { label: '营业中', cls: 'bg-green-100 text-green-700' },
  closed: { label: '休息中', cls: 'bg-gray-100 text-gray-500' },
  preparing: { label: '筹划中', cls: 'bg-blue-100 text-blue-600' },
  shutdown: { label: '已闭店', cls: 'bg-red-100 text-red-500' },
}

const COLOR_MAP = {
  sagegreen: { hex: '#8FBC8F', label: '纯素' },
  olivedrab: { hex: '#6B8E23', label: '半绿半素' },
  seagreen:  { hex: '#2E8B57', label: '纯绿' },
  salmon:    { hex: '#FA8072', label: '半荤半绿' },
  hotpink:   { hex: '#FF69B4', label: '纯荤' },
}

const statusLabel = computed(() => STATUS_MAP[props.shop?.status]?.label || props.shop?.status)
const statusClass = computed(() => STATUS_MAP[props.shop?.status]?.cls || 'bg-gray-100 text-gray-500')
const colorEntry = computed(() => COLOR_MAP[props.shop?.color] || { hex: '#6b7280', label: props.shop?.color })
const colorHex = computed(() => colorEntry.value.hex)
const colorLabel = computed(() => colorEntry.value.label)

function formatHours(hours) {
  if (typeof hours === 'string') return hours
  if (hours?.open && hours?.close) return `${hours.open} - ${hours.close}`
  return JSON.stringify(hours)
}

async function favorite() {
  await shopApi.favorite(props.shop.id)
  shopsStore.selectShop(props.shop.id)
}

async function checkin() {
  await shopApi.checkin(props.shop.id)
  shopsStore.selectShop(props.shop.id)
}
</script>
