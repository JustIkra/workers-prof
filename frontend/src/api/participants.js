/**
 * Participants API endpoints
 */

import apiClient from './client'

export const participantsApi = {
  /**
   * Создать нового участника
   * @param {Object} data - { full_name, birth_date?, external_id? }
   */
  async create(data) {
    const response = await apiClient.post('/participants', data)
    return response.data
  },

  /**
   * Поиск/список участников с пагинацией
   * @param {Object} params - { query?, external_id?, page?, size? }
   */
  async search(params = {}) {
    const response = await apiClient.get('/participants', { params })
    return response.data
  },

  /**
   * Получить участника по ID
   * @param {string} participantId - UUID
   */
  async getById(participantId) {
    const response = await apiClient.get(`/participants/${participantId}`)
    return response.data
  },

  /**
   * Обновить участника
   * @param {string} participantId - UUID
   * @param {Object} data - { full_name?, birth_date?, external_id? }
   */
  async update(participantId, data) {
    const response = await apiClient.put(`/participants/${participantId}`, data)
    return response.data
  },

  /**
   * Удалить участника
   * @param {string} participantId - UUID
   */
  async delete(participantId) {
    const response = await apiClient.delete(`/participants/${participantId}`)
    return response.data
  },

  /**
   * Получить список отчётов участника
   * @param {string} participantId - UUID
   */
  async getReports(participantId) {
    const response = await apiClient.get(`/participants/${participantId}/reports`)
    return response.data
  },

  // ===== Participant Metrics (S2-08) =====

  /**
   * Получить актуальные метрики участника
   * @param {string} participantId - UUID участника
   * @returns {Promise<{participant_id: string, metrics: Array, total: number}>}
   */
  async getMetrics(participantId) {
    const response = await apiClient.get(`/participants/${participantId}/metrics`)
    return response.data
  },

  /**
   * Обновить значение метрики участника вручную
   * @param {string} participantId - UUID участника
   * @param {string} metricCode - Код метрики
   * @param {Object} data - { value, confidence? }
   * @returns {Promise<Object>}
   */
  async updateMetric(participantId, metricCode, data) {
    const response = await apiClient.put(
      `/participants/${participantId}/metrics/${metricCode}`,
      data
    )
    return response.data
  }
}
