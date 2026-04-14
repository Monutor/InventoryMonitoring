import { defineStore } from 'pinia'
import { ref, computed, watch } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || ''

// Адаптивный размер страницы: мобилка — 15, десктоп — 30
function getPageSize() {
  return window.innerWidth < 768 ? 15 : 30
}

function getInitialTheme() {
  const saved = localStorage.getItem('theme')
  if (saved === 'dark' || saved === 'light') return saved
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light'
}

function applyTheme(theme) {
  if (theme === 'dark') {
    document.documentElement.classList.add('dark')
  } else {
    document.documentElement.classList.remove('dark')
  }
  localStorage.setItem('theme', theme)
}

export const useInventoryStore = defineStore('inventory', () => {
  // Theme
  const theme = ref(getInitialTheme())

  function toggleTheme() {
    theme.value = theme.value === 'dark' ? 'light' : 'dark'
    applyTheme(theme.value)
  }

  // State
  const groups = ref([])
  const stats = ref({
    total_groups: 0,
    counted_groups: 0,
    partial_groups: 0,
    not_counted_groups: 0,
    counted_percentage: 0,
    total_items: 0,
    total_found: 0,
    total_surplus: 0,
    total_shortage: 0,
    total_defect: 0,
  })
  const stores = ref([])
  const categories = ref([])
  const frequencies = ref([])
  const loading = ref(false)
  const loadingMore = ref(false)
  const searchLoading = ref(false)
  const connected = ref(false)
  const lastUpdate = ref(null)
  const notifications = ref([])
  const fileName = ref('')

  // Pagination state
  const currentPage = ref(0)
  const hasMore = ref(true)
  const totalGroups = ref(0)
  const loadingInitial = ref(false)

  // Filters
  const selectedCategory = ref('')
  const selectedStatus = ref('')
  const selectedFrequency = ref('')
  const searchQuery = ref('')

  // Debounce timer для поиска
  let searchDebounceTimer = null
  // Timer для задержки показа скелетона при смене фильтров
  let filterLoadingTimer = null

  // Фильтры категории/статуса/частоты — скелетон через 300мс если запрос ещё не завершён
  watch([selectedCategory, selectedStatus, selectedFrequency], () => {
    filterLoadingTimer = setTimeout(() => {
      searchLoading.value = true
    }, 300)
    fetchInitial().finally(() => {
      clearTimeout(filterLoadingTimer)
      searchLoading.value = false
    })
  })

  // Поиск — с debounce 1000мс (чтобы не дёргать API на каждый символ)
  watch(searchQuery, () => {
    clearTimeout(searchDebounceTimer)
    searchLoading.value = true
    searchDebounceTimer = setTimeout(() => {
      fetchInitial().finally(() => {
        searchLoading.value = false
      })
    }, 1000)
  })

  function resetPagination() {
    groups.value = []
    currentPage.value = 0
    hasMore.value = true
    totalGroups.value = 0
    resetCache()
  }

  // Фильтр-кэш: ключ → { groups, total, hasMore }
  const filterCache = new Map()
  const MAX_CACHE_SIZE = 10

  function getCacheKey() {
    return JSON.stringify({
      category: selectedCategory.value,
      frequency: selectedFrequency.value,
      status: selectedStatus.value,
      search: searchQuery.value,
    })
  }

  function resetCache() {
    filterCache.clear()
  }

  // Computed — groups уже отфильтрованы сервером
  const filteredGroups = computed(() => groups.value)

  const hasDiscrepancies = computed(() => {
    return groups.value.filter(g =>
      g.Излишки > 0 || g.Недостачи > 0 || g.Брак > 0
    )
  })

  // Actions
  async function fetchStoresAndCategories() {
    try {
      const [storesRes, categoriesRes] = await Promise.all([
        fetch(`${API_BASE}/api/stores`),
        fetch(`${API_BASE}/api/categories`),
      ])
      if (storesRes.ok) {
        const data = await storesRes.json()
        stores.value = data.stores || []
      }
      if (categoriesRes.ok) {
        const data = await categoriesRes.json()
        categories.value = data.categories || []
      }
    } catch (e) {
      console.error('Error fetching stores/categories:', e)
    }
  }

  async function fetchInitial() {
    if (loadingInitial.value) return // Prevent parallel requests

    const cacheKey = getCacheKey()

    // Проверяем кэш
    if (filterCache.has(cacheKey)) {
      const cached = filterCache.get(cacheKey)
      groups.value = cached.groups
      totalGroups.value = cached.total
      hasMore.value = cached.hasMore
      currentPage.value = 0
      lastUpdate.value = new Date().toISOString()
      loading.value = false
      loadingInitial.value = false
      return // Используем кэш, без запроса
    }

    loadingInitial.value = true
    loading.value = true
    try {
      const params = new URLSearchParams()
      params.set('limit', String(getPageSize()))
      params.set('offset', '0')
      if (selectedCategory.value) params.set('category', selectedCategory.value)
      if (selectedFrequency.value) params.set('frequency', selectedFrequency.value)
      if (selectedStatus.value) params.set('status', selectedStatus.value)
      if (searchQuery.value) params.set('search', searchQuery.value)

      const [groupsRes, statsRes, storesRes, categoriesRes, frequenciesRes] = await Promise.all([
        fetch(`${API_BASE}/api/groups?${params}`),
        fetch(`${API_BASE}/api/stats`),
        fetch(`${API_BASE}/api/stores`),
        fetch(`${API_BASE}/api/categories`),
        fetch(`${API_BASE}/api/frequencies`),
      ])

      if (groupsRes.ok) {
        const data = await groupsRes.json()
        const newGroups = data.groups || []
        const newTotal = data.total || 0
        const newHasMore = data.has_more ?? false

        groups.value = newGroups
        totalGroups.value = newTotal
        hasMore.value = newHasMore
        currentPage.value = 0

        // Сохраняем в кэш (LRU: удаляем oldest при переполнении)
        if (filterCache.size >= MAX_CACHE_SIZE) {
          const firstKey = filterCache.keys().next().value
          filterCache.delete(firstKey)
        }
        filterCache.set(cacheKey, {
          groups: newGroups,
          total: newTotal,
          hasMore: newHasMore,
        })
      }
      if (statsRes.ok) {
        stats.value = await statsRes.json()
      }
      if (storesRes.ok) {
        const data = await storesRes.json()
        stores.value = data.stores || []
      }
      if (categoriesRes.ok) {
        const data = await categoriesRes.json()
        categories.value = data.categories || []
      }
      if (frequenciesRes.ok) {
        const data = await frequenciesRes.json()
        frequencies.value = data.frequencies || []
      }

      lastUpdate.value = new Date().toISOString()
    } catch (e) {
      console.error('Error fetching data:', e)
    } finally {
      loading.value = false
      loadingInitial.value = false
    }
  }

  async function loadMore() {
    if (loadingMore.value || !hasMore.value || loading.value) return

    loadingMore.value = true
    try {
      const nextPage = currentPage.value + 1
      const offset = nextPage * getPageSize()

      const params = new URLSearchParams()
      params.set('limit', String(getPageSize()))
      params.set('offset', String(offset))
      if (selectedCategory.value) params.set('category', selectedCategory.value)
      if (selectedFrequency.value) params.set('frequency', selectedFrequency.value)
      if (selectedStatus.value) params.set('status', selectedStatus.value)
      if (searchQuery.value) params.set('search', searchQuery.value)

      const response = await fetch(`${API_BASE}/api/groups?${params}`)
      if (response.ok) {
        const data = await response.json()
        groups.value = [...groups.value, ...(data.groups || [])]
        totalGroups.value = data.total || totalGroups.value
        hasMore.value = data.has_more ?? false
        currentPage.value = nextPage
      }
    } catch (e) {
      console.error('Error loading more:', e)
    } finally {
      loadingMore.value = false
    }
  }

  function connectWebSocket() {
    // Определяем WS URL на основе API_BASE (для GitHub Pages / других хостов)
    let wsHost
    if (API_BASE) {
      const url = new URL(API_BASE)
      const protocol = url.protocol === 'https:' ? 'wss:' : 'ws:'
      wsHost = `${protocol}//${url.host}/ws`
    } else {
      // Fallback для локальной разработки
      const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      wsHost = `${protocol}//${window.location.host}/ws`
    }

    const ws = new WebSocket(wsHost)

    // Fallback: если WS не ответил за 3 секунды, загружаем данные через REST
    let wsReady = false
    const wsTimeout = setTimeout(() => {
      if (!wsReady && groups.value.length === 0) {
        console.log('[WS] Timeout, falling back to REST')
        fetchInitial()
      }
    }, 3000)

    ws.onopen = () => {
      connected.value = true
      console.log('WebSocket connected')
    }

    ws.onclose = () => {
      connected.value = false
      console.log('WebSocket disconnected, reconnecting...')
      setTimeout(connectWebSocket, 3000)
    }

    ws.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    ws.onmessage = (event) => {
      // Игнорируем ping/pong и не-JSON ответы
      if (typeof event.data === 'string' && (event.data === 'pong' || event.data === 'ping')) {
        return
      }
      try {
        const message = JSON.parse(event.data)
        
        if (message.type === 'initial') {
          wsReady = true
          clearTimeout(wsTimeout)
          // При первом подключении принимаем только summary из WS
          const data = message.data
          console.log('[WS] initial received, summary:', data.summary)

          // Обновляем статистику
          if (data.summary) {
            stats.value = {
              ...stats.value,
              ...data.summary,
            }
          }
          fileName.value = data.file_name || ''
          lastUpdate.value = message.timestamp || new Date().toISOString()

          // Группы загружаем через REST API (с пагинацией)
          fetchInitial()
        }
        
        if (message.type === 'update') {
          // При обновлении (новый файл или ручной ввод) перезагружаем данные
          const data = message.data
          console.log('[WS] update received, summary:', data.summary)

          // Обновляем статистику
          if (data.summary) {
            stats.value = {
              ...stats.value,
              ...data.summary,
            }
          }
          if (data.file_name) fileName.value = data.file_name
          lastUpdate.value = message.timestamp || new Date().toISOString()

          const pct = data.summary?.counted_percentage ?? 0
          addNotification('Данные обновлены', `Готовность: ${pct}%`, 'info')

          // Перезагружаем с начала (новый файл — полная замена данных)
          resetPagination()
          fetchInitial()
        }
      } catch (e) {
        console.error('Error parsing WS message:', e)
      }
    }

    // Ping every 30s to keep connection alive
    setInterval(() => {
      if (ws.readyState === WebSocket.OPEN) {
        ws.send('ping')
      }
    }, 30000)
  }

  function addNotification(title, message, type = 'info') {
    const id = Date.now()
    notifications.value.push({ id, title, message, type })
    // Auto-remove after 5 seconds
    setTimeout(() => {
      notifications.value = notifications.value.filter(n => n.id !== id)
    }, 5000)
  }

  function removeNotification(id) {
    notifications.value = notifications.value.filter(n => n.id !== id)
  }

  async function uploadFile(file, skipHeaderRows = 0) {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('skip_header_rows', String(skipHeaderRows))

    try {
      const response = await fetch(`${API_BASE}/api/upload`, {
        method: 'POST',
        body: formData,
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.detail || 'Ошибка загрузки')
      }

      const result = await response.json()
      addNotification('Файл загружен', result.message, 'success')
      resetPagination()
      await fetchInitial()
      return result
    } catch (e) {
      addNotification('Ошибка загрузки', e.message, 'error')
      throw e
    }
  }

  function clearFilters() {
    clearTimeout(searchDebounceTimer)
    clearTimeout(filterLoadingTimer)
    selectedCategory.value = ''
    selectedStatus.value = ''
    selectedFrequency.value = ''
    searchQuery.value = ''
  }

  return {
    groups,
    stats,
    stores,
    categories,
    loading,
    loadingMore,
    searchLoading,
    loadingInitial,
    connected,
    lastUpdate,
    notifications,
    fileName,
    theme,
    toggleTheme,
    selectedCategory,
    selectedStatus,
    selectedFrequency,
    searchQuery,
    filteredGroups,
    hasDiscrepancies,
    hasMore,
    totalGroups,
    frequencies,
    fetchInitial,
    fetchAll: fetchInitial, // alias for backwards compatibility
    loadMore,
    connectWebSocket,
    addNotification,
    removeNotification,
    uploadFile,
    clearFilters,
    resetCache,
  }
})
