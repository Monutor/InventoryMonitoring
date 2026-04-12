<template>
  <Teleport to="body">
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="isOpen" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Оверлей -->
        <div class="absolute inset-0 bg-black/50" @click="close"></div>

        <!-- Модалка ввода -->
        <Transition
          enter-active-class="transition ease-out duration-200"
          enter-from-class="opacity-0 scale-95 translate-y-4"
          enter-to-class="opacity-100 scale-100 translate-y-0"
          leave-active-class="transition ease-in duration-150"
          leave-from-class="opacity-100 scale-100 translate-y-0"
          leave-to-class="opacity-0 scale-95 translate-y-4"
        >
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-md overflow-hidden">
            <!-- Шапка -->
            <div class="px-6 py-4 bg-gradient-to-r from-primary-600 to-primary-700">
              <div class="flex items-center justify-between">
                <h3 class="text-lg font-semibold text-white">Внести результат</h3>
                <button @click="close" class="text-white/80 hover:text-white transition-colors">
                  <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                  </svg>
                </button>
              </div>
              <p class="text-sm text-white/80 mt-1">{{ group?.Группа }}</p>
            </div>

            <!-- Тело -->
            <div class="p-6 space-y-4">
              <!-- План -->
              <div class="flex items-center justify-between p-3 bg-gray-50 dark:bg-gray-700/50 rounded-lg">
                <span class="text-sm text-gray-600 dark:text-gray-400">План штук:</span>
                <span class="text-lg font-bold text-gray-900 dark:text-gray-100">{{ group?.['Штук в группе'] || 0 }}</span>
              </div>

              <!-- Факт найдено -->
              <div>
                <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">
                  Найдено штук
                </label>
                <div class="flex items-center gap-2">
                  <input
                    v-model.number="form.found_count"
                    type="number"
                    min="0"
                    class="input text-lg font-semibold"
                    @input="autoCalculatePercentage"
                  />
                  <!-- Быстрые кнопки -->
                  <div class="flex gap-1">
                    <button
                      @click="setFoundFromPlan"
                      class="px-2 py-1 text-xs bg-green-100 text-green-700 rounded hover:bg-green-200 transition-colors"
                      title="Ровно по плану"
                    >
                      = план
                    </button>
                  </div>
                </div>
              </div>

              <!-- Расхождения -->
              <div class="grid grid-cols-3 gap-3">
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Излишки</label>
                  <input
                    v-model.number="form.surplus"
                    type="number"
                    min="0"
                    class="input text-center font-semibold"
                    :class="form.surplus > 0 ? 'border-orange-300 dark:border-orange-600 bg-orange-50 dark:bg-orange-900/20' : ''"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Недостачи</label>
                  <input
                    v-model.number="form.shortage"
                    type="number"
                    min="0"
                    class="input text-center font-semibold"
                    :class="form.shortage > 0 ? 'border-red-300 dark:border-red-600 bg-red-50 dark:bg-red-900/20' : ''"
                  />
                </div>
                <div>
                  <label class="block text-sm font-medium text-gray-700 dark:text-gray-300 mb-1">Брак</label>
                  <input
                    v-model.number="form.defect"
                    type="number"
                    min="0"
                    class="input text-center font-semibold"
                    :class="form.defect > 0 ? 'border-yellow-300 dark:border-yellow-600 bg-yellow-50 dark:bg-yellow-900/20' : ''"
                  />
                </div>
              </div>

              <!-- Расчёт % -->
              <div class="p-4 bg-gradient-to-r from-primary-50 to-primary-100 dark:from-primary-900/30 dark:to-primary-800/20 rounded-xl">
                <div class="flex items-center justify-between">
                  <span class="text-sm font-medium text-primary-700 dark:text-primary-300">Прогресс:</span>
                  <span class="text-2xl font-bold text-primary-600 dark:text-primary-400">{{ calculatedPercentage }}%</span>
                </div>
                <div class="mt-2 w-full bg-white/60 dark:bg-white/10 rounded-full h-2">
                  <div
                    class="h-2 rounded-full bg-primary-500 transition-all duration-300"
                    :style="{ width: `${Math.min(calculatedPercentage, 100)}%` }"
                  ></div>
                </div>
              </div>
            </div>

            <!-- Футер -->
            <div class="px-6 py-4 bg-gray-50 dark:bg-gray-800 flex gap-3">
              <!-- Сбросить -->
              <button
                v-if="group?.is_manual"
                @click="showConfirmDialog = true"
                class="btn btn-secondary flex-1"
              >
                <svg class="w-4 h-4 mr-1" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                </svg>
                Сбросить
              </button>

              <!-- Сохранить -->
              <button
                @click="saveCount"
                class="btn btn-primary flex-1"
                :disabled="saving"
              >
                <svg v-if="saving" class="animate-spin w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                {{ group?.is_manual ? 'Обновить' : 'Сохранить' }}
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>

    <!-- Модалка подтверждения сброса -->
    <Transition
      enter-active-class="transition ease-out duration-200"
      enter-from-class="opacity-0"
      enter-to-class="opacity-100"
      leave-active-class="transition ease-in duration-150"
      leave-from-class="opacity-100"
      leave-to-class="opacity-0"
    >
      <div v-if="showConfirmDialog" class="fixed inset-0 z-[60] flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-black/60" @click="showConfirmDialog = false"></div>
        <Transition
          enter-active-class="transition ease-out duration-200"
          enter-from-class="opacity-0 scale-95"
          enter-to-class="opacity-100 scale-100"
          leave-active-class="transition ease-in duration-150"
          leave-from-class="opacity-100 scale-100"
          leave-to-class="opacity-0 scale-95"
        >
          <div class="relative bg-white dark:bg-gray-800 rounded-2xl shadow-2xl w-full max-w-sm overflow-hidden">
            <!-- Иконка предупреждения -->
            <div class="flex justify-center pt-6">
              <div class="w-14 h-14 rounded-full bg-red-100 flex items-center justify-center">
                <svg class="w-7 h-7 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
                </svg>
              </div>
            </div>

            <!-- Текст -->
            <div class="p-6 text-center">
              <h3 class="text-lg font-semibold text-gray-900 dark:text-gray-100">Сбросить результат?</h3>
              <p class="text-sm text-gray-500 dark:text-gray-400 mt-2">
                Все данные для группы <span class="font-medium text-gray-700 dark:text-gray-300">«{{ group?.Группа }}»</span> будут удалены
              </p>
            </div>

            <!-- Кнопки -->
            <div class="px-6 pb-6 flex gap-3">
              <button
                @click="showConfirmDialog = false"
                class="btn btn-secondary flex-1"
              >
                Отмена
              </button>
              <button
                @click="confirmReset"
                class="btn flex-1 bg-red-600 text-white hover:bg-red-700 focus:ring-red-500"
                :disabled="resetting"
              >
                <svg v-if="resetting" class="animate-spin w-4 h-4 mr-1" fill="none" viewBox="0 0 24 24">
                  <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4" />
                  <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
                </svg>
                Сбросить
              </button>
            </div>
          </div>
        </Transition>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup>
