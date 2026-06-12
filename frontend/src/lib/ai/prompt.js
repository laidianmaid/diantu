import { jsonrepair } from 'jsonrepair'

export function parseAgentJson(rawText) {
  const repaired = jsonrepair(rawText)
  const parsed = JSON.parse(repaired)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('MODEL_OUTPUT_NOT_OBJECT')
  }
  return parsed
}

export function normalizeFinalAnswer(payload) {
  const reply = String(payload?.reply || '').trim()
  if (!reply) {
    throw new Error('FINAL_REPLY_REQUIRED')
  }

  const highlighted = Array.isArray(payload?.highlighted_shop_ids)
    ? payload.highlighted_shop_ids
    : []

  return {
    reply,
    highlighted_shop_ids: highlighted
      .map(id => Number(id))
      .filter(id => Number.isInteger(id) && id > 0),
  }
}

export function filterExistingHighlightedIds(highlightedIds, shops) {
  const validIds = new Set((shops || []).map(shop => shop.id))
  const result = []
  const seen = new Set()

  for (const shopId of highlightedIds || []) {
    if (validIds.has(shopId) && !seen.has(shopId)) {
      result.push(shopId)
      seen.add(shopId)
    }
  }

  return result
}

export function buildToolResultMessage(toolName, ok, result = null, error = null) {
  return JSON.stringify({
    type: 'tool_result',
    tool_name: toolName,
    ok,
    result,
    error,
  })
}

export function buildFormatErrorMessage(message) {
  return JSON.stringify({
    type: 'format_error',
    message,
  })
}
