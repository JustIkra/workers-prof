/**
 * Weights API endpoints
 */

import apiClient from './client'

export const weightsApi = {
  /**
   * Загрузить новую весовую таблицу
   * @param {Object} data - { prof_activity_code, version, weights: [{metric_code, weight}] }
   */
  async upload(data) {
    const response = await apiClient.post('/admin/weights/upload', data)
    return response.data
  },

  /**
   * Список весовых таблиц (с фильтром по проф. области)
   * @param {string} profActivityCode - опциональный код проф. области
   */
  async list(profActivityCode = null) {
    const params = profActivityCode ? { prof_activity_code: profActivityCode } : {}
    const response = await apiClient.get('/admin/weights', { params })
    return response.data
  },

  /**
   * Активировать весовую таблицу
   * @param {string} weightTableId - UUID
   */
  async activate(weightTableId) {
    const response = await apiClient.post(`/admin/weights/${weightTableId}/activate`)
    return response.data
  }
}
