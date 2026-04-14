<template>
  <div class="card">
    <div class="flex flex-wrap gap-3 items-end">
      <!-- Выбор категории -->
      <div class="flex-1 min-w-[180px]">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Категория</label>
        <DropdownSelect
          v-model="store.selectedCategory"
          :options="categoryOptions"
          placeholder="Все категории"
        />
      </div>

      <!-- Частота подсчёта -->
      <div class="flex-1 min-w-[160px]">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Частота подсчёта</label>
        <DropdownSelect
          v-model="store.selectedFrequency"
          :options="frequencyOptions"
          placeholder="Все"
        />
      </div>

      <!-- Статус -->
      <div class="flex-1 min-w-[160px]">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Статус</label>
        <DropdownSelect
          v-model="store.selectedStatus"
          :options="statusOptions"
          placeholder="Все"
        />
      </div>

      <!-- Поиск -->
      <div class="flex-1 min-w-[200px]">
        <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Поиск</label>
        <div class="relative">
          <input
            v-model="store.searchQuery"
            type="text"
            placeholder="Название группы..."
            class="w-full px-3 py-2 pr-9 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors hover:border-gray-400 dark:hover:border-gray-500 placeholder:text-gray-500 dark:placeholder:text-gray-400 text-gray-900 dark:text-gray-100"
          />
          <button 
            v-if="store.searchQuery"
            @click="store.searchQuery = ''"
            class="absolute right-2 top-1/2 -translate-y-1/2 w-5 h-5 flex items-center justify-center text-gray-400 hover:text-gray-600 rounded-full hover:bg-gray-100 transition-colors"
          >
            ×
          </button>
          <svg v-else class="w-4 h-4 absolute right-3 top-1/2 -translate-y-1/2 text-gray-400 pointer-events-none" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
          </svg>
        </div>
      </div>

      <!-- Сброс фильтров -->
      <button 
        @click="store.clearFilters()" 
        class="btn btn-secondary whitespace-nowrap"
      >
        Сбросить
      </button>
    </div>

    <!-- Активные фильтры -->
    <div v-if="hasActiveFilters" class="mt-3 flex flex-wrap gap-2">
      <span class="text-sm text-gray-500 dark:text-gray-400">Фильтры:</span>
      <span v-if="store.selectedCategory" class="badge badge-gray">
        {{ store.selectedCategory }}
        <button @click="store.selectedCategory = ''" class="ml-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">×</button>
      </span>
      <span v-if="store.selectedFrequency" class="badge badge-gray">
        🔄 {{ store.selectedFrequency }}
        <button @click="store.selectedFrequency = ''" class="ml-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">×</button>
      </span>
      <span v-if="store.selectedStatus" class="badge badge-gray">
        {{ statusLabel }}
        <button @click="store.selectedStatus = ''" class="ml-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">×</button>
      </span>
      <span v-if="store.searchQuery" class="badge badge-gray">
        "{{ store.searchQuery }}"
        <button @click="store.searchQuery = ''" class="ml-1 text-gray-400 dark:text-gray-500 hover:text-gray-600 dark:hover:text-gray-300">×</button>
      </span>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useInventoryStore } from '@/stores/inventory'
import DropdownSelect from '@/components/DropdownSelect.vue'

const store = useInventoryStore()

const hasActiveFilters = computed(() =>
  store.selectedCategory || store.selectedStatus || store.selectedFrequency || store.searchQuery
)

const categoryOptions = computed(() =>
  store.categories.map(c => ({ value: c, label: c }))
)

const frequencyOptions = computed(() =>
  store.frequencies.map(f => ({ value: f, label: f }))
)

const statusOptions = computed(() => [
  { value: 'counted', label: '✅ Посчитано' },
  { value: 'partial', label: '⏳ Частично' },
  { value: 'not_counted', label: '❌ Не начато' },
])

const statusLabel = computed(() => {
  const labels = {
    counted: '✅ Посчитано',
    partial: '⏳ Частично',
    not_counted: '❌ Не начато',
  }
  return labels[store.selectedStatus] || ''
})
</script>