import { ref, computed, watch } from 'vue'
import { useInventoryStore } from '@/stores/inventory'

const store = useInventoryStore()

const props = defineProps({
  group: {
    type: Object,
    default: null,
  },
})

const emit = defineEmits(['close', 'saved'])

const isOpen = computed(() => props.group !== null)
const saving = ref(false)
const resetting = ref(false)
const showConfirmDialog = ref(false)

const form = ref({
  found_count: 0,
  surplus: 0,
  shortage: 0,
  defect: 0,
})

const totalPlanned = computed(() => props.group?.['Штук в группе'] || 0)

const calculatedPercentage = computed(() => {
  if (totalPlanned.value === 0) return 0
  return Math.round((form.value.found_count / totalPlanned.value) * 100)
})

function autoCalculatePercentage() {
  // Автоматический расчёт уже работает через computed
}

function setFoundFromPlan() {
  form.value.found_count = totalPlanned.value
}

function resetForm() {
  if (props.group?.is_manual) {
    form.value = {
      found_count: props.group?.['Найдено'] || 0,
      surplus: props.group?.['Излишки'] || 0,
      shortage: props.group?.['Недостачи'] || 0,
      defect: props.group?.['Брак'] || 0,
    }
  } else {
    form.value = {
      found_count: totalPlanned.value,
      surplus: 0,
      shortage: 0,
      defect: 0,
    }
  }
}

async function saveCount() {
  saving.value = true
  try {
    await store.submitManualCount(
      props.group['Группа ID'],
      props.group['Магазин'],
      form.value.found_count,
      totalPlanned.value,
      form.value.surplus,
      form.value.shortage,
      form.value.defect,
    )
    emit('saved')
    close()
  } catch (e) {
    console.error('Error saving count:', e)
  } finally {
    saving.value = false
  }
}

async function confirmReset() {
  resetting.value = true
  try {
    await store.removeManualCount(
      props.group['Группа ID'],
      props.group['Магазин'],
      props.group['Группа'],
    )
    emit('saved')
    showConfirmDialog.value = false
    close()
  } catch (e) {
    console.error('Error resetting count:', e)
  } finally {
    resetting.value = false
  }
}

function close() {
  emit('close')
}

watch(() => props.group, (newGroup) => {
  if (newGroup) {
    resetForm()
    showConfirmDialog.value = false
  }
})
</script>
