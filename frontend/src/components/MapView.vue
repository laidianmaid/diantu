<template>
  <div class="w-full h-full">
    <div ref="mapContainer" class="w-full h-full" />

    <!-- 同坐标多店弹出列表 -->
    <Teleport to="body">
      <div
        v-if="clusterPopup.visible"
        class="fixed z-50 bg-white rounded-xl shadow-xl border border-gray-100 py-2 min-w-48 max-w-64"
        :style="{ left: clusterPopup.x + 'px', top: clusterPopup.y + 'px' }"
        @click.stop
        @touchstart.stop
      >
        <p class="text-xs text-gray-400 px-3 pb-1 border-b border-gray-100">{{ clusterPopup.shops.length }} 家女仆店</p>
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
      <div v-if="clusterPopup.visible && !isMobileViewport" class="fixed inset-0 z-40" @click="clusterPopup.visible = false" />
    </Teleport>
  </div>
</template>

<script setup>
import { ref, reactive, watch, onMounted, onUnmounted } from 'vue'
import { useShopsStore } from '../stores/shops'

const mapContainer = ref(null)
const shopsStore = useShopsStore()
let map = null
let mapObjects = []  // 所有添加到地图的对象
let suppressMapClickUntil = 0
const isMobileViewport = ref(false)

const COLOR_HEX = {
  sagegreen: '#8FBC8F',
  olivedrab: '#6B8E23',
  seagreen:  '#2E8B57',
  salmon:    '#FA8072',
  hotpink:   '#FF69B4',
}

const clusterPopup = reactive({ visible: false, x: 0, y: 0, shops: [] })
let renderFrame = 0

function updateViewportFlags() {
  isMobileViewport.value = window.innerWidth < 768
}

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
  })
  map.on('click', () => {
    if (Date.now() < suppressMapClickUntil) return
    shopsStore.selectedShop = null
    clusterPopup.visible = false
  })
  map.on('zoomchange', scheduleRenderMarkers)
  map.on('moveend', scheduleRenderMarkers)
  scheduleRenderMarkers()
}

// 把坐标精度截断到小数点后4位（约11米），相当于"同一栋楼"
function coordKey(lat, lng) {
  return `${parseFloat(lat).toFixed(4)},${parseFloat(lng).toFixed(4)}`
}

function getClusterCellSize(zoom) {
  if (zoom >= 16) return 0
  if (zoom >= 15) return 16
  if (zoom >= 14) return 24
  if (zoom >= 13) return 36
  return 48
}

function groupShopsByCoordinate() {
  const groups = new Map()
  shopsStore.shops.forEach(shop => {
    if (!shop.lat || !shop.lng) return
    const lat = Number(shop.lat)
    const lng = Number(shop.lng)
    const key = coordKey(lat, lng)
    if (!groups.has(key)) {
      groups.set(key, { shops: [], lat, lng })
    }
    groups.get(key).shops.push(shop)
  })
  return Array.from(groups.values())
}

