import wllamaWasm from '@wllama/wllama/src/wasm/wllama.wasm?url'

const DEFAULT_MODEL_URLS = [
  'https://huggingface.co/huihui-ai/Huihui-gemma-4-E2B-it-qat-q4_0-unquantized-abliterated-GGUF/resolve/main/Huihui-gemma-4-E2B-it-qat-q4_0-unquantized-abliterated-Q4_K.gguf',
]

const envModelUrls = (import.meta.env.VITE_EDGE_MODEL_URLS || '')
  .split(',')
  .map(item => item.trim())
  .filter(Boolean)

function isGgufUrl(url) {
  return typeof url === 'string' && /\.gguf(?:\?.*)?$/i.test(url)
}

export const EDGE_MODEL = {
  label: 'Gemma 4 E2B',
  sizeBytes: Number(import.meta.env.VITE_EDGE_MODEL_SIZE_BYTES || 3416118240),
  urls: envModelUrls.length > 0 ? envModelUrls : DEFAULT_MODEL_URLS,
}

export const EDGE_MODEL_PRIMARY_URL = EDGE_MODEL.urls[0] || ''
export const EDGE_MODEL_URLS_VALID =
  EDGE_MODEL.urls.length > 0 && EDGE_MODEL.urls.every(isGgufUrl)

export const EDGE_MODEL_SIZE_LABEL = '约 3.42GB'
export const MAX_BROWSER_MODEL_FILE_BYTES = 2 * 1024 * 1024 * 1024
export const EDGE_MODEL_REQUIRES_SPLIT =
  EDGE_MODEL.urls.length === 1 && EDGE_MODEL.sizeBytes > MAX_BROWSER_MODEL_FILE_BYTES

export const EDGE_AI_PROMPT = `你是「来点妹抖吗？」地图助手，帮助用户发现上海妹抖店。
你可以根据用户需求推荐女仆店，或帮助筛选。
如果你要高亮地图上的女仆店，请在回复末尾添加 JSON 块：
\`\`\`highlight
{"shop_ids": [1, 2, 3]}
\`\`\`
否则不要输出 highlight 块。`

export const WLLAMA_CONFIG_PATHS = {
  default: wllamaWasm,
}

export const EDGE_MODEL_LOAD_PARAMS = {
  n_batch: 128,
  n_ctx: 4096,
  reasoning: false,
  reasoning_budget_tokens: 0,
}

export const EDGE_MODEL_CHAT_PARAMS = {
  max_tokens: 512,
  temperature: 0.2,
  top_p: 0.9,
  reasoning: false,
  reasoning_budget_tokens: 0,
}
