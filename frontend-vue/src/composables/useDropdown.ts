import { ref, onMounted, onBeforeUnmount } from 'vue'

/**
 * Shared dropdown/flyout composable.
 * Replaces prototype app.html's per-menu `document.addEventListener('click', ...)` pattern
 * with a single Vue-managed listener.
 *
 * Usage:
 *   const { openMenu, toggleMenu, closeMenu } = useDropdown()
 *   // In template: :class="{ open: openMenu === 'myMenu' }" @click="toggleMenu('myMenu')"
 */
export function useDropdown() {
  const openMenu = ref('')

  function toggleMenu(name: string) {
    openMenu.value = openMenu.value === name ? '' : name
  }

  function closeMenu() {
    openMenu.value = ''
  }

  function onDocClick(e: MouseEvent) {
    // If the click lands inside an open menu or on its trigger button, ignore
    const target = e.target as HTMLElement
    // Check if target is inside any .more-menu-float, .plus-menu, .sidebar-create-menu,
    // .model-dropdown, .agent-info-popup, or a known trigger button
    const closeSelectors = [
      '.more-menu-float', '.plus-menu', '.sidebar-create-menu',
      '.model-dropdown', '.agent-info-popup',
    ]
    const triggerSelectors = [
      '#moreMenuBtn', '#plusMenuBtn', '#mentionBtn', '#connectorBtn',
      '#modelPill', '#sidebarCreateBtn', '.header-action-btn',
      '.toolbar-plus-btn', '.toolbar-btn', '.model-pill',
    ]

    for (const sel of closeSelectors) {
      if (target.closest(sel)) return // click inside open menu
    }
    for (const sel of triggerSelectors) {
      if (target.closest(sel)) return // click on trigger — toggleMenu handles it
    }

    openMenu.value = ''
  }

  function onEsc(e: KeyboardEvent) {
    if (e.key === 'Escape' && openMenu.value) {
      openMenu.value = ''
    }
  }

  onMounted(() => {
    document.addEventListener('click', onDocClick)
    document.addEventListener('keydown', onEsc)
  })

  onBeforeUnmount(() => {
    document.removeEventListener('click', onDocClick)
    document.removeEventListener('keydown', onEsc)
  })

  return { openMenu, toggleMenu, closeMenu }
}
