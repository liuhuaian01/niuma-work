<template>
<div class="page-view active" id="pageLab">
  <div class="page-header">
    <div><h1>实验室</h1><p class="page-subtitle">太极引擎 · 实验应用 · 持续进化</p></div>
  </div>
  <div class="page-body">
    <!-- 核心引擎状态 -->
    <div class="engine-hero">
      <div class="engine-hero-viz"><svg viewBox="0 0 120 120" fill="none"><circle cx="60" cy="60" r="56" stroke="currentColor" stroke-width="2" opacity=".4"/><path d="M60 4A56 56 0 0 1 60 116A28 28 0 0 1 60 60A28 28 0 0 0 60 4z" fill="currentColor" opacity=".6"/><circle cx="60" cy="32" r="8" fill="#0A0F18"/><circle cx="60" cy="88" r="8" fill="currentColor"/></svg></div>
      <div class="engine-hero-info">
        <h2>太极引擎 TaiChi Engine · 元大脑</h2>
        <p>太极哲学，循环进化，模型的大脑，越用越强。</p>
      </div>
      <div class="engine-hero-stats">
        <div class="engine-stat"><div class="engine-stat-value">29</div><div class="engine-stat-label">已激活引擎</div></div>
        <div class="engine-stat"><div class="engine-stat-value">35</div><div class="engine-stat-label">总模块数</div></div>
        <div class="engine-stat"><div class="engine-stat-value">100%</div><div class="engine-stat-label">核心链路覆盖</div></div>
        <div class="engine-stat"><div class="engine-stat-value">0</div><div class="engine-stat-label">致命Bug</div></div>
      </div>
    </div>

    <div class="engine-status-grid">
      <div v-for="engine in engines" :key="engine.name" class="engine-card">
        <div class="engine-card-header">
          <div class="engine-card-name">{{ engine.name }}</div>
          <div class="engine-card-status"><span class="engine-card-dot active"></span><span class="engine-card-label active">Active</span></div>
        </div>
        <div class="engine-card-desc">{{ engine.desc }}</div>
        <div class="engine-card-meta">
          <div v-for="m in engine.meta" :key="m.label" class="engine-card-meta-item">
            <span class="engine-card-meta-value">{{ m.value }}</span>
            <span class="engine-card-meta-label">{{ m.label }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 实验性应用 -->
    <div class="lab-section">
      <div class="lab-section-title">实验性应用</div>
      <div class="entity-card-grid">
        <div v-for="app in labApps" :key="app.name" class="entity-card" @click="showToast('打开: ' + app.name, 'info')">
          <div class="entity-card-header">
            <div class="entity-card-icon" :class="app.iconClass"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" width="22" height="22" v-html="app.iconPath"></svg></div>
            <div class="entity-card-info">
              <div class="entity-card-name">{{ app.name }}</div>
              <div class="entity-card-meta">{{ app.meta }}</div>
            </div>
          </div>
          <div class="entity-card-desc">{{ app.desc }}</div>
        </div>
      </div>
    </div>
  </div>
</div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useToast } from '@/composables/useToast'
const { showToast } = useToast()

const engines = [
  { name: '自愈引擎', desc: '最好的治理是不治理。系统自己发现问题、纠正问题、预防问题。你甚至不需要知道它做了什么。', meta: [{ value: '24/7', label: '自愈运行' }, { value: '100%', label: 'Coverage' }] },
  { name: '递归进化引擎', desc: '每一次对话都在让系统变得更聪明。进化不是版本号，是持续的呼吸。越用越懂你，越用越强。', meta: [{ value: '持续', label: '进化' }, { value: '✅', label: '桥接完成' }] },
  { name: '涌现引擎', desc: '当多个智能模块协同运转时，会自然涌现出设计者未曾预设的能力。群体的力量，远超个体之和。', meta: [{ value: '已激活', label: '状态' }, { value: '4', label: '能力域' }] },
  { name: '太极网格', desc: '算力如水，流动即生。节点自发组网，能力因共享而成倍增长。一个人的算力有限，一群人的力量无限。', meta: [{ value: '去中心', label: '组网' }, { value: 'P2P', label: '共享' }] },
  { name: 'Token压缩层', desc: '每一分算力都花在刀刃上。智能压缩让对话更轻、更快、更省。', meta: [{ value: '85%+', label: '压缩率' }, { value: '智能', label: '路由' }] },
  { name: '预知引擎', desc: '在你开口之前，答案已经在路上。越用越快，越用越准。', meta: [{ value: '75%', label: '命中率' }, { value: '实时', label: '响应' }] },
]

const labApps = [
  { name: 'Ollama', meta: 'v0.5.13 · Meta · 3 模型已加载', iconClass: 'ollama', iconPath: '<rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/>', desc: '本地大模型运行环境，支持 LLaMA、Mistral、Gemma 等开源模型一键部署与调用。' },
  { name: 'Anything LLM', meta: 'v1.8.3 · Mintplex Labs · 已连接', iconClass: 'anything', iconPath: '<polygon points="12 2 2 7 12 12 22 7 12 2"/><polyline points="2 17 12 22 22 17"/><polyline points="2 12 12 17 22 12"/>', desc: '多模型管理桌面端，支持 RAG 知识库、自定义 Agent、本地文档嵌入与检索。' },
  { name: 'Open WebUI', meta: 'v0.5.21 · ollama-webui · 已连接', iconClass: 'openwebui', iconPath: '<circle cx="12" cy="12" r="10"/><path d="M2 12h20"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>', desc: '类 ChatGPT 界面，对接 Ollama/OpenAI API，支持对话管理、插件市场和多用户。' },
  { name: 'ComfyUI', meta: 'v0.3.22 · comfyanonymous · 本地', iconClass: 'comfyui', iconPath: '<rect x="3" y="3" width="7" height="7"/><rect x="14" y="3" width="7" height="7"/><rect x="14" y="14" width="7" height="7"/><rect x="3" y="14" width="7" height="7"/>', desc: 'Stable Diffusion 工作流编辑器，节点化绘图流程，支持 ControlNet、LoRA 等扩展。' },
  { name: 'Dify', meta: 'v1.1.2 · langgenius · 已连接', iconClass: 'dify', iconPath: '<polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"/>', desc: 'LLMOps 平台，可视化编排 AI 工作流，支持 RAG、Agent、工具调用与应用发布。' },
  { name: 'Cursor', meta: 'v0.48.x · anysphere · 已安装', iconClass: 'cursor', iconPath: '<polyline points="16 18 22 12 16 6"/><polyline points="8 6 2 12 8 18"/>', desc: 'AI 原生 IDE，内置 AI 代码补全、多文件编辑、上下文感知。与 Hermes Agent 深度集成。' },
  { name: 'Diffusion Lab', meta: '实验性 · SDXL / Flux', iconClass: 'diffusion', iconPath: '<circle cx="12" cy="12" r="10"/><line x1="2" y1="12" x2="22" y2="12"/><path d="M12 2a15.3 15.3 0 0 1 4 10 15.3 15.3 0 0 1-4 10 15.3 15.3 0 0 1-4-10 15.3 15.3 0 0 1 4-10z"/>', desc: 'AI 绘图实验室，集成多个文生图模型和图像处理管线，支持批量生成与风格迁移。' },
]
</script>
