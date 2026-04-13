<template>
  <div class="min-h-screen bg-gray-50 dark:bg-gray-900">
    <!-- Уведомления -->
    <Notifications />

    <!-- Шапка -->
    <AppHeader />

    <!-- Основной контент -->
    <main class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-6">
      <!-- Загрузка при первом запуске -->
      <div v-if="isLoading" class="flex items-center justify-center py-20">
        <div class="text-center">
          <svg class="animate-spin h-12 w-12 text-primary-600 dark:text-primary-400 mx-auto" viewBox="0 0 24 24">
            <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
            <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
          </svg>
          <p class="mt-4 text-gray-600 dark:text-gray-400">Загрузка данных...</p>
        </div>
      </div>

      <template v-else>
        <!-- Статистика -->
        <section class="mb-6">
          <StatsCards />
        </section>

        <!-- Загрузка файла -->
        <section class="mb-6">
          <FileUploader />
        </section>

        <!-- Фильтры -->
        <section class="mb-6">
          <FiltersBar />
        </section>

        <!-- Список групп -->
        <section>
          <!-- Пустое состояние -->
          <div v-if="store.filteredGroups.length === 0" class="card text-center py-12">
            <svg class="w-16 h-16 text-gray-300 dark:text-gray-600 mx-auto" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M20 13V6a2 2 0 00-2-2H6a2 2 0 00-2 2v7m16 0v5a2 2 0 01-2 2H6a2 2 0 01-2-2v-5m16 0h-2.586a1 1 0 00-.707.293l-2.414 2.414a1 1 0 01-.707.293h-3.172a1 1 0 01-.707-.293l-2.414-2.414A1 1 0 006.586 13H4" />
            </svg>
            <h3 class="mt-4 text-lg font-medium text-gray-900 dark:text-gray-100">Нет данных</h3>
            <p class="mt-2 text-sm text-gray-500 dark:text-gray-400">
              Загрузите файл инвентаризации или измените фильтры
            </p>
          </div>

          <!-- Счётчик результатов -->
          <div v-if="store.filteredGroups.length > 0" class="mb-4 flex items-center justify-between">
            <p class="text-sm text-gray-600 dark:text-gray-400">
              Показано: <span class="font-medium">{{ store.filteredGroups.length }}</span> из <span class="font-medium">{{ store.totalGroups }}</span> групп
            </p>
            <!-- Сортировка -->
            <DropdownSelect
              v-model="sortBy"
              :options="sortOptions"
              class="w-[200px]"
            />
          </div>

          <!-- Сетка карточек -->
          <div v-if="sortedGroups.length > 0" class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
            <GroupCard
              v-for="group in sortedGroups"
              :key="group['Группа ID']"
              :group="group"
              @count="openCountModal"
            />
          </div>

          <!-- Sentinel для бесконечного скролла -->
          <div ref="sentinel" class="py-8 text-center">
            <div v-if="store.loadingMore" class="flex items-center justify-center gap-2 text-gray-500 dark:text-gray-400">
              <svg class="animate-spin h-5 w-5" viewBox="0 0 24 24">
                <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
                <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
              </svg>
              <span class="text-sm">Загрузка...</span>
            </div>
            <div v-else-if="!store.hasMore && store.filteredGroups.length > 0" class="text-sm text-gray-400 dark:text-gray-500">
              Все группы загружены
            </div>
          </div>
        </section>
      </template>
    </main>

    <!-- Модалка ручного ввода -->
    <CountModal 
      :group="selectedGroupForCount"
      @close="selectedGroupForCount = null"
      @saved="selectedGroupForCount = null"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useInventoryStore } from '@/stores/inventory'

import StatsCards from '@/components/StatsCards.vue'
import FiltersBar from '@/components/FiltersBar.vue'
import GroupCard from '@/components/GroupCard.vue'
import FileUploader from '@/components/FileUploader.vue'
import Notifications from '@/components/Notifications.vue'
import AppHeader from '@/components/AppHeader.vue'
import DropdownSelect from '@/components/DropdownSelect.vue'
import CountModal from '@/components/CountModal.vue'

const store = useInventoryStore()
const sortBy = ref('status')
const selectedGroupForCount = ref(null)
const sentinel = ref(null)

function openCountModal(group) {
  selectedGroupForCount.value = group
}

const sortOptions = computed(() => [
  { value: 'status', label: '📊 По статусу' },
  { value: 'name', label: '🔤 По названию' },
  { value: 'date', label: '📅 По дате' },
  { value: 'discrepancies', label: '⚠️ С расхождениями' },
])

const isLoading = computed(() => store.loading && store.groups.length === 0)

const sortedGroups = computed(() => {
  let groups = [...store.filteredGroups]

  switch (sortBy.value) {
    case 'status':
      groups.sort((a, b) => {
        const aHasIssues = a.Излишки > 0 || a.Недостачи > 0 || a.Брак > 0
        const bHasIssues = b.Излишки > 0 || b.Недостачи > 0 || b.Брак > 0
        if (aHasIssues && !bHasIssues) return -1
        if (!aHasIssues && bHasIssues) return 1
        return b.Доля - a.Доля
      })
      break
    case 'name':
      groups.sort((a, b) => a['Группа'].localeCompare(b['Группа'], 'ru'))
      break
    case 'date':
      groups.sort((a, b) => {
        if (!a['Дата пересчета']) return 1
        if (!b['Дата пересчета']) return -1
        return b['Дата пересчета'].localeCompare(a['Дата пересчета'])
      })
      break
    case 'discrepancies':
      groups = groups.filter(g =>
        g['Излишки'] > 0 || g['Недостачи'] > 0 || g['Брак'] > 0
      )
      break
  }

  return groups
})

// IntersectionObserver для бесконечного скролла
let observer = null

function setupInfiniteScroll() {
  if (observer) observer.disconnect()

  observer = new IntersectionObserver((entries) => {
    if (entries[0].isIntersecting && store.hasMore && !store.loadingMore) {
      store.loadMore()
    }
  }, { rootMargin: '200px' })

  // Ждём следующий тик, чтобы элемент появился в DOM
  setTimeout(() => {
    if (sentinel.value) {
      observer.observe(sentinel.value)
    }
  }, 100)
}

// Пересоздаём observer при изменении фильтров (с задержкой, чтобы данные обновились)
let filterWatchTimer = null
watch(() => store.filteredGroups.length, () => {
  clearTimeout(filterWatchTimer)
  filterWatchTimer = setTimeout(setupInfiniteScroll, 200)
})

onMounted(async () => {
  store.connectWebSocket()
  // fetchInitial вызывается автоматически при получении WS 'initial'
  setupInfiniteScroll()
})

onUnmounted(() => {
  if (observer) observer.disconnect()
  clearTimeout(filterWatchTimer)
})
</script>
