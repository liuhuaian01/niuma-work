<template>
  <div class="onboarding">
    <!-- 步骤 1: 欢迎 -->
    <div v-if="step === 1" class="onboard-card fade-in">
      <div class="onboard-logo">
        <svg viewBox="0 0 64 64" width="80" height="80">
          <circle cx="32" cy="32" r="30" fill="none" stroke="#4DA8F0" stroke-width="2"/>
          <text x="32" y="38" text-anchor="middle" fill="#4DA8F0" font-size="22" font-weight="bold">牛</text>
        </svg>
      </div>
      <h1>欢迎使用超级牛马工作台</h1>
      <p class="onboard-sub">AI 驱动的工作台，装完即用。</p>
      <div class="onboard-features">
        <div class="feature"><span class="check">&#10003;</span> 本地 AI 推理，数据不出电脑</div>
        <div class="feature"><span class="check">&#10003;</span> Gemma 4 + Qwen3 双模型支持</div>
        <div class="feature"><span class="check">&#10003;</span> 首次启动自动推荐最佳模型</div>
      </div>
      <div class="onboard-actions">
        <button class="btn-primary" @click="detectHardware">开始设置</button>
        <button class="btn-skip" @click="skipAll">跳过，使用云端 API</button>
      </div>
    </div>

    <!-- 步骤 2: 硬件检测 + 模型推荐 -->
    <div v-if="step === 2" class="onboard-card fade-in">
      <h2>检测硬件...</h2>
      <div class="hardware-info">
        <div class="hw-item">
          <span class="hw-label">内存</span>
          <span class="hw-value">{{ hardware.ram.toFixed(1) }} GB</span>
        </div>
        <div class="hw-item">
          <span class="hw-label">CPU 核心</span>
          <span class="hw-value">{{ hardware.cores }}</span>
        </div>
        <div class="hw-item" v-if="hardware.gpu">
          <span class="hw-label">显卡</span>
          <span class="hw-value">{{ hardware.gpu }}</span>
        </div>
      </div>
      <p class="recommend-text">推荐下载 <strong>{{ recommendedModel.name }}</strong></p>
      <p class="recommend-size">下载大小 {{ recommendedModel.size_gb }}GB，预计 {{ estimatedTime }} 分钟</p>
      <div class="model-options">
        <label v-for="m in models" :key="m.id" class="model-radio"
          :class="{ active: selectedModelId === m.id }">
          <input type="radio" v-model="selectedModelId" :value="m.id" />
          <span class="model-name">{{ m.name }}</span>
          <span class="model-size">{{ m.size_gb }}GB</span>
          <span class="model-tag" v-if="m.recommended">推荐</span>
        </label>
      </div>
      <div class="onboard-actions">
        <button class="btn-primary" @click="startDownload">下载并安装</button>
        <button class="btn-secondary" @click="step = 1">返回</button>
      </div>
    </div>

    <!-- 步骤 3: 下载进度 -->
    <div v-if="step === 3" class="onboard-card fade-in">
      <h2>正在下载 {{ selectedModel.name }}</h2>
      <div class="progress-bar">
        <div class="progress-fill" :style="{ width: downloadProgress + '%' }"></div>
      </div>
      <p class="progress-text">{{ downloadProgress }}%</p>
      <p class="progress-detail">
        {{ downloadedMB }}MB / {{ totalMB }}MB
        <span v-if="speed > 0"> · {{ speed }} MB/s</span>
      </p>
      <p class="progress-source">来源: {{ currentMirror }}</p>
      <div class="onboard-actions">
        <button class="btn-secondary" @click="cancelDownload" v-if="!downloadDone">取消</button>
      </div>
      <div v-if="downloadDone" class="download-success">
        <span class="check big">&#10003;</span>
        <p>下载完成！</p>
        <button class="btn-primary" @click="finish">进入超级牛马</button>
      </div>
      <div v-if="downloadError" class="download-error">
        <p>下载失败: {{ downloadError }}</p>
        <button class="btn-secondary" @click="retryDownload">重试</button>
        <button class="btn-skip" @click="skipAll">跳过，使用云端 API</button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'

const router = useRouter()

const step = ref(1)
const selectedModelId = ref('')
const downloadProgress = ref(0)
const downloadDone = ref(false)
const downloadError = ref('')
const downloadSpeed = ref(0)
const currentMirror = ref('hf-mirror.com')

