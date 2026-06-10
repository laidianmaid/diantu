<template>
  <div ref="mapContainer" class="w-full h-full" />

  <!-- 同坐标多店弹出列表 -->
  <Teleport to="body">
    <div
      v-if="clusterPopup.visible"
      class="fixed z-50 bg-white rounded-xl shadow-xl border border-gray-100 py-2 min-w-48 max-w-64"
      :style="{ left: clusterPopup.x + 'px', top: clusterPopup.y + 'px' }"
    >
      <p class="text-xs text-gray-400 px-3 pb-1 border-b border-gray-100">{{ clusterPopup.shops.length }} 家店铺</p>
      <button
        v-for="s in clusterPopup.shops"
        :key="s.id"
        @click="selectFromCluster(s.id)"
        class="w-full text-left px-3 py-2 text-sm text-gray-700 hover:bg-amber-50 flex items-center gap-2 transition"
      >
        <span class="w-2.5 h-2.5 rounded-full flex-shrink-0" :style="`background:${COLOR_HEX[s.color] || '#6b7280'}`" />
        {{ s.name }}
      </button>
    </div>
    <div v-if="clusterPopup.visible" class="fixed inset-0 z-40" @click="clusterPopup.visible = false" />
  </Teleport>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { useShopsStore } from '../stores/shops'

const mapContainer = ref(null)
const shopsStore = useShopsStore()
let map = null
let mapObjects = []  // 所有添加到地图的对象

const COLOR_HEX = {
  sagegreen: '#8FBC8F',
  olivedrab: '#6B8E23',
  seagreen:  '#2E8B57',
  salmon:    '#FA8072',
  hotpink:   '#FF69B4',
}

const clusterPopup = reactive({ visible: false, x: 0, y: 0, shops: [] })

function loadAmapScript() {
  return new Promise((resolve, reject) => {
    if (window.AMap) return resolve()
    const key = import.meta.env.VITE_AMAP_JS_KEY
    if (!key) {
      console.warn('VITE_AMAP_JS_KEY 未配置，地图不加载')
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
    mapStyle: 'amap://styles/macaron',
  })
  map.on('click', () => {
    shopsStore.selectedShop = null
    clusterPopup.visible = false
  })
  renderMarkers()
}

// 把坐标精度截断到小数点后4位（约11米），相当于"同一栋楼"
function coordKey(lat, lng) {
  return `${parseFloat(lat).toFixed(4)},${parseFloat(lng).toFixed(4)}`
}

// 生成水滴形 SVG pin
function makePinSvg(color, { opacity = 1, count = 0, w = 18 } = {}) {
  const h = Math.round(w * 4 / 3)
  const cx = w / 2
  const cr = w * 0.42
  const cy = cr + 1
  const inner = count > 1
    ? `<text x="12" y="13" text-anchor="middle" dominant-baseline="middle"
         font-size="11" font-weight="700" fill="white"
         font-family="system-ui,sans-serif">${count}</text>`
    : ''
  return `<svg xmlns="http://www.w3.org/2000/svg" width="${w}" height="${h}" viewBox="0 0 24 32">
    <path d="M12 0C5.4 0 0 5.4 0 12c0 8.4 12 20 12 20s12-11.6 12-20C24 5.4 18.6 0 12 0z"
      fill="${color}" fill-opacity="${opacity}" stroke="white" stroke-width="1.5"/>
    ${inner}
  </svg>`
}

function renderMarkers() {
  if (!map) return
  map.remove(mapObjects)
  mapObjects = []
  clusterPopup.visible = false

  const highlightSet = new Set(shopsStore.highlightedIds)
  const hasFilter = highlightSet.size > 0

  // 按坐标分组
  const groups = new Map()
  shopsStore.shops.forEach(shop => {
    if (!shop.lat || !shop.lng) return
    const key = coordKey(shop.lat, shop.lng)
    if (!groups.has(key)) groups.set(key, [])
    groups.get(key).push(shop)
  })

  groups.forEach((shops, key) => {
    const [lat, lng] = key.split(',').map(Number)
    const isMulti = shops.length > 1
    const isHighlighted = !hasFilter || shops.some(s => highlightSet.has(s.id))

    // 多店聚合取主色（众数）
    const colorCount = {}
    shops.forEach(s => { colorCount[s.color] = (colorCount[s.color] || 0) + 1 })
    const mainColor = Object.entries(colorCount).sort((a, b) => b[1] - a[1])[0][0]
    const fillColor = COLOR_HEX[mainColor] || '#6b7280'

    // pin 尺寸：多店稍大，暗淡时缩小
    const pinW = isMulti ? 22 : (isHighlighted ? 18 : 14)
    const pinH = Math.round(pinW * 4 / 3)
    const opacity = isHighlighted ? 1 : 0.4

    const pinSvg = makePinSvg(fillColor, { opacity, count: isMulti ? shops.length : 0, w: pinW })

    const marker = new window.AMap.Marker({
      position: [lng, lat],
      content: pinSvg,
      // offset: 让 pin 底部尖端对齐坐标点
      offset: new window.AMap.Pixel(-pinW / 2, -pinH),
      zIndex: isHighlighted ? 120 : 100,
      cursor: 'pointer',
    })

    function handleClick() {
      if (isMulti) {
        const pixel = map.lngLatToContainer([lng, lat])
        const rect = mapContainer.value.getBoundingClientRect()
        clusterPopup.x = rect.left + pixel.x + 16
        clusterPopup.y = rect.top + pixel.y - 8
        clusterPopup.shops = shops
        clusterPopup.visible = true
      } else {
        shopsStore.selectShop(shops[0].id)
      }
    }

    marker.on('click', handleClick)
    mapObjects.push(marker)
    map.add(marker)

    // 单店名称标签（高亮时显示），居中在 pin 下方
    if (!isMulti && isHighlighted) {
      const label = new window.AMap.Text({
        text: shops[0].name,
        position: [lng, lat],
        anchor: 'center',
        offset: new window.AMap.Pixel(0, 4),
        style: {
          background: 'transparent',
          border: 'none',
          fontSize: '11px',
          color: '#1f2937',
          whiteSpace: 'nowrap',
          cursor: 'pointer',
          textShadow: '0 1px 3px rgba(255,255,255,0.9)',
        },
      })
      label.on('click', handleClick)
      mapObjects.push(label)
      map.add(label)
    }
  })
}

function selectFromCluster(id) {
  clusterPopup.visible = false
  shopsStore.selectShop(id)
}

let locationMarker = null

function locateUser() {
  if (!navigator.geolocation) return
  navigator.geolocation.getCurrentPosition(
    (pos) => {
      if (!map) return
      const { longitude, latitude } = pos.coords
      map.setCenter([longitude, latitude])
      map.setZoom(15)
      if (locationMarker) map.remove(locationMarker)
      locationMarker = new window.AMap.CircleMarker({
        center: [longitude, latitude],
        radius: 8,
        strokeColor: '#fff',
        strokeWeight: 2,
        fillColor: '#3b82f6',
        fillOpacity: 1,
        zIndex: 200,
      })
      map.add(locationMarker)
    },
    () => {},
    { enableHighAccuracy: true, timeout: 8000 },
  )
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

defineExpose({ locateUser })
</script>
