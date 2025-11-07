/**
 * Auth Store - управление аутентификацией
 */

import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { authApi } from '@/api'

export const useAuthStore = defineStore('auth', () => {
  const user = ref(null)
  const loading = ref(false)
  const error = ref(null)

  const isAuthenticated = computed(() => user.value !== null)
  const isAdmin = computed(() => user.value?.role === 'ADMIN')
  const isActive = computed(() => user.value?.status === 'ACTIVE')

  async function register(email, password) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.register(email, password)
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка регистрации'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function login(email, password) {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.login(email, password)
      user.value = data.user
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка входа'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function logout() {
    loading.value = true
    error.value = null
    try {
      await authApi.logout()
      user.value = null
    } catch (err) {
      error.value = err.response?.data?.detail || 'Ошибка выхода'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function fetchCurrentUser() {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.getMe()
      user.value = data
      return data
    } catch (err) {
      user.value = null
      error.value = err.response?.data?.detail || 'Ошибка получения пользователя'
      throw err
    } finally {
      loading.value = false
    }
  }

  async function checkActive() {
    loading.value = true
    error.value = null
    try {
      const data = await authApi.checkActive()
      user.value = data
      return data
    } catch (err) {
      error.value = err.response?.data?.detail || 'Пользователь не активен'
      throw err
    } finally {
      loading.value = false
    }
  }

  return {
    user,
    loading,
    error,
    isAuthenticated,
    isAdmin,
    isActive,
    register,
    login,
    logout,
    fetchCurrentUser,
    checkActive
  }
})
