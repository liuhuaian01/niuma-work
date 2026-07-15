import { onBeforeUnmount } from 'vue'

let toastContainer: HTMLElement | null = null
let toastTimers: number[] = []

function getContainer(): HTMLElement {
  if (toastContainer) return toastContainer
  const el = document.createElement('div')
  el.id = 'niumaToastContainer'
  el.className = 'toast-container'
  el.setAttribute('aria-live', 'polite')
  document.body.appendChild(el)
  toastContainer = el
  return el
}

const icons: Record<string, string> = {
  info: '<svg viewBox="0 0 24 24" fill="none" stroke="#6391ED" stroke-width="2" width="18" height="18"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12" y2="8"/></svg>',
  success: '<svg viewBox="0 0 24 24" fill="none" stroke="#34D399" stroke-width="2.5" width="18" height="18"><polyline points="20 6 9 17 4 12"/></svg>',
  warning: '<svg viewBox="0 0 24 24" fill="none" stroke="#FBBF24" stroke-width="2" width="18" height="18"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"/><line x1="12" y1="9" x2="12" y2="13"/><line x1="12" y1="17" x2="12" y2="17"/></svg>',
  error: '<svg viewBox="0 0 24 24" fill="none" stroke="#ef4444" stroke-width="2" width="18" height="18"><circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/></svg>',
}

export function useToast() {
  function showToast(msg: string, type: string = 'info', subtitle: string = '') {
    const container = getContainer()
    const t = document.createElement('div')
    t.className = 'toast-item'
    t.innerHTML =
      '<span class="toast-item-icon">' + (icons[type] || icons.info) + '</span>' +
      '<div class="toast-item-body"><div class="toast-item-title">' + msg + '</div>' +
      (subtitle ? '<div class="toast-item-sub">' + subtitle + '</div>' : '') + '</div>' +
      '<button class="toast-item-close" aria-label="关闭" onclick="this.parentElement.remove()"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" width="14" height="14"><line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/></svg></button>'
    container.appendChild(t)
    requestAnimationFrame(() => { t.classList.add('show') })
    const timer = window.setTimeout(() => {
      t.classList.remove('show')
      const t2 = window.setTimeout(() => { t.remove() }, 300)
      toastTimers.push(t2)
    }, 4000)
    toastTimers.push(timer)
  }

  onBeforeUnmount(() => {
    toastTimers.forEach(clearTimeout)
    toastTimers = []
  })

  return { showToast }
}
