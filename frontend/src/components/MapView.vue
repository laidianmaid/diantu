<template>
  <div ref="mapContainer" class="w-full h-full" />
</template>

<script setup>
import { ref, watch, onMounted, onUnmounted } from 'vue'
import { useShopsStore } from '../stores/shops'

const mapContainer = ref(null)
const shopsStore = useShopsStore()
let map = null
let markers = {}

const COLOR_HEX = {
  red: '#ef4444', green: '#22c55e', yellow: '#eab308', blue: '#3b82f6',
  purple: '#a855f7', orange: '#f97316', pink: '#ec4899', black: '#1f2937',
  white: '#f9fafb', gray: '#6b7280',
}

function loadAmapScript() {
  return new Promise((resolve, reject) => {
    if (window.AMap) return resolve()
    const key = window.AMAP_JS_KEY
    if (!key || key === '__AMAP_JS_KEY__') {
      console.warn('高德地图 JS Key 未配置，使用占位地图')
      return resolve()
    }
    const s = document.createElement('script')
    s.src = `https://webapi.amap.com/maps?v=2.0&key=${key}`
    s.onload = resolve
    s.onerror = reject
    document.head.appendChild(s)
  })
}

function initMap() {
  if (!window.AMap) return
  map = new window.AMap.Map(mapContainer.value, {
    center: [121.473701, 31.230416],
    zoom: 14,
    mapStyle: 'amap://styles/light',
  })
  renderMarkers()
}

function renderMarkers() {
  if (!map) return
  // Clear old markers
  Object.values(markers).forEach(m => map.remove(m))
  markers = {}

  shopsStore.shops.forEach(shop => {
    if (!shop.lat || !shop.lng) return
    const isHighlighted = shopsStore.highlightedIds.length === 0 || shopsStore.highlightedIds.includes(shop.id)
    const color = COLOR_HEX[shop.color] || '#6b7280'
    const circle = new window.AMap.CircleMarker({
      center: [shop.lng, shop.lat],
      radius: isHighlighted ? 10 : 7,
      strokeColor: '#fff',
      strokeWeight: 2,
      fillColor: color,
      fillOpacity: isHighlighted ? 1 : 0.4,
      zIndex: isHighlighted ? 120 : 100,
      cursor: 'pointer',
    })
    circle.on('click', () => shopsStore.selectShop(shop.id))
    const label = new window.AMap.Text({
      text: shop.name,
      position: [shop.lng, shop.lat],
      offset: new window.AMap.Pixel(14, -8),
      style: { background: 'transparent', border: 'none', fontSize: '12px', color: '#1f2937' },
    })
    map.add([circle, label])
    markers[shop.id] = circle
  })
}

onMounted(async () => {
  await loadAmapScript()
  initMap()
})

onUnmounted(() => {
  if (map) map.destroy()
})

watch(() => shopsStore.shops, renderMarkers, { deep: true })
watch(() => shopsStore.highlightedIds, renderMarkers, { deep: true })
</script>
