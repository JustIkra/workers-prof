/**
 * Утилиты для форматирования чисел с локалью ru-RU
 *
 * Обеспечивает:
 * - Запятая как десятичный разделитель
 * - Корректное преобразование строка ↔ число
 * - Валидация ввода
 */

/**
 * Форматирует число для отображения в ru-RU формате (с запятой)
 * @param {number|string} value - Значение для форматирования
 * @param {number} decimals - Количество знаков после запятой (по умолчанию 1)
 * @returns {string} Отформатированное значение
 */
export function formatNumber(value, decimals = 1) {
  if (value === null || value === undefined || value === '') {
    return ''
  }

  const num = typeof value === 'string' ? parseFloat(value) : value

  if (isNaN(num)) {
    return ''
  }

  return num.toLocaleString('ru-RU', {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals
  })
}

/**
 * Парсит строку с ru-RU форматом (запятая) в число
 * @param {string} value - Строка для парсинга
 * @returns {number|null} Число или null если невалидно
 */
export function parseNumber(value) {
  if (value === null || value === undefined || value === '') {
    return null
  }

  // Приводим к строке
  const str = String(value).trim()

  // Заменяем запятую на точку для парсинга
  const normalized = str.replace(',', '.')

  const num = parseFloat(normalized)

  return isNaN(num) ? null : num
}

/**
 * Валидирует строку как число в ru-RU формате
 * @param {string} value - Строка для валидации
 * @returns {boolean} true если валидная
 */
export function isValidNumber(value) {
  if (value === null || value === undefined || value === '') {
    return false
  }

  const str = String(value).trim()

  // Допустимые паттерны:
  // - Целые числа: 5, 10
  // - С точкой: 5.5, 7.8
  // - С запятой: 5,5, 7,8
  // - Отрицательные: -5, -7.5, -7,8
  const pattern = /^-?\d+([.,]\d+)?$/

  return pattern.test(str)
}

/**
 * Нормализует ввод пользователя (заменяет точку на запятую)
 * @param {string} value - Введённое значение
 * @returns {string} Нормализованное значение
 */
export function normalizeInput(value) {
  if (!value) return ''

  // Заменяем точку на запятую для ru-RU
  return String(value).replace('.', ',')
}

/**
 * Форматирует метрику для API (конвертирует в число)
 * @param {string|number} value - Значение метрики
 * @returns {number|null} Число для API
 */
export function formatForApi(value) {
  return parseNumber(value)
}

/**
 * Форматирует метрику из API для отображения
 * @param {number|string} value - Значение из API
 * @param {number} decimals - Количество знаков после запятой
 * @returns {string} Значение для отображения
 */
export function formatFromApi(value, decimals = 1) {
  return formatNumber(value, decimals)
}
