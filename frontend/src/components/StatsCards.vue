<template>
  <div class="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
    <div class="card text-center">
      <div class="text-2xl font-bold text-gray-900 dark:text-gray-100">{{ stats.total_groups }}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Всего групп</div>
    </div>

    <div class="card text-center border-l-4 border-green-500">
      <div class="text-2xl font-bold text-green-600 dark:text-green-400">{{ stats.counted_groups }}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Посчитано</div>
    </div>

    <div class="card text-center border-l-4 border-yellow-500">
      <div class="text-2xl font-bold text-yellow-600 dark:text-yellow-400">{{ stats.partial_groups }}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Частично</div>
    </div>

    <div class="card text-center border-l-4 border-red-500">
      <div class="text-2xl font-bold text-red-600 dark:text-red-400">{{ stats.not_counted_groups }}</div>
      <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Не начато</div>
    </div>

    <div class="card text-center">
      <div class="text-2xl font-bold text-primary-600 dark:text-primary-400">{{ stats.counted_percentage }}%</div>
      <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Готовность</div>
    </div>

    <div class="card text-center">
      <div class="text-2xl font-bold" :class="hasIssues ? 'text-orange-600 dark:text-orange-400' : 'text-gray-400 dark:text-gray-500'">
        {{ discrepancyCount }}
      </div>
      <div class="text-sm text-gray-500 dark:text-gray-400 mt-1">Расхождения</div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useInventoryStore } from '@/stores/inventory'

const store = useInventoryStore()
const stats = computed(() => store.stats)
const hasDiscrepancies = computed(() => store.hasDiscrepancies)

const hasIssues = computed(() => hasDiscrepancies.value.length > 0)
const discrepancyCount = computed(() => hasDiscrepancies.value.length)
</script>
