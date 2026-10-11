# Tasks

## 1. AI 助手接口认证

- [x] 1.1 在 `takeout/ai_service/views.py` 的 `create_session`、`chat`、`draft_detail`、`draft_confirm` 上挂 `@api_login_required`（从 `common.auth` 导入）；验证：不带令牌请求这四个接口均返回 401 与"未登录或登录已过期"提示

## 2. AI 助手作用域限定为当前登录顾客

- [x] 2.1 在 `takeout/ai_service/views.py` 中把顾客身份改为从 `request.user` 反查 `UserInfo`，删除 `_default_customer()` 与对请求体 `customerId` 的读取；验证：请求体携带其它顾客的 `customerId` 时，新会话的归属仍是当前登录顾客
- [x] 2.2 在 `chat`、`draft_detail`、`draft_confirm` 中按对象归属过滤（会话按 `customer`、草稿按 `customer`），不匹配时按"不存在"返回；验证：以顾客 A 的令牌访问顾客 B 的会话与草稿，返回"会话不存在"与"草稿不存在"

## 3. 审计与催单记录的操作者

- [x] 3.1 在 `takeout/ai_service/tools.py` 中把 `_audit` 与 `t_urge_order` 的操作者由 `session.cs_user_id` 改为 `session.customer_id`，`actor_role` 保持 `ai`；验证：触发一次工具调用后，`operation_log.actor_id` 等于该顾客的标识而非空

## 4. 移除 ChatSession.cs_user

- [x] 4.1 从 `takeout/ai_service/models.py` 的 `ChatSession` 移除 `cs_user` 字段，从 `takeout/ai_service/admin.py` 的 `ChatSessionAdmin.list_display` 移除该列，并生成迁移；验证：`python manage.py makemigrations --check --dry-run` 无待生成变更，`python manage.py check` 通过

## 5. 订单接口的归属过滤与前置校验

- [x] 5.1 在 `takeout/order/views.py` 的 `order_detail` 中把查询条件补上 `user=user_info`；验证：以顾客 A 的令牌请求顾客 B 的订单，返回"订单不存在"
- [x] 5.2 在 `takeout/order/views.py` 的 `order_pay` 中把查询条件补上 `user=user_info`；验证：以顾客 A 的令牌支付顾客 B 的订单，返回"订单不存在"且该订单状态保持不变
- [x] 5.3 在 `takeout/order/views.py` 的 `create_order` 中，未指定收货地址或地址不属于本人时拒绝建单，返回"请选择收货地址"；验证：不带 `addressId` 提交订单被拒，且不产生订单记录

## 6. 顾客端 AI 请求接入统一请求实例

- [x] 6.1 在 `web/apps/customer/src/api/index.ts` 中移除裸 axios 的 `aiHttp` 实例，让 `aiApi` 使用带令牌的请求实例（复用 `http` 或等价的 `createRequest` 配置）；验证：`npm run build -w @takeout/customer` 通过，且未登录访问 AI 页面时会跳转登录页

## 7. 作用域与前置校验的测试

- [x] 7.1 在 `takeout/ai_service/tests.py` 中补测试：AI 四个接口未登录被拒、跨顾客访问会话与草稿被拒、审计记录的操作者非空
- [x] 7.2 在 `takeout/order/tests.py` 中补测试：订单详情与支付的归属过滤、未选收货地址被拒、归属校验通过时行为不变
- [x] 7.3 运行 `python manage.py test ai_service order` 并全部通过

## 8. 验收

- [x] 8.1 运行 `python manage.py check` 与 `python manage.py makemigrations --check --dry-run`，均无错误、无待生成迁移
- [x] 8.2 运行 `python manage.py test` 全绿
- [x] 8.3 核对实现与 `thesis-docs/02-需求分析.md` 第 4.2 节、UC-01 异常流 3a、F-E-01 及 `03-系统设计.md` 的 `chat_session` 表定义一致；若发现出入，先改文档再改代码

## Workflow follow-up

- 归档本 change（`openspec archive enforce-server-side-scope -y --json`）。
- 归档后在已归档基线 change 的 `proposal.md` 落差表中，把落差 1、2、3 标注为已消化。
