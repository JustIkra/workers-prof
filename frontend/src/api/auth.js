/**
 * Auth API endpoints
 */

import apiClient from './client'

export const authApi = {
  /**
   * Регистрация нового пользователя
   * @param {string} email
   * @param {string} password
   */
  async register(email, password) {
    const response = await apiClient.post('/auth/register', { email, password })
    return response.data
  },

  /**
   * Вход в систему
   * @param {string} email
   * @param {string} password
   */
  async login(email, password) {
    const response = await apiClient.post('/auth/login', { email, password })
    return response.data
  },

  /**
   * Выход из системы
   */
  async logout() {
    const response = await apiClient.post('/auth/logout')
    return response.data
  },

  /**
   * Получить текущего пользователя
   */
  async getMe() {
    const response = await apiClient.get('/auth/me')
    return response.data
  },

  /**
   * Проверить, что пользователь активен
   */
  async checkActive() {
    const response = await apiClient.get('/auth/me/check-active')
    return response.data
  }
}
