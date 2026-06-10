import { defineStore } from 'pinia'
import { ref } from 'vue'
import { shopApi } from '../api'

export const useShopsStore = defineStore('shops', () => {
  const shops = ref([])
  const selectedShop = ref(null)
  const highlightedIds = ref([])
  const filters = ref({ color: null, status: null, style: null })

  async function fetchShops() {
    const params = Object.fromEntries(Object.entries(filters.value).filter(([, v]) => v))
    const { data } = await shopApi.list(params)
    shops.value = data
  }

  async function selectShop(id) {
    const { data } = await shopApi.get(id)
    selectedShop.value = data
  }

  function setHighlight(ids) {
    highlightedIds.value = ids
  }

  function applyFilter(key, value) {
    filters.value[key] = value || null
    fetchShops()
  }

  fetchShops()

  return { shops, selectedShop, highlightedIds, filters, fetchShops, selectShop, setHighlight, applyFilter }
})
