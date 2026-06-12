import { reactive, readonly } from 'vue'

import { aiApi } from '../../api'
import { useShopsStore } from '../../stores/shops'
import {
  EDGE_MODEL,
  EDGE_MODEL_CHAT_PARAMS,
  EDGE_MODEL_LOAD_PARAMS,
  EDGE_MODEL_PRIMARY_URL,
  EDGE_MODEL_REQUIRES_SPLIT,
  EDGE_MODEL_SIZE_LABEL,
  EDGE_MODEL_URLS_VALID,
  WLLAMA_CONFIG_PATHS,
} from './config'
import {
  buildFormatErrorMessage,
  buildToolResultMessage,
  deriveHighlightedIdsFromToolHistory,
  filterExistingHighlightedIds,
  normalizeFinalAnswer,
  parseAgentJson,
} from './prompt'

const EDGE_AI_CONSENT_KEY = 'edge_ai_download_approved'

const state = reactive({
  mode: 'checking',
  detail: '正在检测浏览器端 AI 能力…',
  activity: '',
  ready: false,
  downloadProgress: 0,
  lastSource: null,
})

let detectPromise = null
let warmupPromise = null
let wllamaModulePromise = null
let agentConfigPromise = null
let wllama = null

async function loadWllamaModule() {
  if (!wllamaModulePromise) {
    wllamaModulePromise = import('@wllama/wllama')
  }
  return wllamaModulePromise
}

async function getAgentConfig() {
  if (!agentConfigPromise) {
    agentConfigPromise = aiApi.agentConfig().then(({ data }) => data)
  }
  return agentConfigPromise
}

function isDesktopChromium() {
  const ua = navigator.userAgent || ''
  const isMobile = /Android|iPhone|iPad|iPod|Mobile/i.test(ua)
  const brands = navigator.userAgentData?.brands || []
  const chromiumBrand = brands.some(item => /Chrom|Edge/i.test(item.brand))
  const chromiumUa = /(Chrome|Chromium|Edg)\/\d+/i.test(ua) && !/(Firefox|OPR)\/\d+/i.test(ua)
  return !isMobile && (chromiumBrand || chromiumUa)
}

function hasConsent() {
  return localStorage.getItem(EDGE_AI_CONSENT_KEY) === 'accepted'
}

function requestConsent() {
  if (hasConsent()) return true
  const accepted = window.confirm(
    `浏览器端 ${EDGE_MODEL.label} 首次使用需要下载 ${EDGE_MODEL_SIZE_LABEL} 模型，并占用较多显存/磁盘缓存。确认后将优先在本地运行，失败时自动切换到远程模型。是否继续？`
  )
  if (accepted) {
    localStorage.setItem(EDGE_AI_CONSENT_KEY, 'accepted')
  }
  return accepted
}

async function createWllama() {
  const { LoggerWithoutDebug, Wllama } = await loadWllamaModule()
  return new Wllama(WLLAMA_CONFIG_PATHS, {
    logger: LoggerWithoutDebug,
    parallelDownloads: 3,
  })
}

