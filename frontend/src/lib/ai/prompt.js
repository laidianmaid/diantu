import { jsonrepair } from 'jsonrepair'

export function parseAgentJson(rawText) {
  const repaired = jsonrepair(rawText)
  const parsed = JSON.parse(repaired)
  if (!parsed || typeof parsed !== 'object' || Array.isArray(parsed)) {
    throw new Error('MODEL_OUTPUT_NOT_OBJECT')
  }
  return parsed
}

function extractShopIdsFromPayload(payload, limit = 10) {
  if (limit <= 0) return []

  const results = []
  const seen = new Set()

  const push = (rawId) => {
    const id = Number(rawId)
    if (!Number.isInteger(id) || id <= 0 || seen.has(id)) return
    seen.add(id)
    results.push(id)
  }

  const walk = (value) => {
    if (results.length >= limit || value == null) return
    if (Array.isArray(value)) {
      for (const item of value) {
        if (results.length >= limit) break
        walk(item)
      }
      return
    }
    if (typeof value !== 'object') return

    if ('id' in value) push(value.id)
    if ('shop_id' in value) push(value.shop_id)
    for (const key of ['shops', 'data', 'items', 'results']) {
      if (key in value) {
        walk(value[key])
      }
    }
  }

  walk(payload)
  return results
}

export function deriveHighlightedIdsFromToolHistory(toolHistory) {
  for (let i = (toolHistory || []).length - 1; i >= 0; i -= 1) {
    const extracted = extractShopIdsFromPayload(toolHistory[i])
    if (extracted.length > 0) {
      return extracted
    }
  }
  return []
}

export function normalizeFinalAnswer(payload, fallbackHighlightedIds = []) {
  const reply = String(payload?.reply || '').trim()
  if (!reply) {
    throw new Error('FINAL_REPLY_REQUIRED')
  }

  const highlighted = Array.isArray(payload?.highlighted_shop_ids)
    ? payload.highlighted_shop_ids
    : []

  return {
    reply,
    highlighted_shop_ids: (highlighted.length > 0 ? highlighted : fallbackHighlightedIds)
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
