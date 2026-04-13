<template>
  <header class="bg-white dark:bg-gray-800 border-b border-gray-200 dark:border-gray-700 sticky top-0 z-40">
    <div class="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
      <div class="flex items-center justify-between h-16">
        <!-- Логотип и название -->
        <div class="flex items-center gap-3">
          <div class="w-8 h-8 bg-primary-600 rounded-lg flex items-center justify-center">
            <svg class="w-5 h-5 text-white" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-3 7h3m-3 4h3m-6-4h.01M9 16h.01" />
            </svg>
          </div>
          <div>
            <h1 class="text-lg font-bold text-gray-900 dark:text-gray-100">Инвентаризация</h1>
            <p class="text-xs text-gray-500">Мониторинг в реальном времени</p>
          </div>
        </div>

        <!-- Статус подключения и обновление -->
        <div class="flex items-center gap-2 sm:gap-4">
          <!-- Индикатор подключения -->
          <div class="flex items-center gap-1.5 sm:gap-2 text-sm">
            <span
              class="w-2 h-2 rounded-full"
              :class="store.connected ? 'bg-green-500' : 'bg-red-500'"
            ></span>
            <span class="text-gray-600 dark:text-gray-400 hidden sm:inline">
              {{ store.connected ? 'Онлайн' : 'Отключено' }}
            </span>
          </div>

          <!-- Время обновления -->
          <div v-if="store.lastUpdate" class="text-xs text-gray-400 dark:text-gray-500 hidden md:block">
            Обновлено: {{ formatTime(store.lastUpdate) }}
          </div>

          <!-- Кнопка обновления -->
          <button
            @click="store.fetchAll()"
            class="btn btn-secondary p-2"
            :disabled="store.loading"
            title="Обновить данные"
          >
            <svg
              class="w-4 h-4"
              :class="{ 'animate-spin': store.loading }"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
            </svg>
          </button>

          <!-- Переключатель темы -->
          <button
            @click="store.toggleTheme()"
            class="btn btn-secondary p-2"
            :title="store.theme === 'dark' ? 'Светлая тема' : 'Тёмная тема'"
          >
            <svg v-if="store.theme === 'dark'" class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 3v1m0 16v1m9-9h-1M4 12H3m15.364 6.364l-.707-.707M6.343 6.343l-.707-.707m12.728 0l-.707.707M6.343 17.657l-.707.707M16 12a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M20.354 15.354A9 9 0 018.646 3.646 9.003 9.003 0 0012 21a9.003 9.003 0 008.354-5.646z" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  </header>
</template>

<script setup>
import { useInventoryStore } from '@/stores/inventory'

const store = useInventoryStore()

function formatTime(isoString) {
  if (!isoString) return ''
  const date = new Date(isoString)
  return date.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit', second: '2-digit' })
}
</script>
