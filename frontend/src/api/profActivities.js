/**
 * Professional Activities API endpoints
 */

import apiClient from './client'

export const profActivitiesApi = {
  /**
   * Получить список всех профессиональных областей
   */
  async list() {
    const response = await apiClient.get('/prof-activities')
    return response.data
  },

  /**
   * Создать новую профессиональную область
   * @param {Object} data - { code, name, description }
   */
  async create(data) {
    const response = await apiClient.post('/prof-activities', data)
    return response.data
  },

  /**
   * Обновить профессиональную область
   * @param {string} id - UUID профессиональной области
   * @param {Object} data - { name?, description? }
   */
  async update(id, data) {
    const response = await apiClient.put(`/prof-activities/${id}`, data)
    return response.data
  },

  /**
   * Удалить профессиональную область
   * @param {string} id - UUID профессиональной области
   */
  async delete(id) {
    await apiClient.delete(`/prof-activities/${id}`)
  }
}
