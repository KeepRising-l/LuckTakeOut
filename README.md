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
- 顾客：任意手机号 + 验证码 `123456`（`13700000001` 为演示账号，含历史订单）
- 商户：统一密码 `merchant123`

| 账号 | 店铺 | 品类 |
| --- | --- | --- |
| `merchant1` | 川香小馆 | 川菜 |
| `merchant2` | 快乐奶茶 | 奶茶饮品 |
| `coffee1` | 晨光咖啡 | 咖啡烘焙 |
| `noodle1` | 面面俱到 | 面食 |
| `fastfood1` | 快意小厨 | 快餐便当 |
| `sushi1` | 江户寿司 | 寿司日料 |

- 骑手：`rider1` / `rider123`

## 演示数据

```bat
cd takeout
.venv\Scripts\python.exe scripts\fetch_food_images.py   :: 抓取自由许可菜品图（可选，已入库可跳过）
.venv\Scripts\python.exe manage.py seed_shops           :: 生成 6 家商户与 30 道菜
```

图片来自 Wikimedia Commons / TheMealDB 的 CC 或公有领域素材，来源与许可清单见
`takeout/media/products/sources.json`。

## 图片存储

- **文件**：全部落在 `takeout/media/`（`MEDIA_ROOT`），数据库只存路径字符串
- **目录**：`products/<店铺>/` 演示菜品图 ｜ `products/uploads/` 商家后台上传 ｜ `avatar/` 门店头像
- **访问**：开发态由 Django `static()` 在 `/media/...` 下托管，Vite 已把 `/media` 代理到 8091；
  生产环境建议交给 nginx 直接托管，不要走 Django
- **商家上传**：菜品管理 → 新增/编辑菜品 → 图片 → 选择本地图片即上传（≤5MB，jpg/png/webp/gif）

## 技术栈
- 后端：Django + SQLite（可切 MySQL），ResultAPI `{code, info, data}`，三类端独立盐值签名 token
- 前端：Vue 3 + Vite + TypeScript + Pinia + Vue Router；移动端 Vant 4 / 商户端 Element Plus + ECharts
- 结构：`web/` npm workspaces monorepo（`packages/shared` 公共请求层 + `apps/customer|merchant|rider`）
- 部署：三端构建产物由 Django 同源托管（`/` 顾客端、`/merchant/`、`/rider/`）；旧版静态页已移除
- 安全：`SECRET_KEY`/`DEBUG`/`ALLOWED_HOSTS` 支持环境变量注入（`DJANGO_SECRET_KEY`/`DJANGO_DEBUG=0`/`DJANGO_ALLOWED_HOSTS`），生产模式未配密钥拒绝启动

## 演示链路
顾客点菜下单 → 模拟支付 → 商户接单 → 骑手抢单配送 → 顾客评价 → 退款申请/商户审核（模拟到账）→（AI 客服对话式下单）

## AI 个性化点餐

| 能力 | 入口 | 说明 |
| --- | --- | --- |
| 对话下单 | 首页 AI 悬浮按钮（半屏对话面板） | 多轮对话 + 工具调用，生成待确认草稿再转正式订单 |
| 历史推荐 | 首页「猜你想吃」 | 按历史订单画像推荐，每条带理由（「你点过 4 次」「来自你常点的店」） |
| 一键复购 | 首页「再点一单」 | 用最近订单重建草稿，自动跳过下架/缺货菜品 |
| 确认即支付 | AI 草稿卡片 | 确认后直接完成支付并跳订单详情，不经过购物车与结算页 |
| 断网兜底 | 自动 | LLM 密钥失效/断网时降级为内置规则 Mock，推荐与下单链路仍可演示 |

接口：`GET /api/v1/ai/recommend`（画像 + 推荐）、`POST /api/v1/ai/reorder`（复购草稿）；
工具：`get_my_history`、`recommend_dishes`、`apply_refund`（另有 search_merchant / search_menu /
validate_draft / create_draft / get_order_status / urge_order / submit_review）。

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
| 工程规格（51 条可验收要求） | `openspec/specs/` |