async function detectSupport() {
  if (detectPromise) return detectPromise

  detectPromise = (async () => {
    if (typeof window === 'undefined' || typeof navigator === 'undefined') {
      state.mode = 'fallback'
      state.detail = '当前环境不支持浏览器端 AI，正在使用远程模型。'
      return false
    }

    if (!isDesktopChromium()) {
      state.mode = 'fallback'
      state.detail = '首版浏览器端 AI 仅支持桌面 Chromium，正在使用远程模型。'
      return false
    }

    if (!navigator.gpu) {
      state.mode = 'fallback'
      state.detail = '当前浏览器未启用 WebGPU，正在使用远程模型。'
      return false
    }

    if (EDGE_MODEL_REQUIRES_SPLIT) {
      state.mode = 'fallback'
      state.detail = '当前 Gemma 4 E2B GGUF 是 3.42GB 单文件；浏览器端运行前需先切分为多个分片 URL，正在使用远程模型。'
      return false
    }

    if (!EDGE_MODEL_URLS_VALID || !EDGE_MODEL_PRIMARY_URL) {
      state.mode = 'fallback'
      state.detail = '浏览器端模型 URL 配置无效；请检查 VITE_EDGE_MODEL_URLS 是否为逗号分隔的 .gguf 分片地址，正在使用远程模型。'
      return false
    }

    const adapter = await navigator.gpu.requestAdapter().catch(() => null)
    if (!adapter) {
      state.mode = 'fallback'
      state.detail = '当前设备无法分配 WebGPU adapter，正在使用远程模型。'
      return false
    }

    state.mode = hasConsent() ? 'warming' : 'consent-required'
    state.detail = hasConsent()
      ? `已检测到浏览器端 ${EDGE_MODEL.label} 能力，正在准备本地模型…`
      : `已检测到浏览器端 ${EDGE_MODEL.label} 能力，首次使用会下载 ${EDGE_MODEL_SIZE_LABEL} 模型。`
    return true
  })()

  return detectPromise
}

async function warmupEdgeModel({ interactive = false } = {}) {
  const supported = await detectSupport()
  if (!supported) return false
  if (state.ready && wllama) return true

  if (!hasConsent()) {
    if (!interactive) return false
    if (!requestConsent()) {
      state.mode = 'fallback'
      state.detail = '已取消浏览器端模型下载，当前继续使用远程模型。'
      return false
    }
  }

  if (warmupPromise) return warmupPromise

  state.mode = 'warming'
  state.detail = `正在下载并预热浏览器端 ${EDGE_MODEL.label}…`
  state.downloadProgress = 0

  warmupPromise = (async () => {
    try {
      if (!wllama) {
        wllama = await createWllama()
      }

      await getAgentConfig()
      await wllama.loadModelFromUrl(EDGE_MODEL_PRIMARY_URL, {
        ...EDGE_MODEL_LOAD_PARAMS,
        progressCallback: ({ loaded, total }) => {
          if (!total) return
          state.downloadProgress = Math.max(0, Math.min(100, Math.round((loaded / total) * 100)))
          state.detail = `正在下载并预热浏览器端 ${EDGE_MODEL.label}… ${state.downloadProgress}%`
        },
      })

      state.ready = true
      state.mode = 'ready'
      state.detail = `浏览器端 ${EDGE_MODEL.label} 已就绪，将优先本地推理。`
      return true
    } catch (error) {
      state.ready = false
      state.mode = 'fallback'
      state.detail = `浏览器端 ${EDGE_MODEL.label} 初始化失败，正在使用远程模型。`
      if (wllama) {
        await wllama.exit().catch(() => {})
        wllama = null
      }
      console.warn('Edge AI warmup failed:', error)
      return false
    } finally {
      warmupPromise = null
    }
  })()

  return warmupPromise
}

function buildInitialUserMessage(message, userLocation) {
  return JSON.stringify({
    type: 'user_request',
    message,
    user_location: userLocation ? { lat: userLocation.lat, lng: userLocation.lng } : null,
  })
}

