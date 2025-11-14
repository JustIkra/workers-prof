const DEFAULT_FALLBACK_MESSAGE = 'Произошла ошибка. Попробуйте ещё раз.'

const IGNORED_LOC_PARTS = new Set(['body', 'query', 'path', 'header'])

const unique = (items) => Array.from(new Set(items.filter(Boolean)))

const ensureArray = (value) => {
  if (Array.isArray(value)) return value
  if (value === undefined || value === null) return []
  return [value]
}

const parseJsonIfPossible = (value) => {
  if (typeof value !== 'string') return { ok: false }
  const trimmed = value.trim()
  if (!trimmed) return { ok: false }
  const firstChar = trimmed[0]
  if (firstChar !== '{' && firstChar !== '[') return { ok: false }
  try {
    return { ok: true, value: JSON.parse(trimmed) }
  } catch {
    return { ok: false }
  }
}

const normalizeFieldPath = (loc = []) => {
  if (!Array.isArray(loc)) return ''
  return loc
    .filter((part) => !IGNORED_LOC_PARTS.has(part))
    .map((part) => String(part))
    .join('.')
}

const appendFieldError = (fieldErrors, field, message) => {
  if (!field) return
  if (!fieldErrors[field]) {
    fieldErrors[field] = []
  }
  fieldErrors[field].push(message)
}

const collectFromDetailArray = (detail, fallbackMessage) => {
  const messages = []
  const fieldErrors = {}

  detail.forEach((originalItem) => {
    let item = originalItem
    if (typeof originalItem === 'string') {
      const parsed = parseJsonIfPossible(originalItem)
      if (parsed.ok) {
        item = parsed.value
      }
    }

    if (!item) {
      return
    }

    if (typeof item === 'string') {
      messages.push(item)
      return
    }

    if (typeof item === 'object') {
      const msg = item.msg || item.message || item.detail || fallbackMessage
      messages.push(msg)
      if (item.loc) {
        const field = normalizeFieldPath(item.loc)
        appendFieldError(fieldErrors, field, msg)
      }
      return
    }

    messages.push(String(item))
  })

  return {
    messages: unique(messages),
    fieldErrors: Object.fromEntries(
      Object.entries(fieldErrors).map(([field, fieldMessages]) => [field, unique(fieldMessages)])
    )
  }
}

export function normalizeApiError(error, fallbackMessage = DEFAULT_FALLBACK_MESSAGE) {
  const normalized = {
    status: error?.response?.status,
    message: fallbackMessage,
    messages: [],
    fieldErrors: {},
    raw: error
  }

  const data = error?.response?.data ?? error?.data ?? {}
  let detail = data?.detail ?? data?.message ?? data

  if (typeof detail === 'string') {
    const parsed = parseJsonIfPossible(detail)
    if (parsed.ok) {
      detail = parsed.value
    }
  }

  const pushMessage = (message) => {
    if (!message) return
    normalized.messages.push(String(message))
  }

  if (typeof detail === 'string') {
    pushMessage(detail)
  } else if (Array.isArray(detail)) {
    const { messages, fieldErrors } = collectFromDetailArray(detail, fallbackMessage)
    normalized.messages.push(...messages)
    normalized.fieldErrors = fieldErrors
  } else if (detail && typeof detail === 'object') {
    const nestedDetail = detail.detail
    if (typeof nestedDetail === 'string') {
      pushMessage(nestedDetail)
    }

    const detailArray = Array.isArray(nestedDetail) ? nestedDetail : detail.errors
    if (Array.isArray(detailArray)) {
      const { messages, fieldErrors } = collectFromDetailArray(detailArray, fallbackMessage)
      normalized.messages.push(...messages)
      normalized.fieldErrors = fieldErrors
    }

    ensureArray(detail.message).forEach(pushMessage)
    ensureArray(detail.error).forEach(pushMessage)
    if (normalized.messages.length === 0 && nestedDetail && typeof nestedDetail === 'object') {
      // Попробуем собрать сообщения из вложенных структур
      ensureArray(nestedDetail.message).forEach(pushMessage)
      ensureArray(nestedDetail.error).forEach(pushMessage)
    }
  }

  if (normalized.messages.length === 0 && error?.message) {
    pushMessage(error.message)
  }

  normalized.messages = unique(normalized.messages.length ? normalized.messages : [fallbackMessage])
  normalized.message = normalized.messages[0] || fallbackMessage

  // Удаляем возможные дубликаты в fieldErrors
  normalized.fieldErrors = Object.fromEntries(
    Object.entries(normalized.fieldErrors).map(([field, fieldMessages]) => [field, unique(fieldMessages)])
  )

  return normalized
}

export function extractFieldErrors(error, fallbackMessage) {
  const normalized = normalizeApiError(error, fallbackMessage)
  return normalized.fieldErrors
}


