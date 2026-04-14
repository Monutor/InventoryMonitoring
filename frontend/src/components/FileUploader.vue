<template>
  <div class="card">
    <div class="flex flex-col gap-3">
      <!-- Зона загрузки -->
      <label
        class="flex items-center justify-center gap-3 px-4 py-3 border-2 border-dashed border-gray-300 rounded-lg cursor-pointer hover:border-primary-500 hover:bg-primary-50 transition-colors w-full"
        :class="{ 'border-green-500 bg-green-50': dragOver }"
        @dragover.prevent="dragOver = true"
        @dragleave="dragOver = false"
        @drop.prevent="handleDrop"
      >
        <svg class="w-6 h-6 text-gray-400 dark:text-gray-500" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
        </svg>
        <span class="text-sm text-gray-600 dark:text-gray-400">
          <span class="font-medium text-primary-600">Нажмите для загрузки</span> или перетащите файл
        </span>
        <input
          type="file"
          class="hidden"
          accept=".csv,.xlsx,.xls"
          @change="handleFileSelect"
        />
      </label>

      <!-- Опции загрузки -->
      <div
        class="flex items-center gap-3 p-3 bg-gray-50 dark:bg-gray-800/50 rounded-lg cursor-pointer select-none transition-colors hover:bg-gray-100 dark:hover:bg-gray-800"
        @click="skipHeaderRows = !skipHeaderRows"
      >
        <!-- Кастомный чекбокс -->
        <div
          class="w-5 h-5 rounded-md border-2 flex items-center justify-center shrink-0 transition-all duration-200"
          :class="skipHeaderRows
            ? 'border-primary-500 bg-primary-500 scale-100'
            : 'border-gray-300 dark:border-gray-600 bg-transparent scale-95'"
        >
          <svg
            v-if="skipHeaderRows"
            class="w-3.5 h-3.5 text-white"
            fill="none"
            stroke="currentColor"
            viewBox="0 0 24 24"
          >
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="3" d="M5 13l4 4L19 7" />
          </svg>
        </div>

        <div class="flex flex-col">
          <span class="text-sm font-medium text-gray-700 dark:text-gray-300">
            Пропустить первые 2 строки
          </span>
          <span class="text-xs text-gray-500 dark:text-gray-400">
            Служебные строки SAP: дата, имя отчёта
          </span>
        </div>
      </div>

      <!-- Статус -->
      <div v-if="store.fileName" class="text-sm truncate">
        <span class="text-gray-500 dark:text-gray-400">Текущий файл: </span>
        <span class="font-medium dark:text-gray-200 truncate" :title="store.fileName">{{ store.fileName }}</span>
      </div>
    </div>

    <!-- Прогресс загрузки -->
    <div v-if="uploading" class="mt-3">
      <div class="flex items-center gap-2 text-sm text-gray-600 dark:text-gray-400">
        <svg class="animate-spin h-4 w-4" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" fill="none" />
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
        Загрузка файла...
      </div>
    </div>

    <!-- Поддерживаемые форматы -->
    <div class="mt-2 text-xs text-gray-400">
      Поддерживаемые форматы: CSV, XLSX, XLS
    </div>
  </div>
</template>

<script setup>
import { ref } from 'vue'
import { useInventoryStore } from '@/stores/inventory'

const store = useInventoryStore()
const uploading = ref(false)
const dragOver = ref(false)
const skipHeaderRows = ref(true)

async function handleFileSelect(event) {
  const file = event.target.files[0]
  if (file) {
    await uploadFile(file)
  }
  // Reset input
  event.target.value = ''
}

async function handleDrop(event) {
  dragOver.value = false
  const file = event.dataTransfer.files[0]
  if (file) {
    await uploadFile(file)
  }
}

async function uploadFile(file) {
  uploading.value = true
  try {
    await store.uploadFile(file, skipHeaderRows.value ? 2 : 0)
  } catch (e) {
    console.error('Upload failed:', e)
  } finally {
    uploading.value = false
  }
}
</script>
