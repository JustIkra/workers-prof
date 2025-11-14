/**
 * Admin Store - управление пользователями (админ)
 */

import { defineStore } from 'pinia'
import { ref } from 'vue'
import { adminApi } from '@/api'
import { normalizeApiError } from '@/utils/normalizeError'

export const useAdminStore = defineStore('admin', () => {
  const pendingUsers = ref([])
  const loading = ref(false)
  const error = ref(null)

  async function fetchPendingUsers() {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.getPendingUsers()
      pendingUsers.value = data
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка загрузки пользователей')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  async function approveUser(userId) {
    loading.value = true
    error.value = null
    try {
      const data = await adminApi.approveUser(userId)
      pendingUsers.value = pendingUsers.value.filter(u => u.id !== userId)
      return data
    } catch (err) {
      const normalized = normalizeApiError(err, 'Ошибка одобрения пользователя')
      error.value = normalized.message
      err.normalizedError = normalized
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    pendingUsers,
    loading,
    error,
    fetchPendingUsers,
    approveUser
  }
})
