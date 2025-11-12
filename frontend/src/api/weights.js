/**
 * Weights API endpoints
 */

import apiClient from './client'

export const weightsApi = {
  /**
   * Создать или обновить весовую таблицу (upsert)
   * @param {Object} data - { prof_activity_code, weights: [{metric_code, weight}], metadata }
   */
  async upload(data) {
    const response = await apiClient.post('/admin/weights/upload', data)
    return response.data
  },

  /**
   * Обновить существующую весовую таблицу
   * @param {string} weightTableId - UUID таблицы
   * @param {Object} data - { prof_activity_code, weights: [{metric_code, weight}], metadata }
   */
  async update(weightTableId, data) {
    const response = await apiClient.put(`/admin/weights/${weightTableId}`, data)
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
  }
}
