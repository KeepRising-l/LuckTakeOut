# LuckTakeOut 外卖平台

Django 后端 + Vue 3 前端（三端 SPA）。

## 启动

### 1. 后端 API（必须先启动）
```bat
takeout\run.bat
```
或 `cd takeout && .venv\Scripts\python.exe manage.py runserver 8091`
（LLM key 从 takeout/llm_key.txt 读取，未配置时 AI 客服走内置 Mock）

### 2. 前端

**方式一：演示模式（Django 直接托管构建产物）**
```bat
cd web && npm install && npm run build
```
然后直接访问 http://127.0.0.1:8091/

**方式二：开发模式（Vite 热更新）**
```bat
cd web && npm install && web\run-dev.bat
```
| 端 | 开发地址 | 生产地址（8091） |
| --- | --- | --- |
| 顾客端 H5 | http://localhost:5173 | http://127.0.0.1:8091/ |
| 商户端 | http://localhost:5174 | http://127.0.0.1:8091/merchant/ |
| 骑手端 | http://localhost:5175 | http://127.0.0.1:8091/rider/ |

## 测试账号
- 顾客：任意手机号 + 验证码 `123456`
- 商户：`merchant1` / `merchant123`（merchant2、3 同密码）
- 骑手：`rider1` / `rider123`

## 技术栈
- 后端：Django + SQLite（可切 MySQL），ResultAPI `{code, info, data}`，三类端独立盐值签名 token
- 前端：Vue 3 + Vite + TypeScript + Pinia + Vue Router；移动端 Vant 4 / 商户端 Element Plus + ECharts
- 结构：`web/` npm workspaces monorepo（`packages/shared` 公共请求层 + `apps/customer|merchant|rider`）
- 部署：三端构建产物由 Django 同源托管（`/` 顾客端、`/merchant/`、`/rider/`）；旧版静态页已移除
- 安全：`SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` 支持环境变量注入（`DJANGO_SECRET_KEY`/`DJANGO_DEBUG=0`/`DJANGO_ALLOWED_HOSTS`），生产模式未配密钥拒绝启动

## 演示链路
顾客点菜下单 → 模拟支付 → 商户接单 → 骑手抢单配送 → 顾客评价 →（AI 客服对话式下单）

## 文档导航

| 文档 | 位置 |
| --- | --- |
| 任务书（学院格式，含 Word 版） | `thesis-docs/00-任务书.md` / `.docx` |
| 需求分析（功能需求权威源） | `thesis-docs/02-需求分析.md` |
| 系统设计 | `thesis-docs/03-系统设计.md` |
| 产品需求（为什么这样设计 / 研究背景与意义） | `thesis-docs/04-产品需求说明书.md` |
| 项目功能技术详解（技术栈与亮点） | `thesis-docs/05-项目功能技术详解.md` |
| 答辩应对问答 | `thesis-docs/06-答辩应对问答.md` |
| 项目使用文档（四端操作 + 演示脚本） | `thesis-docs/07-项目使用文档.md` |
| 部署与数据库说明（换机运行 / 数据库脚本） | `thesis-docs/08-部署与数据库说明.md` |
| 数据库快照与恢复脚本 | `thesis-docs/db/` |
| 工程规格（47 条可验收要求） | `openspec/specs/` |
