/**
 * Super Niuma — Theme Manager v2.0
 * 
 * 三主题切换: Day (浅色) · Night (深色) · System (跟随系统)
 * 
 * 依赖: design-tokens.css (L0种子色体系)
 * 
 * 行为:
 * - 默认跟随系统 (data-theme 不设置)
 * - 用户选择后存储到 localStorage
 * - 监听系统主题变化 (matchMedia)
 * - 切换时添加 transition 类防止闪烁
 * 
 * 使用:
 *   import { initTheme } from './theme-manager.js';
 *   initTheme();
 * 
 * 全局 API:
 *   window.NiumaTheme.setTheme('day' | 'night' | 'system')
 *   window.NiumaTheme.getTheme() → 'day' | 'night' | 'system'
 */

(function () {
  'use strict';

  const STORAGE_KEY = 'niuma-theme';
  const THEMES = ['day', 'night', 'system'];

  // ── 内部 ──

  function getStoredTheme() {
    try {
      const stored = localStorage.getItem(STORAGE_KEY);
      return THEMES.includes(stored) ? stored : 'system';
    } catch {
      return 'system';
    }
  }

  function getSystemTheme() {
    return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'night' : 'day';
  }

  function getEffectiveTheme(preference) {
    return preference === 'system' ? getSystemTheme() : preference;
  }

  /**
   * 应用主题到 DOM
   * 'system' → 移除 data-theme 属性（让 CSS @media 规则生效）
   * 'day'    → data-theme="day"
   * 'night'  → data-theme="night"
   */
  function applyTheme(preference) {
    const effective = getEffectiveTheme(preference);

    // 添加过渡类防止颜色跳变
    document.documentElement.classList.add('theme-transitioning');
    
    if (preference === 'system') {
      document.documentElement.removeAttribute('data-theme');
      try { localStorage.removeItem(STORAGE_KEY); } catch {}
    } else {
      document.documentElement.setAttribute('data-theme', preference);
      try { localStorage.setItem(STORAGE_KEY, preference); } catch {}
    }

    // 移除过渡类
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        document.documentElement.classList.remove('theme-transitioning');
      });
    });

    return effective;
  }

  function updateToggleUI(preference) {
    const buttons = document.querySelectorAll('[data-theme-toggle]');
    buttons.forEach(btn => {
      const isActive = btn.dataset.themeToggle === preference;
      btn.classList.toggle('theme-toggle__option--active', isActive);
      btn.setAttribute('aria-checked', String(isActive));
    });
  }

  // ── 公开 API ──

  const ThemeManager = {
    current: 'system',

    setTheme(preference) {
      if (!THEMES.includes(preference)) {
        console.warn('[ThemeManager] 无效的主题:', preference);
        return;
      }
      this.current = preference;
      applyTheme(preference);
      updateToggleUI(preference);
    },

    getTheme() {
      return this.current;
    },

    getEffectiveTheme() {
      return getEffectiveTheme(this.current);
    },

    /** 初始化：读取存储 → 应用 → 监听系统变化 */
    init() {
      const stored = getStoredTheme();
      this.current = stored;
      applyTheme(stored);
      updateToggleUI(stored);

      // 监听系统主题变化（当用户选择 "system" 时生效）
      const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');
      
      // 现代浏览器使用 addEventListener
      if (mediaQuery.addEventListener) {
        mediaQuery.addEventListener('change', () => {
          if (this.current === 'system') {
            applyTheme('system');
            updateToggleUI('system');
          }
        });
      }
      // 兼容旧浏览器
      else if (mediaQuery.addListener) {
        mediaQuery.addListener(() => {
          if (this.current === 'system') {
            applyTheme('system');
            updateToggleUI('system');
          }
        });
      }

      // 绑定全局切换按钮事件
      document.addEventListener('click', (e) => {
        const toggleBtn = e.target.closest('[data-theme-toggle]');
        if (toggleBtn) {
          const theme = toggleBtn.dataset.themeToggle;
          this.setTheme(theme);
        }
      });

      console.log('[ThemeManager] 初始化完成，当前主题:', this.current, 
                  '生效主题:', this.getEffectiveTheme());
    }
  };

  // ── 全局暴露 ──
  window.NiumaTheme = ThemeManager;

  // ── 自动初始化（DOM 就绪后） ──
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => ThemeManager.init());
  } else {
    ThemeManager.init();
  }

})();
