# Niuma Agent 品牌资源

此目录包含超级牛马工作台的品牌视觉资源。

## 文件清单

### 1. niuma-icon.png (1.1 MB)
- **用途**: Niuma Agent Logo / Icon
- **尺寸**: 建议 512x512px 或更高
- **格式**: PNG (透明背景)
- **使用场景**:
  - Loading 页面 Logo
  - 应用图标
  - 品牌标识

### 2. niuma-running.mp4 (3.4 MB)
- **用途**: 牛马奔跑视频背景
- **时长**: 约 3-5 秒循环
- **格式**: MP4 (H.264 编码)
- **使用场景**:
  - Loading 页面动态背景
  - 品牌宣传视频
  - 启动动画

## 加载页面

访问 `http://localhost:8000/` 查看完整的 Loading 页面效果:
- 牛马奔跑视频背景(半透明)
- Niuma Agent Logo 脉冲动画
- 实时安装进度条
- 品牌渐变色彩(#00E5A0 → #8B5CF6)

## 品牌色彩

- **主色**: #00E5A0 (Niuma Green - 活力、成长)
- **辅色**: #8B5CF6 (Niuma Purple - 智慧、创新)
- **背景**: #0A0A0F (深色主题)
- **文字**: #F0F0F5 (浅色文字)

## 技术实现

### 静态文件服务

在 `main.py` 中已配置:
```python
assets_dir = Path(__file__).parent / "assets"
app.mount("/assets", StaticFiles(directory=str(assets_dir)), name="assets")
```

### 访问方式

前端可通过以下 URL 访问资源:
- Logo: `http://localhost:8000/assets/niuma-icon.png`
- 视频: `http://localhost:8000/assets/niuma-running.mp4`

## 未来扩展

可以添加更多品牌资源:
- `niuma-logo.svg` - SVG 矢量 Logo
- `niuma-avatar.png` - 圆形头像版本
- `niuma-banner.jpg` - 横幅图片
- `sounds/` - 音效文件

---

**更新日期**: 2026-06-15
**版本**: v1.0
