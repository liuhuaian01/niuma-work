/**
 * SSE 流式接收 composable
 */
import { ref } from 'vue'

export function useSSE() {
  const streaming = ref(false)
  const streamContent = ref('')
  const streamError = ref<string | null>(null)
  let eventSource: EventSource | null = null

  function connect(url: string, onDone?: () => void) {
    disconnect()
    streaming.value = true
    streamContent.value = ''
    streamError.value = null

    eventSource = new EventSource(url)

    eventSource.addEventListener('token', (e) => {
      try {
        const data = JSON.parse(e.data)
        if (data.token) streamContent.value += data.token
        if (data.tool_call) streamContent.value += `\n🔧 正在使用 ${data.tool_call}...\n`
      } catch {}
    })

    eventSource.addEventListener('done', (e) => {
      streaming.value = false
      onDone?.()
      disconnect()
    })

    eventSource.addEventListener('error', () => {
      if (eventSource?.readyState === EventSource.CLOSED) {
        streaming.value = false
        streamError.value = '连接已关闭'
        disconnect()
      }
    })
  }

  function disconnect() {
    eventSource?.close()
    eventSource = null
  }

  return { streaming, streamContent, streamError, connect, disconnect }
}