async function executeBrowserAgentLoop(message) {
  const agentConfig = await getAgentConfig()
  const shopsStore = useShopsStore()
  const userLocation = shopsStore.userLocation
  state.activity = 'AI 正在分析你的问题…'

  const messages = [
    { role: 'system', content: agentConfig.system_prompt },
    { role: 'user', content: buildInitialUserMessage(message, userLocation) },
  ]
  const successfulToolHistory = []
  let lastWasToolCall = false

  for (let turn = 0; turn < agentConfig.max_turns; turn += 1) {
    if (!lastWasToolCall) state.activity = `Thinking…`
    lastWasToolCall = false
    const response = await wllama.createChatCompletion({
      messages,
      ...EDGE_MODEL_CHAT_PARAMS,
    })

    const rawText = response?.choices?.[0]?.message?.content || ''
    let payload
    try {
      payload = parseAgentJson(rawText)
    } catch {
      messages.push({ role: 'assistant', content: rawText })
      messages.push({
        role: 'user',
        content: buildFormatErrorMessage('请只返回一个合法 JSON 对象，且只能是 tool_call 或 final_answer。'),
      })
      continue
    }

    if (payload.type === 'final_answer') {
      const normalized = normalizeFinalAnswer(payload, deriveHighlightedIdsFromToolHistory(successfulToolHistory))
      return {
        ...normalized,
        highlighted_shop_ids: filterExistingHighlightedIds(normalized.highlighted_shop_ids, shopsStore.shops),
      }
    }

    if (payload.type !== 'tool_call') {
      messages.push({ role: 'assistant', content: rawText })
      messages.push({
        role: 'user',
        content: buildFormatErrorMessage('type 字段必须是 tool_call 或 final_answer。'),
      })
      continue
    }

    const toolName = String(payload.tool_name || '').trim()
    const argumentsPayload = payload.arguments && typeof payload.arguments === 'object' ? payload.arguments : {}
    const TOOL_LABELS = {
      get_top_shops: '查找热门妹抖店',
      get_nearest_to_self: '查找附近妹抖店',
      get_nearby_shops_by_place: '搜索地点周边店铺',
      search_shops_by_keywords: '按关键词检索店铺',
      get_shop_details: '获取店铺详情',
      get_available_api_docs: '查阅可用接口文档',
      call_available_api: '调用数据接口',
    }
    state.activity = `AI 正在${TOOL_LABELS[toolName] || '查询数据'}…`
    lastWasToolCall = true
    const { data } = await aiApi.executeTool({
      tool_name: toolName,
      arguments: argumentsPayload,
      user_location: userLocation,
    })
    if (data.ok) {
      successfulToolHistory.push(data.result || null)
    }

    messages.push({ role: 'assistant', content: rawText })
    messages.push({
      role: 'user',
      content: buildToolResultMessage(data.tool_name, data.ok, data.result || null, data.error || null),
    })
  }

  state.activity = ''
  return {
    reply: '我暂时没能稳定完成这次检索，请换一种问法，或缩小范围后再试。',
    highlighted_shop_ids: [],
  }
}

async function runEdgeChat(message) {
  const result = await executeBrowserAgentLoop(message)
  state.activity = ''
  return {
    ...result,
    source: 'browser',
  }
}

async function runFallbackChat(message, detail) {
  const shopsStore = useShopsStore()
  state.activity = '正在等待远程模型回复…'
  const { data } = await aiApi.chat({
    message,
    user_location: shopsStore.userLocation,
  })
  state.mode = state.ready ? 'ready' : 'fallback'
  state.detail = detail || state.detail
  state.activity = ''
  state.lastSource = 'ollama'
  return {
    reply: data.reply,
    highlighted_shop_ids: data.highlighted_shop_ids || [],
    source: 'ollama',
  }
}

export async function primeEdgeAi() {
  const supported = await detectSupport()
  if (supported && hasConsent()) {
    await warmupEdgeModel()
  }
}

export async function chatWithEdgeFallback(message) {
  const supported = await detectSupport()
  if (supported) {
    const ready = await warmupEdgeModel({ interactive: true })
    if (ready && wllama) {
      try {
        state.activity = 'AI 正在整理本地推理结果…'
        const result = await runEdgeChat(message)
        state.mode = 'ready'
        state.detail = `当前优先使用浏览器端 ${EDGE_MODEL.label}。`
        state.lastSource = 'browser'
        return result
      } catch (error) {
        console.warn('Edge AI inference failed, falling back to remote model:', error)
        return runFallbackChat(message, `浏览器端 ${EDGE_MODEL.label} 推理失败，已自动切换到远程模型。`)
      }
    }
  }

  return runFallbackChat(message, state.detail || '正在使用远程模型。')
}

export function useEdgeAiRuntime() {
  return {
    state: readonly(state),
    prime: primeEdgeAi,
    chat: chatWithEdgeFallback,
  }
}