const hardware = ref({ ram: 0, cores: 0, gpu: '' })
const models = ref<Array<{
  id: string; name: string; desc: string; size_gb: number;
  min_ram_gb: number; recommended: boolean; repo: string; file: string;
}>>([])

const selectedModel = computed(() =>
  models.value.find(m => m.id === selectedModelId.value) || models.value[0] || { name: '', size_gb: 0 }
)

const recommendedModel = computed(() =>
  models.value.find(m => m.recommended) || models.value[0] || { name: '', size_gb: 0 }
)

const estimatedTime = computed(() => {
  if (!selectedModel.value.size_gb) return '?'
  const mbps = 10 // 假设 10MB/s
  return Math.ceil(selectedModel.value.size_gb * 1024 / mbps / 60)
})

const totalMB = computed(() => Math.round(selectedModel.value.size_gb * 1024))
const downloadedMB = computed(() => Math.round(downloadProgress.value / 100 * totalMB.value))
const speed = computed(() => downloadSpeed.value)

async function detectHardware() {
  step.value = 2

  // 硬件检测 (客户端 JS API)
  if ('deviceMemory' in navigator) {
    hardware.value.ram = (navigator as any).deviceMemory || 8
  } else {
    hardware.value.ram = 8
  }
  hardware.value.cores = navigator.hardwareConcurrency || 4

  // 从后端获取可下载模型列表
  try {
    const resp = await fetch('/api/v1/models/downloadable')
    const data = await resp.json()
    if (data.success) {
      models.value = data.data.models || []
      // 自动选推荐
      const rec = models.value.find(m => m.recommended)
      if (rec) selectedModelId.value = rec.id
    }
  } catch {
    // fallback
    models.value = [
      { id: 'qwen3-8b', name: 'Qwen3 8B', desc: '', size_gb: 5.0, min_ram_gb: 10, recommended: true, repo: '', file: '' },
      { id: 'qwen3-14b', name: 'Qwen3 14B', desc: '', size_gb: 8.5, min_ram_gb: 16, recommended: false, repo: '', file: '' },
      { id: 'gemma-4-e4b', name: 'Gemma 4 E4B', desc: '', size_gb: 3.0, min_ram_gb: 6, recommended: false, repo: '', file: '' },
      { id: 'gemma-4-12b', name: 'Gemma 4 12B', desc: '', size_gb: 7.0, min_ram_gb: 12, recommended: false, repo: '', file: '' },
    ]
    selectedModelId.value = 'qwen3-8b'
  }
}

async function startDownload() {
  step.value = 3
  downloadProgress.value = 0
  downloadDone.value = false
  downloadError.value = ''

  try {
    // 触发下载
    const resp = await fetch('/api/v1/models/download', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model_id: selectedModelId.value, mirror: 'https://hf-mirror.com' }),
    })
    const data = await resp.json()
    if (!data.success) {
      downloadError.value = data.error?.message || '启动下载失败'
      return
    }

    const taskId = data.data.task_id

    // SSE 监听进度
    const es = new EventSource(`/api/v1/models/download/${taskId}/progress`)
    es.addEventListener('progress', (e) => {
      try {
        const d = JSON.parse(e.data)
        downloadProgress.value = Math.round(d.progress || 0)
        downloadSpeed.value = d.speed_mbps || 0
        if (d.mirror) currentMirror.value = d.mirror
      } catch {}
    })
    es.addEventListener('completed', () => {
      downloadDone.value = true
      downloadProgress.value = 100
      es.close()
    })
    es.addEventListener('failed', (e) => {
      try {
        const d = JSON.parse(e.data)
        downloadError.value = d.error || '下载失败'
      } catch {
        downloadError.value = '下载失败'
      }
      es.close()
    })
    es.addEventListener('cancelled', () => {
      downloadError.value = '下载已取消'
      es.close()
    })
    es.addEventListener('error', () => {
      if (es.readyState === EventSource.CLOSED && !downloadDone.value) {
        downloadError.value = '连接中断，请检查网络后重试'
      }
    })
  } catch (e: any) {
    downloadError.value = e.message || '网络错误'
  }
}

function cancelDownload() {
  downloadError.value = '下载已取消'
  step.value = 2
}

function retryDownload() {
  startDownload()
}

function skipAll() {
  router.push('/settings')
}

function finish() {
  router.push('/chat')
}

onMounted(() => {
  // 检查是否已完成过引导
  const onboarded = localStorage.getItem('niuma_onboarded')
  if (onboarded === 'true') {
    finish()
  }
})
</script>

