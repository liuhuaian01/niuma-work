/**
 * Niuma Chat Bridge v1.0
 * 桥接前端原型与后端 API，用真实 SSE 流式对话替换模拟逻辑。
 * 在 niuma-api.js 之后加载。
 */
(function() {
  'use strict';

  if (!window.NiumaAPI) {
    console.warn('[ChatBridge] NiumaAPI 未加载，无法桥接');
    return;
  }

  var API = window.NiumaAPI;
  var currentWorkspaceId = 'default';
  var currentStream = null;
  var selectedModel = 'deepseek-chat';

  // ── 替换核心发送逻辑 ──

  /**
   * 新的 sendFromTextarea —— 走后端 API
   */
  function sendToAPI(textarea, sendBtn, fromHome) {
    var text = textarea.value.trim();
    if (!text) return;
    textarea.value = '';
    textarea.rows = 1;
    textarea.style.height = '';
    if (sendBtn) sendBtn.blur();

    if (fromHome) {
      navigateTo('chat');
      setTimeout(function() {
        sendMessageToBackend(text);
      }, 50);
    } else {
      sendMessageToBackend(text);
    }
  }

  /**
   * 发送消息到后端并启动 SSE 流
   */
  function sendMessageToBackend(text) {
    // 0. 显示处理状态
    if (typeof startProcessing === 'function') startProcessing();

    // 1. 添加用户消息到 UI
    addUserMessage(text);

    // 2. 创建 AI 消息占位
    var aiMsgEl = createAIMessagePlaceholder();
    var fullContent = '';

    // 3. 切换到停止按钮
    var stopBtn = document.getElementById('stopBtn');
    var sndBtn = document.getElementById('sendBtn');
    if (stopBtn && sndBtn) {
      sndBtn.classList.add('hidden');
      stopBtn.classList.remove('hidden');
    }

    // 4. 调用后端 API
    API.sendMessage(currentWorkspaceId, text, selectedModel)
      .then(function(result) {
        var data = result.data || result;
        var aiMessageId = data.ai_message_id || data.stream_url;

        if (!aiMessageId && data.stream_url) {
          // 可能是完整 URL
          aiMessageId = data.stream_url.split('/').pop();
        }

        if (!aiMessageId) {
          if (typeof stopProcessing === 'function') stopProcessing();
          updateAIMessage(aiMsgEl, '【错误】后端未返回消息 ID', true);
          resetSendButton();
          return;
        }

        // 5. 启动 SSE 流
        currentStream = API.streamResponse(aiMessageId, {
          onToken: function(token, index, cumulative) {
            fullContent = cumulative;
            updateAIMessage(aiMsgEl, fullContent, false);

            // 更新底部状态栏
            var tokenEl = document.getElementById('wfToken');
            if (tokenEl) {
              var t = parseInt(tokenEl.textContent) || 0;
              tokenEl.textContent = (t + 0.5).toFixed(1) + 'k';
            }
          },
          onDone: function(result) {
            if (typeof stopProcessing === 'function') stopProcessing();
            updateAIMessage(aiMsgEl, fullContent, true);
            resetSendButton();
            currentStream = null;

            // 更新模型状态
            var modelEl = document.querySelector('#wfHermesStatus');
            if (modelEl && result.metadata && result.metadata.model) {
              modelEl.textContent = result.metadata.model;
            }
          },
          onError: function(err) {
            if (typeof stopProcessing === 'function') stopProcessing();
            updateAIMessage(aiMsgEl, '【错误】' + (err.message || '连接中断'), true);
            resetSendButton();
            currentStream = null;
          }
        });
      })
      .catch(function(err) {
        if (typeof stopProcessing === 'function') stopProcessing();
        updateAIMessage(aiMsgEl, '【错误】无法连接后端服务 (' + err.message + ')', true);
        resetSendButton();
      });
  }

  /**
   * 获取消息时间
   */
  function getMsgTime() {
    var d = new Date();
    return d.getHours().toString().padStart(2,'0') + ':' + d.getMinutes().toString().padStart(2,'0');
  }

  /**
   * 添加用户消息气泡
   */
  function addUserMessage(text) {
    var inner = document.querySelector('.messages-inner');
    if (!inner) return;
    var div = document.createElement('div');
    div.className = 'message user';
    div.innerHTML = '<div class="msg-avatar" style="background:var(--brand-gradient)">U</div>' +
      '<div class="msg-content"><div class="msg-meta"><span class="msg-name">You</span>' +
      '<span class="msg-time">' + getMsgTime() + '</span></div>' +
      '<div class="msg-bubble">' + text.replace(/</g,'&lt;').replace(/>/g,'&gt;') + '</div></div>';
    inner.appendChild(div);
    scrollToBottom();
  }

  /**
   * 创建 AI 消息占位元素
   */
  function createAIMessagePlaceholder() {
    var inner = document.querySelector('.messages-inner');
    if (!inner) return null;
    var div = document.createElement('div');
    div.className = 'message ai streaming';
    div.innerHTML = '<div class="msg-avatar" style="background:linear-gradient(135deg,#8B5CF6,#06B6D4)">AI</div>' +
      '<div class="msg-content"><div class="msg-meta"><span class="msg-name">太极引擎</span>' +
      '<span class="msg-time">' + getMsgTime() + '</span></div>' +
      '<div class="msg-bubble"><span class="stream-cursor">▌</span></div></div>';
    inner.appendChild(div);
    scrollToBottom();
    return div;
  }

  /**
   * 更新 AI 消息内容（带打字机效果）
   */
  function updateAIMessage(el, content, isComplete) {
    if (!el) return;
    var bubble = el.querySelector('.msg-bubble');
    if (!bubble) return;

    if (isComplete) {
      el.classList.remove('streaming');
      bubble.innerHTML = formatMessage(content);
    } else {
      bubble.innerHTML = formatMessage(content) + '<span class="stream-cursor">▌</span>';
    }
    scrollToBottom();
  }

  /**
   * 简单 Markdown 格式化
   */
  function formatMessage(text) {
    return text
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
      .replace(/\*(.*?)\*/g, '<em>$1</em>')
      .replace(/`([^`]+)`/g, '<code>$1</code>')
      .replace(/\n/g, '<br>');
  }

  /**
   * 重置发送按钮状态
   */
  function resetSendButton() {
    var stopBtn = document.getElementById('stopBtn');
    var sndBtn = document.getElementById('sendBtn');
    if (stopBtn && sndBtn) {
      stopBtn.classList.add('hidden');
      sndBtn.classList.remove('hidden');
    }
  }

  /**
   * 滚动到底部
   */
  function scrollToBottom() {
    var area = document.querySelector('.messages-area');
    if (area) area.scrollTop = area.scrollHeight;
  }

  // ── 覆盖发送逻辑 ──

  // 保存原始函数引用
  var _originalSendFromTextarea = window.sendFromTextarea;

  /**
   * 根据后端可用性自动选择真实/模拟模式
   */
  window.sendFromTextarea = function(textarea, sendBtn, fromHome) {
    API.healthCheck().then(function(health) {
      if (health._online) {
        // 后端在线：走真实 API
        sendToAPI(textarea, sendBtn, fromHome);
      } else {
        // 后端离线：回退到原始模拟逻辑
        if (typeof _originalSendFromTextarea === 'function') {
          _originalSendFromTextarea(textarea, sendBtn, fromHome);
        } else {
          // 降级：基本模拟
          var text = textarea.value.trim();
          if (!text) return;
          textarea.value = '';
          addUserMessage(text);
          setTimeout(function() {
            var inner = document.querySelector('.messages-inner');
            if (!inner) return;
            var div = document.createElement('div');
            div.className = 'message ai';
            div.innerHTML = '<div class="msg-avatar" style="background:linear-gradient(135deg,#8B5CF6,#06B6D4)">AI</div>' +
              '<div class="msg-content"><div class="msg-meta"><span class="msg-name">太极引擎</span>' +
              '<span class="msg-time">' + getMsgTime() + '</span></div>' +
              '<div class="msg-bubble">后端服务未启动，当前为离线演示模式。<br><br>请启动后端：<code>cd backend && python main.py</code></div></div>';
            inner.appendChild(div);
            scrollToBottom();
          }, 800);
        }
      }
    });
  };

  /**
   * 覆盖聊天发送函数
   */
  window._sendFromChat = function(ta) {
    if (!ta) ta = document.querySelector('#inputCard .input-textarea');
    if (!ta) return;
    var btn = document.getElementById('sendBtn');
    sendFromTextarea(ta, btn, false);
    if (btn) btn.classList.remove('has-content');
  };

  window._sendFromHome = function(ta) {
    if (!ta) ta = document.querySelector('#homeInputCard .input-textarea');
    if (!ta) return;
    var btn = document.getElementById('homeSendBtn');
    sendFromTextarea(ta, btn, true);
    if (btn) btn.classList.remove('has-content');
  };

  // ── 停止按钮 ──
  var stopBtn = document.getElementById('stopBtn');
  if (stopBtn) {
    stopBtn.addEventListener('click', function() {
      if (currentStream) {
        currentStream.stop();
        currentStream = null;
      }
      resetSendButton();
      if (typeof showToast === 'function') showToast('生成已停止');
    });
  }

  // ── 初始健康检查 ──
  setTimeout(function() {
    API.healthCheck().then(function(health) {
      var statusEl = document.getElementById('wfHermesStatus');
      if (statusEl) {
        statusEl.textContent = health._online ? '在线' : '离线';
      }
      var dot = document.querySelector('#wfHermesStatus');
      if (dot && dot.parentElement) {
        var dotEl = dot.parentElement.querySelector('.wf-dot');
        if (dotEl) {
          if (health._online) dotEl.classList.remove('off');
          else dotEl.classList.add('off');
        }
      }
    });
  }, 1000);

  // ── 暴露 API ──
  window.NiumaChat = {
    send: sendMessageToBackend,
    stop: function() { if (currentStream) { currentStream.stop(); currentStream = null; } },
    setWorkspace: function(id) { currentWorkspaceId = id; },
    setModel: function(model) { selectedModel = model; },
    getStatus: function() { return { connected: !!currentStream, model: selectedModel, workspace: currentWorkspaceId }; }
  };

  console.log('[ChatBridge] 对话桥接已就绪，模式: auto-detect');
})();
