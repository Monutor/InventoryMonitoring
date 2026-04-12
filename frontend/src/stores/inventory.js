import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

const API_BASE = import.meta.env.VITE_API_BASE || ''

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
  const loading = ref(false)
  const connected = ref(false)
  const lastUpdate = ref(null)
  const notifications = ref([])
  const fileName = ref('')

  // Filters
  const selectedCategory = ref('')
  const selectedStatus = ref('')
  const searchQuery = ref('')

  // Computed
  const filteredGroups = computed(() => {
    let result = groups.value

    if (selectedCategory.value) {
      result = result.filter(g => g.Категория === selectedCategory.value)
    }
    if (selectedStatus.value) {
      if (selectedStatus.value === 'counted') {
        result = result.filter(g => g.Доля === 100)
      } else if (selectedStatus.value === 'partial') {
        result = result.filter(g => g.Доля > 0 && g.Доля < 100)
      } else if (selectedStatus.value === 'not_counted') {
        result = result.filter(g => g.Доля === 0)
      } else if (selectedStatus.value === 'manual') {
        result = result.filter(g => g.is_manual)
      }
    }
    if (searchQuery.value) {
      const q = searchQuery.value.toLowerCase()
      result = result.filter(g => 
        g.Группа.toLowerCase().includes(q) || 
        g.Группа_ID?.toLowerCase().includes(q) ||
        g.Подкатегория?.toLowerCase().includes(q)
      )
    }

    return result
  })

  const hasDiscrepancies = computed(() => {
    return filteredGroups.value.filter(g => 
      g.Излишки > 0 || g.Недостачи > 0 || g.Брак > 0
    )
  })

  // Actions
  async function fetchAll() {
    loading.value = true
    try {
      const [groupsRes, statsRes, storesRes, categoriesRes] = await Promise.all([
        fetch(`${API_BASE}/api/groups`),
        fetch(`${API_BASE}/api/stats`),
        fetch(`${API_BASE}/api/stores`),
        fetch(`${API_BASE}/api/categories`),
      ])

      if (groupsRes.ok) {
        const data = await groupsRes.json()
        groups.value = data.groups || []
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

      lastUpdate.value = new Date().toISOString()
    } catch (e) {
      console.error('Error fetching data:', e)
    } finally {
      loading.value = false
    }
  }

  function connectWebSocket() {
    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const wsUrl = `${protocol}//${window.location.host}/ws`
    
    const ws = new WebSocket(wsUrl)

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
        if (message.type === 'initial' || message.type === 'update') {
          const data = message.data
          console.log('[WS]', message.type, 'summary:', data.summary)
          groups.value = data.groups || []
          if (data.summary) {
            stats.value = {
              ...stats.value,
              ...data.summary,
            }
          }
          fileName.value = data.file_name || ''
          lastUpdate.value = message.timestamp || new Date().toISOString()

          if (message.type === 'update') {
            addNotification('Данные обновлены', `Файл: ${fileName.value}`, 'info')
          }
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

  async function uploadFile(file) {
    const formData = new FormData()
    formData.append('file', file)

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
      await fetchAll()
      return result
    } catch (e) {
      addNotification('Ошибка загрузки', e.message, 'error')
      throw e
    }
  }

  async function submitManualCount(groupId, storeName, foundCount, totalPlanned, surplus, shortage, defect) {
    const response = await fetch(`${API_BASE}/api/count/${encodeURIComponent(groupId)}`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        store: storeName,
        found_count: foundCount,
        total_planned: totalPlanned,
        surplus,
        shortage,
        defect,
      }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Ошибка сохранения')
    }

    const result = await response.json()
    addNotification('Группа отмечена', `${result.data.found_count} шт. найдено`, 'success')
    await fetchAll()
    return result
  }

  async function removeManualCount(groupId, storeName, groupName) {
    const response = await fetch(`${API_BASE}/api/count/${encodeURIComponent(groupId)}`, {
      method: 'DELETE',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ store: storeName }),
    })

    if (!response.ok) {
      const error = await response.json()
      throw new Error(error.detail || 'Ошибка сброса')
    }

    addNotification('Отметка сброшена', `Результат для "${groupName}" сброшен`, 'info')
    await fetchAll()
  }

  function clearFilters() {
    selectedCategory.value = ''
    selectedStatus.value = ''
    searchQuery.value = ''
  }

  return {
    groups,
    stats,
    stores,
    categories,
    loading,
    connected,
    lastUpdate,
    notifications,
    fileName,
    theme,
    toggleTheme,
    selectedCategory,
    selectedStatus,
    searchQuery,
    filteredGroups,
    hasDiscrepancies,
    fetchAll,
    connectWebSocket,
    addNotification,
    removeNotification,
    uploadFile,
    submitManualCount,
    removeManualCount,
    clearFilters,
  }
})