<style scoped>
.onboarding {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 100vh;
  background: linear-gradient(135deg, #f5f7fa 0%, #e8edf5 100%);
}

.onboard-card {
  background: #ffffff;
  border-radius: 16px;
  padding: 48px 40px;
  max-width: 520px;
  width: 100%;
  box-shadow: 0 8px 32px rgba(0,0,0,0.08);
  text-align: center;
}

.onboard-logo { margin-bottom: 24px; }
.onboard-logo svg { filter: drop-shadow(0 2px 8px rgba(77,168,240,0.3)); }

h1 { font-size: 24px; font-weight: 700; color: #1a1a2e; margin: 0 0 8px; }
h2 { font-size: 20px; font-weight: 600; color: #1a1a2e; margin: 0 0 20px; }

.onboard-sub { color: #666; font-size: 14px; margin-bottom: 32px; }

.onboard-features { text-align: left; margin-bottom: 32px; }
.feature { padding: 8px 0; color: #444; font-size: 14px; }
.feature .check { color: #4DA8F0; margin-right: 8px; font-weight: bold; }

.onboard-actions { display: flex; flex-direction: column; gap: 12px; }

.btn-primary {
  background: linear-gradient(135deg, #4DA8F0, #3d8fd4);
  color: #fff; border: none; border-radius: 8px;
  padding: 12px 24px; font-size: 15px; font-weight: 600;
  cursor: pointer; transition: transform 0.15s, box-shadow 0.15s;
}
.btn-primary:hover { transform: translateY(-1px); box-shadow: 0 4px 16px rgba(77,168,240,0.3); }

.btn-secondary {
  background: #f0f0f0; color: #444; border: 1px solid #ddd;
  border-radius: 8px; padding: 12px 24px; font-size: 14px;
  cursor: pointer; transition: background 0.15s;
}
.btn-secondary:hover { background: #e5e5e5; }

.btn-skip {
  background: none; color: #999; border: none;
  padding: 8px; font-size: 13px; cursor: pointer;
}
.btn-skip:hover { color: #666; text-decoration: underline; }

/* Hardware info */
.hardware-info {
  display: flex; gap: 16px; justify-content: center;
  margin-bottom: 24px; flex-wrap: wrap;
}
.hw-item {
  background: #f5f7fa; border-radius: 10px;
  padding: 12px 20px; text-align: center;
}
.hw-label { display: block; font-size: 12px; color: #999; margin-bottom: 4px; }
.hw-value { font-size: 16px; font-weight: 600; color: #1a1a2e; }

.recommend-text { font-size: 16px; color: #333; margin-bottom: 4px; }
.recommend-size { font-size: 13px; color: #999; margin-bottom: 24px; }

/* Model options */
.model-options { display: flex; flex-direction: column; gap: 8px; margin-bottom: 24px; }
.model-radio {
  display: flex; align-items: center; gap: 10px;
  padding: 12px 16px; border: 2px solid #eee; border-radius: 10px;
  cursor: pointer; transition: border-color 0.15s;
}
.model-radio.active { border-color: #4DA8F0; background: #f0f7ff; }
.model-radio input[type="radio"] { accent-color: #4DA8F0; }
.model-name { flex: 1; text-align: left; font-size: 14px; font-weight: 500; }
.model-size { color: #999; font-size: 13px; }
.model-tag {
  background: #4DA8F0; color: #fff; font-size: 11px;
  padding: 2px 8px; border-radius: 10px; font-weight: 600;
}

/* Progress */
.progress-bar {
  height: 10px; background: #eee; border-radius: 5px;
  margin: 24px 0 12px; overflow: hidden;
}
.progress-fill {
  height: 100%; background: linear-gradient(90deg, #4DA8F0, #3d8fd4);
  border-radius: 5px; transition: width 0.3s;
}
.progress-text { font-size: 28px; font-weight: 700; color: #4DA8F0; margin: 0; }
.progress-detail { font-size: 13px; color: #999; margin: 4px 0; }
.progress-source { font-size: 12px; color: #ccc; margin-bottom: 24px; }

.download-success { margin-top: 24px; }
.download-success .check.big { font-size: 48px; color: #4DA8F0; display: block; margin-bottom: 8px; }
.download-success p { font-size: 16px; color: #333; margin-bottom: 16px; }

.download-error { margin-top: 24px; display: flex; flex-direction: column; gap: 12px; align-items: center; }
.download-error p { color: #e74c3c; font-size: 14px; }

/* Animation */
.fade-in { animation: fadeIn 0.5s ease-out; }
@keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }
</style>
