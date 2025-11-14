/**
 * API клиент для взаимодействия с backend
 *
 * Все запросы идут через /api префикс
 */

import axios from 'axios'
import { normalizeApiError } from '@/utils/normalizeError'

const apiClient = axios.create({
  baseURL: '/api',
  withCredentials: true, // Для работы с httpOnly cookies
  headers: {
    'Content-Type': 'application/json'
  }
})

// Обработка ошибок
apiClient.interceptors.response.use(
  response => response,
  error => {
    if (error && !error.normalizedError) {
      const normalized = normalizeApiError(error)
      error.normalizedError = normalized
      error.userMessage = normalized.message
    }
    if (error.response?.status === 401) {
      const requestUrl = error.config?.url || ''
      const isLoginRequest = requestUrl.includes('/auth/login')
      const isAlreadyOnLoginPage = window.location.pathname === '/login'

      if (!isLoginRequest && !isAlreadyOnLoginPage) {
        // Неавторизован - редирект на логин
        window.location.href = '/login'
      }
    }
    return Promise.reject(error)
  }
)

export default apiClient
