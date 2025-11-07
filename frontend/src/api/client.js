/**
 * API клиент для взаимодействия с backend
 *
 * Все запросы идут через /api префикс
 */

import axios from 'axios'

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
    if (error.response?.status === 401) {
      // Неавторизован - редирект на логин
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export default apiClient
