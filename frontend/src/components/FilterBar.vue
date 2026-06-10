<template>
  <div class="flex flex-wrap gap-2 p-2 bg-white/90 backdrop-blur rounded-xl shadow-md">
    <button
      v-for="c in colors"
      :key="c.value"
      @click="toggle('color', c.value)"
      class="flex items-center gap-1 px-3 py-1 rounded-full text-sm font-medium border transition"
      :class="active('color', c.value) ? 'border-transparent text-white shadow' : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
      :style="active('color', c.value) ? `background:${c.hex}` : ''"
    >
      <span class="w-3 h-3 rounded-full" :style="`background:${c.hex}`" />
      {{ c.label }}
    </button>
    <div class="w-px bg-gray-200 self-stretch mx-1" />
    <button
      v-for="s in statuses"
      :key="s.value"
      @click="toggle('status', s.value)"
      class="px-3 py-1 rounded-full text-sm font-medium border transition"
      :class="active('status', s.value) ? 'bg-gray-800 text-white border-transparent' : 'border-gray-200 text-gray-600 hover:bg-gray-50'"
    >
      {{ s.label }}
    </button>
    <button @click="clearAll" class="ml-auto text-xs text-gray-400 hover:text-gray-600 px-2">清除</button>
  </div>
</template>

<script setup>
import { useShopsStore } from '../stores/shops'

const shopsStore = useShopsStore()

const colors = [
  { value: 'sagegreen', label: '纯素', hex: '#8FBC8F' },
  { value: 'olivedrab', label: '半绿半素', hex: '#6B8E23' },
  { value: 'seagreen', label: '纯绿', hex: '#2E8B57' },
  { value: 'salmon', label: '半荤半绿', hex: '#FA8072' },
  { value: 'hotpink', label: '纯荤', hex: '#FF69B4' },
]

const statuses = [
  { value: 'open', label: '营业中' },
  { value: 'closed', label: '休息' },
  { value: 'preparing', label: '筹划中' },
  { value: 'shutdown', label: '已闭店' },
]

function active(key, value) {
  return shopsStore.filters[key] === value
}

function toggle(key, value) {
  shopsStore.applyFilter(key, active(key, value) ? null : value)
}

function clearAll() {
  shopsStore.applyFilter('color', null)
  shopsStore.applyFilter('status', null)
}
</script>
