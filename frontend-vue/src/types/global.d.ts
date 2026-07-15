export {}

declare global {
  interface Window {
    showNiumaToast: (msg: string, type?: string) => void
    navigateTo: (page: string) => void
  }
}
