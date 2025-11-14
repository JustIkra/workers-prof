/**
 * Возвращает отображаемое название метрики на русском языке.
 * Предпочитает поле name_ru. При отсутствии — пишет предупреждение и
 * возвращает код метрики (либо тире, если кода нет).
 *
 * @param {object | undefined | null} metricDef - объект определения метрики
 * @param {string | undefined | null} metricCode - код метрики (fallback)
 * @param {Console | { warn?: Function }} logger - объект для логирования предупреждений
 * @returns {string}
 */
export function getMetricDisplayName(metricDef, metricCode, logger = console) {
  const code = metricCode || metricDef?.code

  if (metricDef?.name_ru && metricDef.name_ru.trim()) {
    return metricDef.name_ru.trim()
  }

  if (code) {
    logger?.warn?.(
      `[metrics] Отсутствует русское название для метрики "${code}". Отображаем код.`
    )
    return code
  }

  logger?.warn?.('[metrics] Не удалось определить название метрики.')
  return '—'
}

/**
 * Формирует подпись метрики с единицей измерения.
 *
 * @param {object} metricDef - объект определения метрики
 * @param {Console | { warn?: Function }} logger
 * @returns {string}
 */
export function formatMetricLabel(metricDef, logger = console) {
  const displayName = getMetricDisplayName(metricDef, metricDef?.code, logger)
  const unit = metricDef?.unit ? metricDef.unit.trim() : ''

  if (unit) {
    return `${displayName} (${unit})`
  }
  return displayName
}



