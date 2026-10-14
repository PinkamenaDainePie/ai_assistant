# 智慧课堂 UI 设计规范

> **使用方式**：每新增或改版页面，必须先阅读本文档，使用 `globals.css` 中的 `--ui-*` 设计令牌与 `ui-*` 组件类名，保证全站风格统一。  
> 风格参考：极简高对比、双栏卡片、下划线输入、大块主按钮（类 Awwwards 注册/登录模态）。

---

## 1. 设计理念

| 原则 | 说明 |
|------|------|
| 极简 | 少装饰、强留白；表单用下划线而非描边方框 |
| 高对比 | 黑主按钮 + 白/浅灰底；标题纯黑、辅助文字浅灰 |
| 双栏模态 | 左品牌区（浅灰）+ 右内容区（白），整体圆角卡片浮于深色蒙层 |
| 层级清晰 | 标签全大写小号；标题大号粗体；正文适中行高 |

---

## 2. 配色

### 2.1 CSS 变量（`globals.css` `:root`）

| 令牌 | 色值 | 用途 |
|------|------|------|
| `--ui-color-primary` | `#000000` | 主按钮、主标题、Logo |
| `--ui-color-primary-hover` | `#1A1A1A` | 主按钮悬停 |
| `--ui-color-accent-purple` | `#4D49C1` | 品牌装饰、强调图形 |
| `--ui-color-accent-mint` | `#98FF98` | 品牌装饰点缀 |
| `--ui-color-bg-page` | `#0D0D0D` | 全屏页深色蒙层底 |
| `--ui-color-bg-overlay` | `rgba(0, 0, 0, 0.55)` | 模态背后遮罩 |
| `--ui-color-bg-panel-muted` | `#F4F4F4` | 双栏卡片左侧品牌区 |
| `--ui-color-bg-panel` | `#FFFFFF` | 双栏卡片右侧、卡片、表格底 |
| `--ui-color-bg-subtle` | `#FAFAFA` | 次级区域、表头 |
| `--ui-color-border` | `#E0E0E0` | 输入下划线、次要按钮描边、表格线 |
| `--ui-color-border-strong` | `#CCCCCC` | 悬停、选中描边 |
| `--ui-color-text-primary` | `#000000` | 标题、正文强调 |
| `--ui-color-text-secondary` | `#4A4A4A` | 正文、说明 |
| `--ui-color-text-muted` | `#666666` | 法律说明、次要信息 |
| `--ui-color-text-label` | `#999999` | 表单标签、占位符 |
| `--ui-color-text-inverse` | `#FFFFFF` | 主按钮文字 |
| `--ui-color-error` | `#D93025` | 错误提示 |
| `--ui-color-success` | `#1B7F4B` | 成功状态 |

### 2.2 配色规则

- 一页最多 **1 个主色（黑）** + **1 组点缀色（紫/薄荷）**，点缀仅用于品牌区图形，不用于大面背景。
- 禁止在表单区使用大面积渐变或古风纹理；课堂门户游戏内页可保留独立主题，但 **登录/后台/设置** 必须遵循本规范。

---

## 3. 字体

### 3.1 字体族

```css
--ui-font-sans: 'Inter', 'PingFang SC', 'Hiragino Sans GB', 'Microsoft YaHei', system-ui, sans-serif;
```

通过 `next/font` 加载 Inter；中文回退系统黑体。

### 3.2 字号与字重

| 层级 | 类名 / 用途 | 字号 | 字重 | 行高 | 颜色 |
|------|-------------|------|------|------|------|
| Display | 品牌区大标题 | `2.5rem` (40px) | 700 | 1.15 | primary |
| H1 | 表单主标题 | `1.75rem` (28px) | 700 | 1.25 | primary |
| H2 | 区块标题 | `1.25rem` (20px) | 600 | 1.35 | primary |
| Body | 正文 | `0.9375rem` (15px) | 400 | 1.6 | secondary |
| Small | 说明、页脚 | `0.8125rem` (13px) | 400 | 1.55 | muted |
| Label | 表单标签 | `0.6875rem` (11px) | 600 | 1.4 | label |
| Button | 按钮文字 | `0.9375rem` (15px) | 600 | 1 | inverse |

### 3.3 标签样式

- 表单标签：**全大写**（英文）或 **小号加粗**（中文），`letter-spacing: 0.08em`。
- 标题与标签对比：标题至少比标签大 **2 级字号**。

---

## 4. 间距

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--ui-space-1` | `4px` | 图标与文字间隙 |
| `--ui-space-2` | `8px` | 紧凑元素 |
| `--ui-space-3` | `12px` | 标签与输入间距 |
| `--ui-space-4` | `16px` | 表单项之间 |
| `--ui-space-5` | `24px` | 区块内分组 |
| `--ui-space-6` | `32px` | 卡片内边距（小屏） |
| `--ui-space-7` | `48px` | 卡片内边距（桌面） |
| `--ui-space-8` | `64px` | 模块与模块之间 |

### 4.1 布局留白

- 双栏模态内边距：桌面 `48px 56px`，移动 `32px 24px`。
- 表单项垂直间距：`24px`（`--ui-space-5`）。
- 主按钮与上一元素：`32px`（`--ui-space-6`）。
- 页面外边距：模态距视口至少 `24px`。

---

## 5. 圆角与阴影

| 令牌 | 值 | 用途 |
|------|-----|------|
| `--ui-radius-sm` | `6px` | 小按钮、标签 |
| `--ui-radius-md` | `8px` | 主按钮、输入聚焦环 |
| `--ui-radius-lg` | `16px` | 双栏模态外框、大卡片 |
| `--ui-radius-full` | `9999px` | 圆形装饰 |
| `--ui-shadow-modal` | `0 24px 80px rgba(0,0,0,0.35)` | 浮层卡片 |
| `--ui-shadow-sm` | `0 2px 8px rgba(0,0,0,0.06)` | 次要卡片 |

- **输入框无圆角边框**；仅底部分割线。
- 导航栏：无阴影或 `--ui-shadow-sm`；底边 `1px solid var(--ui-color-border)`。

---

## 6. 组件样式

### 6.1 按钮

| 类型 | 类名 | 样式 |
|------|------|------|
| 主按钮 | `ui-btn ui-btn--primary` | 黑底白字、圆角 8px、高 `48px`、全宽（表单内） |
| 次按钮 | `ui-btn ui-btn--secondary` | 白底、1px `#E0E0E0` 描边、黑字 |
| 幽灵 | `ui-btn ui-btn--ghost` | 透明底、无边框、黑字；悬停浅灰底 |

