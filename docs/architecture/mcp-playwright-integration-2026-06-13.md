# MCP Playwright 接入方案 — 超级牛马浏览器操控

> 日期：2026-06-13 | 目标：低成本实现 Kimi Claw WebBridge 等价能力

## 一、为什么需要浏览器操控

### Kimi Work 的 WebBridge 优势

```
Kimi Claw 实测能力:
  ✅ 登录 Jira → 提取任务 → 生成周报 → 发送钉钉
  ✅ 2000+ 社区工作流模板
  ✅ 支持验证码中途暂停人工输入
  ✅ 用户退订 Claude Computer Use
  
Kimi Claw 弱点:
  ❌ SPA页面点击坐标偏移10px
  ❌ 复杂动态页面兼容性差
```

### 超级牛马的切入点

```
超级牛马不需要做到 Kimi Claw 的完整度。
只需要满足:
  1. 网页内容抓取（研究/数据采集）
  2. 简单表单填写（自动化操作）
  3. 截图/页面快照（报告素材）
  4. 登录态管理（Cookie/Token 持久化）

实现方式: MCP Playwright Server
```

## 二、技术方案

### 2.1 MCP Playwright Server

```bash
# 官方 MCP Server
npx @playwright/mcp@latest
```

### 2.2 MCP 配置（超级牛马 mcp.json）

```json
{
  "mcpServers": {
    "playwright": {
      "command": "npx",
      "args": ["@playwright/mcp@latest"],
      "env": {
        "PLAYWRIGHT_BROWSERS_PATH": "0"  // 使用系统浏览器
      }
    }
  }
}
```

### 2.3 暴露的工具

| 工具 | 用途 | 对应 Kimi Claw 功能 |
|------|------|------|
| `browser_navigate` | 导航到URL | ✅ 打开网页 |
| `browser_click` | 点击元素 | ✅ 操作网页 |
| `browser_type` | 输入文本 | ✅ 表单填写 |
| `browser_snapshot` | 页面结构快照 | ✅ 页面分析 |
| `browser_take_screenshot` | 截图 | ✅ 报告素材 |
| `browser_evaluate` | 执行 JS | ⚠️ 高级操作 |
| `browser_fill_form` | 批量填表 | ✅ 表单自动化 |
| `browser_network_requests` | 网络请求监控 | ⚠️ API 调试 |
| `browser_console_messages` | 控制台日志 | ⚠️ 调试 |

### 2.4 与 Kimi Claw 的差距

| 能力 | Kimi Claw | MCP Playwright | 差距 |
|------|:--:|:--:|:--:|
| 社区模板库 | 2000+ | 无 | 🔴 大 |
| 验证码暂停 | ✅ | 需自行实现 | 🟡 中 |
| 坐标偏移容错 | 自动重试 | 需自行实现 | 🟡 中 |
| 跨域操作 | ✅ | ✅ | 🟢 无 |
| 截图/快照 | ✅ | ✅ | 🟢 无 |
| 系统密钥链集成 | ✅ | 需自行实现 | 🟡 中 |
| 跨会话持久化 | ✅ | 需自行实现 | 🟡 中 |

## 三、简单场景实现

### 3.1 网页内容抓取

```python
# 超级牛马 Agent → Playwright 工具调用
async def fetch_webpage(url, extract="main_content"):
    """抓取网页内容（研究任务）"""
    result = await mcp_call("playwright", "browser_navigate", {"url": url})
    snapshot = await mcp_call("playwright", "browser_snapshot", {})
    
    # 从快照中提取正文
    content = extract_from_snapshot(snapshot, extract)
    return content

# 使用场景：每日前沿研究自动化爬取
await fetch_webpage("https://github.com/nousresearch/hermes-agent/releases")
```

### 3.2 表单自动填写

```python
async def auto_login_and_extract(service_config):
    """自动登录并提取数据"""
    # 导航到登录页
    await mcp_call("playwright", "browser_navigate", {
        "url": service_config["login_url"]
    })
    
    # 填写登录表单
    await mcp_call("playwright", "browser_fill_form", {
        "fields": [
            {"selector": service_config["username_selector"], "value": service_config["username"]},
            {"selector": service_config["password_selector"], "value": service_config["password"]}
        ]
    })
    
    # 点击登录
    await mcp_call("playwright", "browser_click", {
        "selector": service_config["submit_selector"]
    })
    
    # 等待跳转
    await mcp_call("playwright", "browser_wait_for", {
        "text": service_config["success_indicator"]
    })
    
    return "login_success"
```

### 3.3 截图作为报告素材

```python
async def capture_dashboard(url, selector=".main-content"):
    """截取仪表盘作为报告素材"""
    await mcp_call("playwright", "browser_navigate", {"url": url})
    await mcp_call("playwright", "browser_wait_for", {"selector": selector})
    
    screenshot = await mcp_call("playwright", "browser_take_screenshot", {
        "selector": selector,
        "fullPage": False
    })
    
    return screenshot  # base64 图片
```

## 四、安全边界（Pi 准则）

```
✅ 允许:
  - 用户明确指定的 URL
  - 研究任务中的公开网页
  - 用户授权的服务（需确认凭据）

❌ 禁止:
  - 未经用户确认的任意 URL 访问
  - 在未授权服务上自动填写凭据
  - 访问本地文件路径（通过 browser_navigate file://）
  - 执行任意 JavaScript（browser_evaluate 需用户审批）

🔒 技术约束:
  - Playwright 运行在独立沙盒进程
  - Cookie/LocalStorage 不跨会话共享
  - 截图不包含密码/敏感字段（自动模糊处理）
  - 每次浏览器操作记录审计日志
```

## 五、接入清单

| # | 事项 | 优先级 | 状态 |
|:--:|------|:--:|:--:|
| 1 | 安装 Playwright MCP Server | P1 | ⬜ |
| 2 | 配置 mcp.json | P1 | ⬜ |
| 3 | 实现 fetch_webpage 工具 | P1 | ⬜ |
| 4 | 实现安全审计中间层 | P1 | ⬜ |
| 5 | 实现 Cookie 持久化 | P2 | ⬜ |
| 6 | 实现验证码暂停交互 | P2 | ⬜ |
| 7 | 社区工作流模板库 | P3 | ⬜ |

## 六、与 Kimi Claw 的错位竞争

```
Kimi Claw 优势区:
  完整浏览器操控 → 2000+模板 → 社区生态
  超级牛马不正面竞争

超级牛马优势区:
  研究抓取（RAG 知识库 → 自动结构化存储）
  表单自动化（记忆系统 → 记住你的常用服务配置）
  报告截图（太极引擎 → 自动选择合适的截图时机）

MCP Playwright 的定位:
  不是 Kimi Claw 的替代品
  是超级牛马工具链的一环
  是太极引擎的手和眼
```

## 七、结论

**MCP Playwright 是浏览器操控的最低成本实现（1个 npx 命令），但不要试图做成 Kimi Claw。** 

超级牛马的核心价值不在浏览器操控本身，而在于：
- 操控结果自动入库（RAG 知识库）—— Kimi Claw 不会
- 操控经验自动沉淀（记忆系统）—— Kimi Claw 不会
- 操控成本自动优化（Token 基准）—— Kimi Claw 不可见

**浏览器是手，记忆才是脑。**
