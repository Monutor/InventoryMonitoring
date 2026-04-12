<template>
  <div 
    class="card cursor-pointer"
    :class="{
      'border-l-4 border-green-500': group.Доля === 100,
      'border-l-4 border-yellow-500': group.Доля > 0 && group.Доля < 100,
      'border-l-4 border-red-500': group.Доля === 0,
      'ring-2 ring-primary-500': expanded,
    }"
    @click="expanded = !expanded"
  >
    <!-- Заголовок -->
    <div class="flex items-start justify-between gap-3">
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2">
          <h3 class="font-semibold text-gray-900 dark:text-gray-100 truncate">{{ group['Группа'] }}</h3>
          <span v-if="group.is_manual" class="badge badge-green text-[10px]" title="Ручной ввод">📝</span>
        </div>
        <p class="text-sm text-gray-500 dark:text-gray-400 mt-0.5">{{ group['Подкатегория'] || group['Категория'] }}</p>
      </div>

      <!-- Статус-бейдж -->
      <span :class="statusBadgeClass" class="badge whitespace-nowrap">
        {{ statusText }}
      </span>
    </div>

    <!-- Прогресс-бар -->
    <div class="mt-3">
      <div class="flex items-center justify-between text-sm mb-1">
        <span class="text-gray-500 dark:text-gray-400">Прогресс</span>
        <span class="font-medium dark:text-gray-200">{{ group.Доля }}%</span>
      </div>
      <div class="w-full bg-gray-200 dark:bg-gray-700 rounded-full h-2">
        <div
          class="h-2 rounded-full transition-all duration-500"
          :class="progressBarClass"
          :style="{ width: `${group.Доля}%` }"
        ></div>
      </div>
    </div>

    <!-- Основная статистика -->
    <div class="mt-3 grid grid-cols-3 gap-2 text-sm">
      <div class="text-center">
        <div class="font-medium text-gray-900 dark:text-gray-100">{{ group['Товаров в группе'] || 0 }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Товаров</div>
      </div>
      <div class="text-center">
        <div class="font-medium text-gray-900 dark:text-gray-100">{{ group['Штук в группе'] || 0 }}</div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Штук</div>
      </div>
      <div class="text-center">
        <div class="font-medium" :class="group['Дата пересчета'] ? 'text-gray-900 dark:text-gray-100' : 'text-gray-400 dark:text-gray-500'">
          {{ formatDate(group['Дата пересчета']) }}
        </div>
        <div class="text-xs text-gray-500 dark:text-gray-400">Пересчёт</div>
      </div>
    </div>

    <!-- Раскрытые детали -->
    <div v-if="expanded" class="mt-4 pt-4 border-t border-gray-200 dark:border-gray-700">
      <div class="grid grid-cols-2 gap-3 text-sm">
        <div>
          <span class="text-gray-500 dark:text-gray-400">Группа ID:</span>
          <span class="ml-2 font-mono text-xs text-gray-700 dark:text-gray-300">{{ group['Группа ID'] }}</span>
        </div>
        <div>
          <span class="text-gray-500 dark:text-gray-400">Частота:</span>
          <span class="ml-2 text-gray-700 dark:text-gray-300">{{ group['Частота подсчета'] || '—' }}</span>
        </div>
        <div>
          <span class="text-gray-500 dark:text-gray-400">Найдено:</span>
          <span class="ml-2 font-medium text-gray-900 dark:text-gray-100">{{ group['Найдено'] || 0 }}</span>
        </div>
        <div>
          <span class="text-gray-500 dark:text-gray-400">Посчитано вручную:</span>
          <span class="ml-2 text-gray-700 dark:text-gray-300">{{ group['Посчитано вручную'] || 0 }}</span>
        </div>
      </div>

      <!-- Расхождения -->
      <div v-if="hasDiscrepancies" class="mt-3 pt-3 border-t border-gray-200 dark:border-gray-700">
        <div class="text-sm font-medium text-red-600 dark:text-red-400 mb-2">⚠️ Расхождения</div>
        <div class="grid grid-cols-3 gap-2 text-sm">
          <div class="text-center p-2 bg-orange-50 dark:bg-orange-900/20 rounded">
            <div class="font-medium text-orange-600 dark:text-orange-400">{{ group.Излишки || 0 }}</div>
            <div class="text-xs text-orange-500 dark:text-orange-500">Излишки</div>
          </div>
          <div class="text-center p-2 bg-red-50 dark:bg-red-900/20 rounded">
            <div class="font-medium text-red-600 dark:text-red-400">{{ group.Недостачи || 0 }}</div>
            <div class="text-xs text-red-500 dark:text-red-400">Недостачи</div>
          </div>
          <div class="text-center p-2 bg-yellow-50 dark:bg-yellow-900/20 rounded">
            <div class="font-medium text-yellow-600 dark:text-yellow-400">{{ group.Брак || 0 }}</div>
            <div class="text-xs text-yellow-500 dark:text-yellow-500">Брак</div>
          </div>
        </div>
      </div>

      <!-- Кнопка ручного ввода -->
      <button 
        @click.stop="$emit('count', group)"
        class="mt-4 w-full btn btn-primary"
      >
        <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
        </svg>
        {{ group.is_manual ? '✏️ Изменить результат' : '✏️ Внести результат' }}
      </button>
    </div>
  </div>
</template>

<script setup>
import { ref, computed } from 'vue'

const props = defineProps({
  group: {
    type: Object,
    required: true,
  },
})

defineEmits(['count'])

const expanded = ref(false)

const statusText = computed(() => {
  if (props.group.Доля === 100) return '✅ Готово'
  if (props.group.Доля > 0) return '⏳ В процессе'
  return '❌ Не начато'
})

const statusBadgeClass = computed(() => {
  if (props.group.Доля === 100) return 'badge-green'
  if (props.group.Доля > 0) return 'badge-yellow'
  return 'badge-red'
})

const progressBarClass = computed(() => {
  if (props.group.Доля === 100) return 'bg-green-500'
  if (props.group.Доля > 0) return 'bg-yellow-500'
  return 'bg-red-400'
})

const hasDiscrepancies = computed(() => 
  props.group.Излишки > 0 || props.group.Недостачи > 0 || props.group.Брак > 0
)

function formatDate(dateStr) {
  if (!dateStr) return '—'
  // Формат даты из CSV: ДД.ММ.ГГГГ
  return dateStr
}
</script>