悬停：主按钮 `#1A1A1A`；次按钮边框 `#CCC`。  
禁用：`opacity: 0.45`，`cursor: not-allowed`。

### 6.2 输入框

类名：`ui-field` > `ui-label` + `ui-input`

- 仅 **底部 1px** 边框 `var(--ui-color-border)`。
- 无左右上边框、无背景色。
- 聚焦：底边变 `var(--ui-color-primary)`。
- 占位符：`var(--ui-color-text-label)`。

### 6.3 卡片 / 模态

| 类名 | 说明 |
|------|------|
| `ui-auth-page` | 全屏深色底 + flex 居中 |
| `ui-auth-modal` | 双栏容器，圆角 16px，阴影 modal |
| `ui-auth-brand` | 左栏 `#F4F4F4`，品牌与装饰 |
| `ui-auth-panel` | 右栏白底，表单区 |
| `ui-card` | 单栏白卡片，圆角 16px，padding 32px |
| `ui-shell` | 后台页：浅灰底 `#FAFAFA` + 最大宽度 1120px |

### 6.4 表格（教师后台）

类名：`ui-table-wrap` > `ui-table`

- 表头：背景 `#FAFAFA`，字重 600，字号 13px。
- 单元格：padding `12px 16px`，底边 `1px solid #E0E0E0`。
- 链接：`#4D49C1`，悬停下划线。

### 6.5 导航 / 页头

类名：`ui-header`

- 高 `auto`，padding `32px 0 24px`
- 标题 H1 + 副标题 Small muted
- 操作区右对齐（如「退出登录」用 `ui-btn--ghost`）

### 6.6 用户头像菜单

类名：`ui-avatar-menu`（导航栏右上角）

- 圆形头像，悬停下方弹出「个人中心 / 退出登录」
- 点击头像跳转 `/account`
- 头像预设存 `localStorage`（按 user id）

### 6.7 个人中心 `/account`

- 换头像（预设色 / 上传 ≤512KB）
- 统计卡片、剧本分布条形图、状态环形图
- 游玩存档表格（来自 `/api/playthroughs/mine`）


类名：`ui-header`

- 高 `auto`，padding `32px 0 24px`。
- 标题 H1 + 副标题 Small muted。
- 操作区右对齐（如「退出登录」用 `ui-btn--ghost`）。

---

## 7. 页面模板

### 7.1 登录 / 注册

- **背景**：全屏循环视频（`/ui/auth/login-bg.mp4`）+ 浅色半透明蒙层，禁止纯黑底。
- **品牌区**：仅两行标题（主标题 + 副标题），无图标、无长段说明。
- **结构**：

```
ui-auth-page
  ├── AuthVideoBackground（固定全屏视频 + overlay）
  └── ui-auth-modal
        ├── ui-auth-brand（左：印鉴 + 标题）
        └── ui-auth-panel（右：表单）
```

### 7.2 后台列表页（教师 / 个人中心）

全宽 **Console 布局**（参考 B 端后台：侧栏 + 顶栏 + 内容区），禁止居中窄栏导致两侧露黑底。

```
ui-console
  ├── ui-console__sidebar（左栏 240px 白底）
  └── ui-console__main
        ├── ui-console__topbar
        └── ui-console__body
              ├── ui-console-stats
              └── ui-panel
```

`html.ui-console-root` 时页面背景 `#f0f2f5`。

---

## 8. 动效

- 过渡：`transition: color, background, border-color 0.2s ease`。
- 模态入场：可选 `opacity + translateY(12px)`，300ms ease-out。
- 避免大面积动画与游戏内 UI 冲突。

---

## 9. 无障碍

- 表单控件必须有可见 `<label>` 或 `aria-label`。
- 主按钮与背景对比度 ≥ 4.5:1。
- 错误信息使用 `ui-error`，附 `role="alert"`。

---

## 10. 文件与实现

| 文件 | 职责 |
|------|------|
| `frontend/design.md` | 本文档 |
| `frontend/app/globals.css` | `--ui-*` 令牌与 `ui-*` 类 |
| `frontend/app/layout.tsx` | Inter 字体加载 |

**新页面检查清单**

- [ ] 使用 `--ui-*` 颜色，无硬编码随意色值
- [ ] 标题/正文符合字号表
- [ ] 间距为 4 的倍数，优先用 `--ui-space-*`
- [ ] 按钮/输入/卡片使用规范类名
- [ ] 与登录页、教师后台视觉一致
