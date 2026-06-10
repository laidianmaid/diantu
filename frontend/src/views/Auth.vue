<template>
  <div class="min-h-screen bg-amber-50 flex items-center justify-center p-4">
    <div class="bg-white rounded-2xl shadow-lg p-8 w-full max-w-sm">
      <div class="text-center mb-6">
        <div class="text-4xl mb-2">☕</div>
        <h1 class="text-xl font-bold text-gray-900">来点妹抖吗？</h1>
        <p class="text-sm text-gray-500 mt-1">请问您今天要来点妹抖吗？</p>
      </div>

      <div class="flex rounded-lg bg-gray-100 p-1 mb-6">
        <button
          @click="mode = 'login'"
          class="flex-1 py-1.5 rounded-md text-sm font-medium transition"
          :class="mode === 'login' ? 'bg-white shadow text-gray-900' : 'text-gray-500'"
        >登录</button>
        <button
          @click="mode = 'register'"
          class="flex-1 py-1.5 rounded-md text-sm font-medium transition"
          :class="mode === 'register' ? 'bg-white shadow text-gray-900' : 'text-gray-500'"
        >注册</button>
      </div>

      <form @submit.prevent="submit" class="space-y-3">
        <div v-if="mode === 'register'">
          <input v-model="form.username" placeholder="用户名" required
            class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-400" />
        </div>
        <input v-model="form.email" type="email" placeholder="邮箱" required
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-400" />
        <input v-model="form.password" type="password" placeholder="密码" required
          class="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm outline-none focus:border-amber-400" />
        <div v-if="mode === 'register'" class="flex gap-2">
          <button
            type="button"
            @click="form.role = 'user'"
            class="flex-1 py-2 rounded-lg text-sm border transition"
            :class="form.role === 'user' ? 'border-amber-400 bg-amber-50 text-amber-700' : 'border-gray-200 text-gray-600'"
          >我是用户</button>
          <button
            type="button"
            @click="form.role = 'owner'"
            class="flex-1 py-2 rounded-lg text-sm border transition"
            :class="form.role === 'owner' ? 'border-amber-400 bg-amber-50 text-amber-700' : 'border-gray-200 text-gray-600'"
          >我是店长</button>
        </div>
        <p v-if="error" class="text-xs text-red-500">{{ error }}</p>
        <button type="submit" :disabled="loading"
          class="w-full py-2.5 bg-amber-500 text-white rounded-lg text-sm font-medium hover:bg-amber-600 disabled:opacity-50 transition">
          {{ loading ? '...' : (mode === 'login' ? '登录' : '注册') }}
        </button>
      </form>

      <router-link to="/" class="block text-center text-xs text-gray-400 mt-4 hover:text-gray-600">← 返回地图</router-link>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const mode = ref('login')
const loading = ref(false)
const error = ref('')
const form = reactive({ username: '', email: '', password: '', role: 'user' })

async function submit() {
  error.value = ''
  loading.value = true
  try {
    if (mode.value === 'login') {
      await authStore.login(form.email, form.password)
    } else {
      await authStore.register(form.username, form.email, form.password, form.role)
    }
    router.push('/')
  } catch (e) {
    error.value = e.response?.data?.detail || '操作失败，请重试'
  } finally {
    loading.value = false
  }
}
</script>
