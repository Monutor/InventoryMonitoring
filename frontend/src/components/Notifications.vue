<template>
  <div class="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
    <TransitionGroup name="notification">
      <div 
        v-for="notification in store.notifications" 
        :key="notification.id"
        class="card shadow-lg border-l-4 cursor-pointer"
        :class="notificationBorderClass(notification.type)"
        @click="store.removeNotification(notification.id)"
      >
        <div class="flex items-start gap-3">
          <div class="flex-shrink-0 text-xl">{{ notificationIcon(notification.type) }}</div>
          <div class="flex-1 min-w-0">
            <div class="font-medium text-sm">{{ notification.title }}</div>
            <div class="text-sm text-gray-500 mt-0.5">{{ notification.message }}</div>
          </div>
          <button 
            @click.stop="store.removeNotification(notification.id)"
            class="flex-shrink-0 text-gray-400 hover:text-gray-600"
          >
            ×
          </button>
        </div>
      </div>
    </TransitionGroup>
  </div>
</template>

<script setup>
import { useInventoryStore } from '@/stores/inventory'

const store = useInventoryStore()

function notificationIcon(type) {
  const icons = {
    success: '✅',
    error: '❌',
    info: 'ℹ️',
    warning: '⚠️',
  }
  return icons[type] || 'ℹ️'
}

function notificationBorderClass(type) {
  const classes = {
    success: 'border-green-500',
    error: 'border-red-500',
    info: 'border-blue-500',
    warning: 'border-yellow-500',
  }
  return classes[type] || 'border-gray-300'
}
</script>

<style scoped>
.notification-enter-active,
.notification-leave-active {
  transition: all 0.3s ease;
}
.notification-enter-from {
  opacity: 0;
  transform: translateX(100%);
}
.notification-leave-to {
  opacity: 0;
  transform: translateX(100%);
}
</style>
