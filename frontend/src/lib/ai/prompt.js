export function buildEdgeUserPrompt(message, shopContext) {
  if (!shopContext) return message
  return `当前地图上的女仆店信息：\n${shopContext}\n\n用户问题：${message}`
}

export function parseAiReply(replyFull) {
  const match = replyFull.match(/```highlight\s*(\{.*?\})\s*```/s)
  if (!match) {
    return {
      reply: replyFull.trim(),
      highlighted_shop_ids: [],
    }
  }

  let highlightedShopIds = []
  try {
    highlightedShopIds = JSON.parse(match[1]).shop_ids || []
  } catch {
    highlightedShopIds = []
  }

  return {
    reply: replyFull.slice(0, match.index).trim(),
    highlighted_shop_ids: highlightedShopIds,
  }
}
