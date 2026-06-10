import { defineStore } from 'pinia'
import { ref } from 'vue'
import { authApi } from '../api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)

  async function login(email, password) {
    const { data } = await authApi.login({ email, password })
    localStorage.setItem('access_token', data.access_token)
    localStorage.setItem('refresh_token', data.refresh_token)
    await fetchMe()
  }

  async function register(username, email, password, role) {
    await authApi.register({ username, email, password, role })
    await login(email, password)
  }

  async function fetchMe() {
    try {
      const { data } = await authApi.me()
      user.value = data
    } catch {
      user.value = null
    }
  }

  function logout() {
    localStorage.removeItem('access_token')
    localStorage.removeItem('refresh_token')
    user.value = null
  }

  if (localStorage.getItem('access_token')) fetchMe()

  return { user, loading, login, register, logout, fetchMe }
})
