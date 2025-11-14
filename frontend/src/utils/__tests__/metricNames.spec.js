import { describe, it, expect, vi } from 'vitest'
import { getMetricDisplayName } from '../metricNames'

describe('getMetricDisplayName', () => {
  it('возвращает name_ru, если оно задано', () => {
    const metric = { code: 'abstractness', name_ru: 'Абстрактность' }
    expect(getMetricDisplayName(metric, metric.code)).toBe('Абстрактность')
  })

  it('возвращает код и логирует предупреждение, если name_ru отсутствует', () => {
    const metric = { code: 'abstractness', name_ru: '' }
    const logger = { warn: vi.fn() }

    const result = getMetricDisplayName(metric, metric.code, logger)

    expect(result).toBe('abstractness')
    expect(logger.warn).toHaveBeenCalledTimes(1)
    expect(logger.warn.mock.calls[0][0]).toContain('Отсутствует русское название')
  })

  it('возвращает тире, если нет кода и имени', () => {
    const logger = { warn: vi.fn() }
    const result = getMetricDisplayName(null, null, logger)

    expect(result).toBe('—')
    expect(logger.warn).toHaveBeenCalledTimes(1)
  })
})