function buildClusters() {
  const coordGroups = groupShopsByCoordinate()
  const cellSize = getClusterCellSize(map.getZoom())
  if (!cellSize) return coordGroups

  const clusters = new Map()

  coordGroups.forEach(group => {
    const pixel = map.lngLatToContainer([group.lng, group.lat])
    const key = `${Math.floor(pixel.x / cellSize)},${Math.floor(pixel.y / cellSize)}`
    const weight = group.shops.length

    if (!clusters.has(key)) {
      clusters.set(key, { shops: [], latSum: 0, lngSum: 0, shopCount: 0 })
    }

    const cluster = clusters.get(key)
    cluster.shops.push(...group.shops)
    cluster.latSum += group.lat * weight
    cluster.lngSum += group.lng * weight
    cluster.shopCount += weight
  })

  return Array.from(clusters.values()).map(cluster => ({
    shops: cluster.shops,
    lat: cluster.latSum / cluster.shopCount,
    lng: cluster.lngSum / cluster.shopCount,
  }))
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

function scheduleRenderMarkers() {
  if (renderFrame) cancelAnimationFrame(renderFrame)
  renderFrame = requestAnimationFrame(() => {
    renderFrame = 0
    renderMarkers()
  })
}

function openClusterPopup(lng, lat, shops) {
  const pixel = map.lngLatToContainer([lng, lat])
  const rect = mapContainer.value.getBoundingClientRect()
  const popupWidth = isMobileViewport.value ? Math.min(window.innerWidth - 24, 256) : 256
  const popupHeight = Math.min(window.innerHeight - 24, 44 + shops.length * 40)
  const margin = 12
  const rawX = rect.left + pixel.x + 16
  const rawY = rect.top + pixel.y - 8

  clusterPopup.x = Math.max(margin, Math.min(rawX, window.innerWidth - popupWidth - margin))
  clusterPopup.y = Math.max(margin, Math.min(rawY, window.innerHeight - popupHeight - margin))
  clusterPopup.shops = shops
  clusterPopup.visible = true
  suppressMapClickUntil = Date.now() + 300
}

function renderMarkers() {
  if (!map) return
  map.remove(mapObjects)
  mapObjects = []
  clusterPopup.visible = false

  const highlightSet = new Set(shopsStore.highlightedIds)
  const hasFilter = highlightSet.size > 0
  const clusters = buildClusters()

  clusters.forEach(({ shops, lat, lng }) => {
    const isMulti = shops.length > 1
    const isHighlighted = !hasFilter || shops.some(s => highlightSet.has(s.id))

    const colorCount = {}
    shops.forEach(s => { colorCount[s.color] = (colorCount[s.color] || 0) + 1 })
    const mainColor = Object.entries(colorCount).sort((a, b) => b[1] - a[1])[0][0]
    const fillColor = COLOR_HEX[mainColor] || '#6b7280'

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
        openClusterPopup(lng, lat, shops)
      } else {
        shopsStore.selectShop(shops[0].id)
      }
    }

    marker.on('click', handleClick)
    mapObjects.push(marker)
    map.add(marker)

    // 单店名称标签（高亮时显示），pin 右侧中部
    if (!isMulti && isHighlighted) {
      const label = new window.AMap.Text({
        text: shops[0].name,
        position: [lng, lat],
        anchor: 'middle-left',
        offset: new window.AMap.Pixel(Math.round(pinW / 2) + 2, -Math.round(pinH * 0.59)),
        zIndex: 130,
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
  if (!map || !window.AMap) return

  // 加载定位插件
  window.AMap.plugin('AMap.Geolocation', function() {
    const geolocation = new window.AMap.Geolocation({
      enableHighAccuracy: true, // 设置为高精度定位
      timeout: 8000,            // 超过8秒后停止定位
      showButton: false,        // 不显示默认的定位按钮
      showMarker: false,        // 不显示默认的定位点
      showCircle: false,        // 不显示默认的定位精度圈
    })

    geolocation.getCurrentPosition(function(status, result) {
      if (status === 'complete') {
        // 获取正确的 GCJ-02 经纬度
        const { lng, lat } = result.position
        shopsStore.setUserLocation({ lat, lng })

        map.setCenter([lng, lat])
        map.setZoom(15)

        if (locationMarker) map.remove(locationMarker)
        locationMarker = new window.AMap.CircleMarker({
          center: [lng, lat],
          radius: 8,
          strokeColor: '#fff',
          strokeWeight: 2,
          fillColor: '#3b82f6',
          fillOpacity: 1,
          zIndex: 200,
        })
        map.add(locationMarker)
      } else {
        shopsStore.setUserLocation(null)
        console.warn('定位失败:', result.message)
      }
    })
  })
}

onMounted(async () => {
  updateViewportFlags()
  window.addEventListener('resize', updateViewportFlags)
  await loadAmapScript()
  initMap()
})

onUnmounted(() => {
  if (renderFrame) cancelAnimationFrame(renderFrame)
  window.removeEventListener('resize', updateViewportFlags)
  if (map) map.destroy()
})

watch(() => shopsStore.shops, scheduleRenderMarkers, { deep: true })
watch(() => shopsStore.highlightedIds, scheduleRenderMarkers, { deep: true })

defineExpose({ locateUser })
</script>
