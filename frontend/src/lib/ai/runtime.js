import { reactive, readonly } from 'vue'

import { aiApi } from '../../api'
import {
  EDGE_AI_PROMPT,
  EDGE_MODEL,
  EDGE_MODEL_PRIMARY_URL,
  EDGE_MODEL_CHAT_PARAMS,
  EDGE_MODEL_LOAD_PARAMS,
  EDGE_MODEL_REQUIRES_SPLIT,
  EDGE_MODEL_SIZE_LABEL,
  EDGE_MODEL_URLS_VALID,
  WLLAMA_CONFIG_PATHS,
} from './config'
import { buildEdgeUserPrompt, parseAiReply } from './prompt'

const EDGE_AI_CONSENT_KEY = 'edge_ai_download_approved'

const state = reactive({
  mode: 'checking',
  detail: '正在检测浏览器端 AI 能力…',
  ready: false,
  downloadProgress: 0,
  lastSource: null,
})

let detectPromise = null
let warmupPromise = null
let wllamaModulePromise = null
let wllama = null

async function loadWllamaModule() {
  if (!wllamaModulePromise) {
    wllamaModulePromise = import('@wllama/wllama')
  }
  return wllamaModulePromise
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
    `浏览器端 ${EDGE_MODEL.label} 首次使用需要下载 ${EDGE_MODEL_SIZE_LABEL} 模型，并占用较多显存/磁盘缓存。确认后将优先在本地运行，失败时自动回退到 Ollama。是否继续？`
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
      state.detail = '当前环境不支持浏览器端 AI，已使用 Ollama 回退。'
      return false
    }

    if (!isDesktopChromium()) {
      state.mode = 'fallback'
      state.detail = '首版浏览器端 AI 仅支持桌面 Chromium，当前已回退到 Ollama。'
      return false
    }

    if (!navigator.gpu) {
      state.mode = 'fallback'
      state.detail = '当前浏览器未启用 WebGPU，已回退到 Ollama。'
      return false
    }

    if (EDGE_MODEL_REQUIRES_SPLIT) {
      state.mode = 'fallback'
      state.detail = '当前 Gemma 4 E2B GGUF 是 3.42GB 单文件；浏览器端运行前需先切分为多个分片 URL，现已回退到 Ollama。'
      return false
    }

    if (!EDGE_MODEL_URLS_VALID || !EDGE_MODEL_PRIMARY_URL) {
      state.mode = 'fallback'
      state.detail = '浏览器端模型 URL 配置无效；请检查 VITE_EDGE_MODEL_URLS 是否为逗号分隔的 .gguf 分片地址，当前已回退到 Ollama。'
      return false
    }

    const adapter = await navigator.gpu.requestAdapter().catch(() => null)
    if (!adapter) {
      state.mode = 'fallback'
      state.detail = '当前设备无法分配 WebGPU adapter，已回退到 Ollama。'
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
      state.detail = '已取消浏览器端模型下载，当前继续使用 Ollama。'
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

      await wllama.loadModelFromUrl(EDGE_MODEL_PRIMARY_URL, {
        ...EDGE_MODEL_LOAD_PARAMS,
        progressCallback: ({ loaded, total }) => {
          if (!total) return
          state.downloadProgress = Math.max(0, Math.min(100, Math.round((loaded / total) * 100)))
          state.detail = `正在下载并预热浏览器端 ${EDGE_MODEL.label}… ${state.downloadProgress}%`
        },
      })

      await wllama.createChatCompletion({
        messages: [
          { role: 'system', content: EDGE_AI_PROMPT },
          { role: 'user', content: '请只回复“好”。' },
        ],
        max_tokens: 8,
        temperature: 0,
      })

      state.ready = true
      state.mode = 'ready'
      state.detail = `浏览器端 ${EDGE_MODEL.label} 已就绪，将优先本地推理。`
      return true
    } catch (error) {
      state.ready = false
      state.mode = 'fallback'
      state.detail = `浏览器端 ${EDGE_MODEL.label} 初始化失败，当前已回退到 Ollama。`
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

async function runEdgeChat(message) {
  const { data } = await aiApi.context()
  const response = await wllama.createChatCompletion({
    messages: [
      { role: 'system', content: EDGE_AI_PROMPT },
      { role: 'user', content: buildEdgeUserPrompt(message, data.shop_context) },
    ],
    ...EDGE_MODEL_CHAT_PARAMS,
  })

  const replyFull = response?.choices?.[0]?.message?.content || ''
  return {
    ...parseAiReply(replyFull),
    source: 'browser',
  }
}

async function runFallbackChat(message, detail) {
  const { data } = await aiApi.chat(message)
  state.mode = state.ready ? 'ready' : 'fallback'
  state.detail = detail || state.detail
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
        const result = await runEdgeChat(message)
        state.mode = 'ready'
        state.detail = `当前优先使用浏览器端 ${EDGE_MODEL.label}。`
        state.lastSource = 'browser'
        return result
      } catch (error) {
        console.warn('Edge AI inference failed, falling back to Ollama:', error)
        return runFallbackChat(message, `浏览器端 ${EDGE_MODEL.label} 推理失败，已自动回退到 Ollama。`)
      }
    }
  }

  return runFallbackChat(message, state.detail || '当前使用 Ollama 回退。')
}

export function useEdgeAiRuntime() {
  return {
    state: readonly(state),
    prime: primeEdgeAi,
    chat: chatWithEdgeFallback,
  }
}
