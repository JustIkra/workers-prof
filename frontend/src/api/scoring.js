/**
 * Scoring API endpoints
 */

import apiClient from './client'

export const scoringApi = {
  /**
   * Рассчитать пригодность участника
   * @param {string} participantId - UUID
   * @param {string} activityCode - Код профессиональной деятельности
   */
  async calculate(participantId, activityCode) {
    const response = await apiClient.post(`/scoring/participants/${participantId}/calculate`, null, {
      params: { activity_code: activityCode }
    })
    return response.data
  },

  /**
   * Получить историю оценок участника
   * @param {string} participantId - UUID
   * @param {number} limit - Максимальное количество результатов (по умолчанию 10)
   */
  async getHistory(participantId, limit = 10) {
    const response = await apiClient.get(`/scoring/participants/${participantId}/scores`, {
      params: { limit }
    })
    return response.data
  },

  /**
   * Получить детали оценки
   * @param {string} scoringResultId - UUID
   */
  async getById(scoringResultId) {
    const response = await apiClient.get(`/scoring-results/${scoringResultId}`)
    return response.data
  },

  /**
   * Генерировать рекомендации для отчёта
   * @param {string} reportId - UUID
   */
  async generateRecommendations(reportId) {
    const response = await apiClient.post(`/reports/${reportId}/recommendations`)
    return response.data
  },

  /**
   * Получить финальный отчёт участника
   * @param {string} participantId - UUID
   * @param {string} activityCode - Код профессиональной деятельности
   * @param {string} format - 'json' | 'html'
   */
  async getFinalReport(participantId, activityCode, format = 'json') {
    const config = {
      params: {
        activity_code: activityCode,
        format
      }
    }

    if (format === 'html') {
      config.responseType = 'text'
    }

    const response = await apiClient.get(`/participants/${participantId}/final-report`, config)
    return format === 'html' ? response.data : response.data
  }
}
