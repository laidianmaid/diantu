<template>
  <div class="bg-white rounded-xl shadow-lg p-4 w-72 max-h-96 overflow-y-auto">
    <div v-if="!authStore.user">
      <p class="text-sm text-gray-600 mb-3">登录后可评论、收藏、打卡</p>
      <router-link to="/auth" class="block w-full text-center py-2 bg-amber-500 text-white rounded-lg text-sm hover:bg-amber-600 transition">登录 / 注册</router-link>
    </div>
    <div v-else>
      <div class="flex items-center gap-3 mb-4">
        <div class="w-10 h-10 rounded-full bg-amber-100 flex items-center justify-center font-bold text-amber-700">
          {{ authStore.user.username[0]?.toUpperCase() }}
        </div>
        <div>
          <p class="font-medium text-gray-900 text-sm">{{ authStore.user.username }}</p>
          <p class="text-xs text-gray-500">{{ authStore.user.role }} · 权重 {{ authStore.user.weight.toFixed(2) }}</p>
        </div>
      </div>
      <div class="space-y-2">
        <button @click="genApiKey" class="w-full text-left text-sm px-3 py-2 rounded-lg hover:bg-gray-50 text-gray-700 transition">
          🔑 生成 API Key
        </button>
        <p v-if="apiKey" class="text-xs bg-gray-50 rounded p-2 break-all font-mono text-gray-500">{{ apiKey }}</p>
        <button @click="authStore.logout" class="w-full text-left text-sm px-3 py-2 rounded-lg hover:bg-red-50 text-red-500 transition">
          退出登录
        </button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { authApi } from '../api'
import { useAuthStore } from '../stores/auth'

const authStore = useAuthStore()
const apiKey = ref('')

async function genApiKey() {
  const { data } = await authApi.generateApiKey()
  apiKey.value = data.api_key
}
</script>
