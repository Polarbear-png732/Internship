# Web App 1 优化报告

**模型:** Gemini-3-Pro-Preview
**日期:** 2026-01-22

## 1. 项目概览
本项目是一个视频内容运营管理平台。
- **后端:** FastAPI (Python)，配合 PyMySQL 和 DBUtils。
- **前端:** 原生 JavaScript，配合 Vue.js (CDN) 和 Tailwind CSS (CDN)。
- **数据库:** MySQL。
- **核心功能:** Excel 文件导入/处理，客户/剧头管理。

## 2. 关键性能优化

### 2.1 后端：异步路由中的阻塞操作 (高危)
**问题:** 应用程序在 `async def` 路由处理函数中混合使用了同步数据库操作 (`pymysql`)。
**位置:** `routers/customers.py` (以及其他文件), `database.py`。
**影响:** 当 `async def` 函数调用阻塞操作（如 `cursor.execute`）时，它会阻塞整个事件循环。这实际上将请求变成了串行处理，抵消了使用 FastAPI 的优势，导致并发性能极差。
**建议:**
- **立即修复:** 将使用同步 DB 调用的路由处理函数从 `async def` 改为 `def`（例如在 `routers/customers.py` 中）。FastAPI 会在线程池中运行标准的 `def` 函数，这对于阻塞 I/O 是安全的。
- **长期方案:** 迁移到异步数据库驱动，如 `aiomysql` 或 `asyncmy`，并对数据库调用使用 `await`。

### 2.2 前端：Tailwind CSS 运行时编译
**问题:** 项目使用了 CDN 版本的 Tailwind CSS (`tailwindcss.js`)，它在浏览器端运行时编译 CSS。
**位置:** `index.html` (第 13 行)。
**影响:** 这会导致“样式闪烁” (FOUC)，并在初始加载时占用大量客户端 CPU 资源，尤其是对于移动用户。
**建议:**
- 在开发/构建阶段使用 Tailwind CLI 生成静态 CSS 文件。
- 在 `index.html` 中链接静态 CSS 文件，并移除 JS 运行时脚本。

### 2.3 前端：高频轮询
**问题:** 导入进度每 500ms 轮询一次。
**位置:** `static/js/main.js` (第 2006 行)。
**影响:** 造成不必要的服务器负载，尤其是在多用户并发时。
**建议:**
- 将轮询间隔增加到 2-3 秒。
- 或者，实现 WebSocket 或 Server-Sent Events (SSE) 以进行实时进度更新。

## 3. 安全漏洞

### 3.1 跨站脚本攻击 (XSS)
**问题:** 用户输入未经过滤直接使用 `innerHTML` 注入到 DOM 中。
**位置:** `static/js/main.js` (例如 `renderCustomerTable` 函数)。
**影响:** 如果恶意用户在 `customer_name` 或 `remark` 中注入脚本，它将在其他用户的浏览器中执行。
**建议:**
- 使用 `textContent` 设置文本。
- 如果必须渲染 HTML，请使用清洗库（如 DOMPurify）。
- 在 Vue.js 中，使用 `v-text` 或 `{{ }}` 插值，它们会自动处理转义（尽管当前代码主要使用原生 JS 字符串模板）。

### 3.2 CORS 配置
**问题:** CORS 配置为允许所有来源 (`allow_origins=["*"]`)。
**位置:** `main.py`。
**影响:** 允许任何恶意网站向您的 API 发起经过身份验证的请求（虽然目前未见明显的身份验证机制，但这是一种不良实践）。
**建议:** 在生产环境中将 `allow_origins` 限制为特定的受信任域名。

## 4. 代码质量与可维护性

### 4.1 单体前端逻辑
**问题:** `static/js/main.js` 是一个包含 API 调用、UI 逻辑和事件处理的大文件（>2000 行）。
**建议:** 重构为 ES 模块：
- `api.js`: 处理所有 `fetch` 请求。
- `components/`: 处理特定表格/模态框的渲染逻辑。
- `utils.js`: 存放工具函数。

### 4.2 硬编码配置
**问题:** 路径如 `temp/uploads` 是硬编码的。
**位置:** `services/import_service.py`。
**建议:** 将所有文件路径和常量移动到 `config.py` 或环境变量中。

### 4.3 静态文件服务
**问题:** FastAPI 通过 `StaticFiles` 直接提供静态文件服务。
**建议:** 在生产环境中，使用 Nginx 或类似的反向代理直接提供 `static/` 目录服务。这要快得多，并且可以释放 Python 应用服务器来处理 API 请求。

## 5. 下一步行动总结
1.  **重构路由:** 移除使用同步 DB 调用的路由中的 `async` 关键字。
2.  **输入清洗:** 修复 `main.js` 中的 XSS 漏洞。
3.  **优化构建:** 为 Tailwind CSS 设置构建流程。
4.  **重构导入服务:** 拆分巨大的 `execute_import_sync` 函数。
