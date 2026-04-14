<template>
  <div class="card animate-pulse">
    <!-- Заголовок -->
    <div class="flex items-start justify-between mb-3">
      <div class="flex-1">
        <div class="h-5 bg-gray-200 dark:bg-gray-700 rounded w-3/4 mb-2"></div>
        <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-1/2"></div>
      </div>
      <div class="h-6 bg-gray-200 dark:bg-gray-700 rounded-full w-16"></div>
    </div>

    <!-- Статус -->
    <div class="flex items-center gap-2 mb-3">
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-20"></div>
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-16"></div>
    </div>

    <!-- Прогресс-бар -->
    <div class="mb-3">
      <div class="h-2 bg-gray-200 dark:bg-gray-700 rounded-full w-full"></div>
    </div>

    <!-- Статистика -->
    <div class="grid grid-cols-2 gap-2">
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-full"></div>
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-2/3"></div>
      <div class="h-4 bg-gray-200 dark:bg-gray-700 rounded w-3/4"></div>
    </div>
  </div>
</template>
