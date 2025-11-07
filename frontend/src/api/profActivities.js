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
  }
}
