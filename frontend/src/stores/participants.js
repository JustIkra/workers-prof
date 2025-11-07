/**
 * Participants Store - управление участниками
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { participantsApi } from '@/api'

export const useParticipantsStore = defineStore('participants', () => {
  const participants = ref([])
  const currentParticipant = ref(null)
  const loading = ref(false)
  const error = ref(null)
  const pagination = ref({
    total: 0,
    page: 1,
    size: 20,
    totalPages: 0
  })

  async function searchParticipants(params = {}) {
    loading.value = true
    error.value = null
    try {
      const data = await participantsApi.search(params)
      participants.value = data.items
      pagination.value = {
        total: data.total,
        page: data.page,
        size: data.size,
        totalPages: Math.ceil(data.total / data.size)
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка загрузки участников'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function getParticipant(participantId) {
    loading.value = true
    error.value = null
    try {
      const data = await participantsApi.getById(participantId)
      currentParticipant.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка загрузки участника'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function createParticipant(participantData) {
    loading.value = true
    error.value = null
    try {
      const data = await participantsApi.create(participantData)
      participants.value.unshift(data)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка создания участника'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function updateParticipant(participantId, participantData) {
    loading.value = true
    error.value = null
    try {
      const data = await participantsApi.update(participantId, participantData)
      const index = participants.value.findIndex(p => p.id === participantId)
      if (index !== -1) {
        participants.value[index] = data
      }
      if (currentParticipant.value?.id === participantId) {
        currentParticipant.value = data
      }
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка обновления участника'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function deleteParticipant(participantId) {
    loading.value = true
    error.value = null
    try {
      await participantsApi.delete(participantId)
      participants.value = participants.value.filter(p => p.id !== participantId)
      if (currentParticipant.value?.id === participantId) {
        currentParticipant.value = null
      }
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка удаления участника'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    participants,
    currentParticipant,
    loading,
    error,
    pagination,
    searchParticipants,
    getParticipant,
    createParticipant,
    updateParticipant,
    deleteParticipant
  }
})
