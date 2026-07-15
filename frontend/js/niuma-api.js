/**
 * Niuma API Client v1.0
 * 太极引擎后端 API 对接层
 * 零依赖，纯 fetch + EventSource
 */
(function() {
  'use strict';

  var API_BASE = 'http://127.0.0.1:18080';

  var NiumaAPI = {
    version: '1.0',
    baseURL: API_BASE,

    // ── 对话接口 ──

    /**
     * 发送消息（非流式，返回消息ID用于后续SSE订阅）
     */
    sendMessage: function(workspaceId, content, model) {
      return fetch(API_BASE + '/api/v1/chat/messages', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          workspace_id: workspaceId || 'default',
          content: content,
          model: model || 'deepseek-chat',
          role: 'user'
        })
      }).then(function(r) {
        if (!r.ok) throw new Error('API error: ' + r.status);
        return r.json();
      });
    },

    /**
     * SSE 流式接收 AI 回复
     * @param {string} messageId - AI 消息 ID
     * @param {object} callbacks - { onToken, onDone, onError, onProgress }
     * @returns {function} stop - 停止流
     */
    streamResponse: function(messageId, callbacks) {
      var url = API_BASE + '/api/v1/chat/stream/' + messageId;
      var stopped = false;
      var abortController = new AbortController();

      callbacks = callbacks || {};
      var onToken = callbacks.onToken || function(){};
      var onDone = callbacks.onDone || function(){};
      var onError = callbacks.onError || function(){};
      var onProgress = callbacks.onProgress || function(){};

      fetch(url, {
        headers: { 'Accept': 'text/event-stream' },
        signal: abortController.signal
      }).then(function(response) {
        if (!response.ok) {
          onError({ code: 'HTTP_' + response.status, message: '连接失败' });
          return;
        }

        var reader = response.body.getReader();
        var decoder = new TextDecoder();
        var buffer = '';
        var fullContent = '';
        var metadata = {};

        function pump() {
          if (stopped) return;
          reader.read().then(function(result) {
            if (result.done) {
              onDone({ content: fullContent, metadata: metadata });
              return;
            }

            buffer += decoder.decode(result.value, { stream: true });
            var lines = buffer.split('\n');
            buffer = lines.pop() || '';

            var currentEvent = '';
            for (var i = 0; i < lines.length; i++) {
              var line = lines[i];
              if (line.startsWith('event: ')) {
                currentEvent = line.slice(7).trim();
              } else if (line.startsWith('data: ')) {
                try {
                  var data = JSON.parse(line.slice(6));
                  switch (currentEvent) {
                    case 'token':
                      fullContent += data.content || '';
                      onToken(data.content || '', data.index || 0, fullContent);
                      break;
                    case 'done':
                      metadata = data;
                      break;
                    case 'progress':
                      onProgress(data);
                      break;
                    case 'error':
                      onError(data);
                      break;
                  }
                } catch(e) {
                  // skip malformed data
                }
              }
            }
            pump();
          }).catch(function(err) {
            if (err.name !== 'AbortError') {
              onError({ code: 'STREAM_ERROR', message: err.message });
            }
          });
        }

        pump();
      }).catch(function(err) {
        if (err.name !== 'AbortError') {
          onError({ code: 'FETCH_ERROR', message: err.message });
        }
      });

      return {
        stop: function() {
          stopped = true;
          abortController.abort();
          // 通知后端停止
          fetch(API_BASE + '/api/v1/chat/stream/' + messageId + '/stop', { method: 'POST' })
            .catch(function(){});
        }
      };
    },

    /**
     * 停止流式生成
     */
    stopStream: function(messageId) {
      return fetch(API_BASE + '/api/v1/chat/stream/' + messageId + '/stop', {
        method: 'POST'
      });
    },

    /**
     * 获取消息历史
     */
    getMessages: function(workspaceId, page, pageSize) {
      var params = new URLSearchParams();
      if (workspaceId) params.set('workspace_id', workspaceId);
      if (page) params.set('page', page);
      if (pageSize) params.set('page_size', pageSize);
      return fetch(API_BASE + '/api/v1/chat/messages?' + params.toString())
        .then(function(r) { return r.json(); });
    },

    // ── 工作间接口 ──

    getWorkspaces: function() {
      return fetch(API_BASE + '/api/v1/workspaces')
        .then(function(r) { return r.json(); });
    },

    createWorkspace: function(name, template) {
      return fetch(API_BASE + '/api/v1/workspaces', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name: name, template: template || 'blank' })
      }).then(function(r) { return r.json(); });
    },

    // ── 健康检查 ──

    healthCheck: function() {
      return fetch(API_BASE + '/health')
        .then(function(r) { return r.json(); })
        .then(function(d) {
          d._online = true;
          return d;
        })
        .catch(function() {
          return { _online: false, status: 'offline' };
        });
    },

    // ── 模型列表 ──

    getModels: function() {
      return fetch(API_BASE + '/api/v1/models/available')
        .then(function(r) { return r.json(); })
        .catch(function() { return { models: [] }; });
    }
  };

  // 挂载到全局命名空间
  window.NiumaAPI = NiumaAPI;

  // ── 后端连接状态监控 ──
  var healthCheck = function() {
    NiumaAPI.healthCheck().then(function(result) {
      var dot = document.querySelector('#wfHermesStatus');
      var statusEl = document.getElementById('wfHermesStatus');
      if (result._online) {
        if (dot) dot.parentElement.querySelector('.wf-dot').classList.remove('off');
        if (statusEl) statusEl.textContent = '在线';
      } else {
        if (dot) dot.parentElement.querySelector('.wf-dot').classList.add('off');
        if (statusEl) statusEl.textContent = '离线';
      }
    });
  };

  // 每30秒检查一次
  setInterval(healthCheck, 30000);
  // 首次5秒后检查
  setTimeout(healthCheck, 5000);

  console.log('[NiumaAPI] API客户端已就绪，后端:', API_BASE);
})();
