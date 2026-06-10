<template>
  <div class="relative w-full h-screen overflow-hidden bg-gray-100">
    <!-- Map Layer -->
    <MapView ref="mapViewRef" class="absolute inset-0" />

    <!-- Top Controls — shrink right edge when sidebar is open -->
    <div
      class="absolute top-4 left-4 z-10 flex flex-col gap-2 pointer-events-none transition-[right] duration-300 ease-in-out"
      :style="{ right: panelOpen ? 'calc(24rem + 1rem)' : '1rem' }"
    >
      <div class="flex items-center gap-2 pointer-events-auto">
        <div class="bg-white/95 backdrop-blur rounded-xl shadow-md px-4 py-2 flex items-center gap-2">
          <span class="text-lg">☕</span>
          <span class="font-semibold text-gray-800 text-sm hidden sm:block">来点妹抖吗？</span>
        </div>
        <button
          @click="mapViewRef?.locateUser()"
          title="定位到我的位置"
          class="bg-blue-500 hover:bg-blue-600 backdrop-blur rounded-xl shadow-md px-3 py-2 text-sm text-white transition"
        >◎</button>
        <div class="flex-1" />
        <button
          @click="showUserPanel = !showUserPanel"
          class="bg-white/95 backdrop-blur rounded-xl shadow-md px-3 py-2 text-sm font-medium text-gray-700 hover:bg-white transition"
        >
          {{ authStore.user ? authStore.user.username[0].toUpperCase() : '👤' }}
        </button>
      </div>

      <div class="pointer-events-auto">
        <FilterBar />
      </div>

      <div class="pointer-events-auto">
        <AiChat />
      </div>
    </div>

    <!-- User Panel Dropdown — follows the user button -->
    <div
      v-if="showUserPanel"
      class="absolute top-16 z-20 transition-[right] duration-300 ease-in-out"
      :style="{ right: panelOpen ? 'calc(24rem + 1rem)' : '1rem' }"
    >
      <UserPanel />
    </div>

    <!-- Shop Detail Panel (layer 2) -->
    <!-- Desktop/Tablet: right sidebar -->
    <transition name="slide-right">
      <div
        v-if="shopsStore.selectedShop && !isMobile"
        class="absolute top-0 right-0 bottom-0 z-10 w-96 shadow-xl border-l border-gray-100"
      >
        <ShopPanel :shop="shopsStore.selectedShop" @close="shopsStore.selectedShop = null" />
      </div>
    </transition>

    <!-- Mobile: bottom drawer -->
    <transition name="slide-up">
      <div
        v-if="shopsStore.selectedShop && isMobile"
        class="absolute left-0 right-0 bottom-0 z-10 h-3/4 rounded-t-2xl shadow-xl overflow-hidden"
      >
        <div class="w-10 h-1 bg-gray-300 rounded-full mx-auto mt-3 mb-2" />
        <ShopPanel :shop="shopsStore.selectedShop" @close="shopsStore.selectedShop = null" />
      </div>
    </transition>

    <!-- Click outside to close user panel -->
    <div v-if="showUserPanel" class="absolute inset-0 z-[15]" @click="showUserPanel = false" />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'
import MapView from '../components/MapView.vue'
import FilterBar from '../components/FilterBar.vue'
import AiChat from '../components/AiChat.vue'
import ShopPanel from '../components/ShopPanel.vue'
import UserPanel from '../components/UserPanel.vue'
import { useShopsStore } from '../stores/shops'
import { useAuthStore } from '../stores/auth'

const shopsStore = useShopsStore()
const authStore = useAuthStore()
const showUserPanel = ref(false)
const windowWidth = ref(window.innerWidth)
const mapViewRef = ref(null)

const isMobile = computed(() => windowWidth.value < 768)
const panelOpen = computed(() => !!shopsStore.selectedShop && !isMobile.value)

function onResize() { windowWidth.value = window.innerWidth }
onMounted(() => window.addEventListener('resize', onResize))
onUnmounted(() => window.removeEventListener('resize', onResize))
</script>

<style scoped>
.slide-right-enter-active, .slide-right-leave-active { transition: transform 0.3s ease; }
.slide-right-enter-from, .slide-right-leave-to { transform: translateX(100%); }
.slide-up-enter-active, .slide-up-leave-active { transition: transform 0.3s ease; }
.slide-up-enter-from, .slide-up-leave-to { transform: translateY(100%); }
</style>
