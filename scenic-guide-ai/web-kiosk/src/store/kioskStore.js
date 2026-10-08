import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useKioskStore = defineStore('kiosk', () => {
  const sessionId = ref('kiosk_' + Date.now())
  const currentSpot = ref('')
  const avatarConfig = ref({
    voice: 'female_1',
    speed: 1.0,
    model: 'default'
  })
  const messages = ref([])
  const stats = ref({
    totalQueries: 0,
    sessionStart: new Date().toISOString()
  })

  function addMessage(msg) {
    messages.value.push({ ...msg, id: Date.now() })
    if (msg.role === 'user') stats.value.totalQueries++
  }

  function clearMessages() {
    messages.value = []
  }

  function setSpot(spotName) {
    currentSpot.value = spotName
  }

  return { sessionId, currentSpot, avatarConfig, messages, stats, addMessage, clearMessages, setSpot }
})
