<template>
  <div class="relative" ref="dropdownRef">
    <!-- Кнопка-триггер -->
    <button
      @click="isOpen = !isOpen"
      class="w-full flex items-center justify-between px-3 py-2 text-sm bg-white dark:bg-gray-700 border border-gray-300 dark:border-gray-600 rounded-lg shadow-sm focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-primary-500 transition-colors hover:border-gray-400 dark:hover:border-gray-500"
      :class="{ 'border-primary-500 ring-2 ring-primary-200 dark:ring-primary-800': isOpen }"
    >
      <span class="truncate" :class="modelValue ? 'text-gray-900 dark:text-gray-100' : 'text-gray-500 dark:text-gray-400'">
        {{ displayText }}
      </span>
      <svg
        class="w-4 h-4 ml-2 text-gray-400 dark:text-gray-500 flex-shrink-0 transition-transform"
        :class="{ 'rotate-180': isOpen }"
        fill="none" 
        stroke="currentColor" 
        viewBox="0 0 24 24"
      >
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
      </svg>
    </button>

    <!-- Выпадающий список -->
    <Transition
      enter-active-class="transition ease-out duration-150"
      enter-from-class="opacity-0 scale-95 -translate-y-1"
      enter-to-class="opacity-100 scale-100 translate-y-0"
      leave-active-class="transition ease-in duration-100"
      leave-from-class="opacity-100 scale-100 translate-y-0"
      leave-to-class="opacity-0 scale-95 -translate-y-1"
    >
      <div
        v-if="isOpen"
        class="absolute z-50 mt-1 w-full bg-white dark:bg-gray-700 rounded-lg shadow-lg border border-gray-200 dark:border-gray-600 py-1 max-h-60 overflow-auto"
      >
        <!-- Опция "Все" / пустая -->
        <button
          v-if="placeholder"
          @click="select(null)"
          class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors"
          :class="modelValue === null || modelValue === '' ? 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 font-medium' : 'text-gray-700 dark:text-gray-200'"
        >
          {{ placeholder }}
        </button>

        <!-- Разделитель -->
        <div v-if="placeholder" class="my-1 border-t border-gray-100 dark:border-gray-600"></div>

        <!-- Опции -->
        <button
          v-for="option in options"
          :key="option.value"
          @click="select(option.value)"
          class="w-full text-left px-3 py-2 text-sm hover:bg-gray-100 dark:hover:bg-gray-600 transition-colors flex items-center justify-between"
          :class="modelValue === option.value ? 'text-primary-600 dark:text-primary-400 bg-primary-50 dark:bg-primary-900/20 font-medium' : 'text-gray-700 dark:text-gray-200'"
        >
          <span class="truncate">{{ option.label }}</span>
          <svg 
            v-if="modelValue === option.value" 
            class="w-4 h-4 text-primary-600 flex-shrink-0 ml-2" 
            fill="currentColor" 
            viewBox="0 0 20 20"
          >
            <path fill-rule="evenodd" d="M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z" clip-rule="evenodd" />
          </svg>
        </button>

        <!-- Пустое состояние -->
        <div v-if="options.length === 0 && !placeholder" class="px-3 py-2 text-sm text-gray-500">
          Нет вариантов
        </div>
      </div>
    </Transition>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, onUnmounted } from 'vue'

const props = defineProps({
  modelValue: {
    type: [String, Number],
    default: '',
  },
  options: {
    type: Array,
    default: () => [],
  },
  placeholder: {
    type: String,
    default: '',
  },
})

const emit = defineEmits(['update:modelValue'])

const isOpen = ref(false)
const dropdownRef = ref(null)

const displayText = computed(() => {
  if (!props.modelValue) return props.placeholder || 'Выберите...'
  const selected = props.options.find(o => o.value === props.modelValue)
  return selected ? selected.label : props.modelValue
})

function select(value) {
  emit('update:modelValue', value)
  isOpen.value = false
}

// Закрытие при клике вне dropdown
function handleClickOutside(event) {
  if (dropdownRef.value && !dropdownRef.value.contains(event.target)) {
    isOpen.value = false
  }
}

onMounted(() => {
  document.addEventListener('click', handleClickOutside)
})

onUnmounted(() => {
  document.removeEventListener('click', handleClickOutside)
})
</script>

<style scoped>
/* Кастомный скроллбар */
.max-h-60::-webkit-scrollbar {
  width: 6px;
}
.max-h-60::-webkit-scrollbar-track {
  background: #f1f5f9;
}
.max-h-60::-webkit-scrollbar-thumb {
  background: #cbd5e1;
  border-radius: 3px;
}
.max-h-60::-webkit-scrollbar-thumb:hover {
  background: #94a3b8;
}
</style>
