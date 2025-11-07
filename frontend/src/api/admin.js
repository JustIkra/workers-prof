/**
 * Admin API endpoints
 */

import apiClient from './client'

export const adminApi = {
  /**
   * Получить список пользователей со статусом PENDING
   */
  async getPendingUsers() {
    const response = await apiClient.get('/admin/pending-users')
    return response.data
  },

  /**
   * Одобрить пользователя (PENDING -> ACTIVE)
   * @param {string} userId - UUID
   */
  async approveUser(userId) {
    const response = await apiClient.post(`/admin/approve/${userId}`)
    return response.data
  }
}
