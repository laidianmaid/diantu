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
  sagegreen: '#8FBC8F',
  olivedrab: '#6B8E23',
  seagreen:  '#2E8B57',
  salmon:    '#FA8072',
  hotpink:   '#FF69B4',
}

function loadAmapScript() {
  return new Promise((resolve, reject) => {
    if (window.AMap) return resolve()
    const key = import.meta.env.VITE_AMAP_JS_KEY
    if (!key) {
      console.warn('VITE_AMAP_JS_KEY 未配置，地图不加载')
      return resolve()
    }
    // _AMapSecurityConfig.serviceHost 在 index.html 中已配置，jscode 由后端代理注入
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
