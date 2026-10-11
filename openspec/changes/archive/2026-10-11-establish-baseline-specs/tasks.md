# Tasks

> 本 change 不含代码改动。任务的实际内容是**核对**：逐条确认基线规格在 `takeout/` 与 `web/` 中有对应实现，核对不通过的需求移出基线并登记到落差表。

## 1. 顾客端规格核对

- [x] 1.1 核对 `specs/customer-ordering/spec.md` 的登录、浏览、下单、支付、查询、取消、地址、评价需求在代码中有对应实现：在 `takeout/user/views.py`、`takeout/merchant/views.py`、`takeout/product/views.py`、`takeout/order/views.py`、`takeout/review/views.py` 中逐一找到对应分支；对不上的需求移出基线并登记到 `proposal.md` 落差表
- [x] 1.2 核对购物车需求的表述与实现一致：`web/apps/customer/src/stores/cart.ts` 以本地存储维护购物车，`takeout/cart/models.py` 的 `ShoppingCart` 未被任何接口引用；确认规格中没有出现"服务端持久化购物车"之类承诺
- [x] 1.3 核对"实付金额由商品金额与配送费组成"这一场景与 `takeout/order/views.py` 的 `create_order` 一致（配送费取自请求而非平台固定值，且未单独落库）；确认规格未声明配送费为平台固定值或已持久化

## 2. 订单生命周期规格核对

- [x] 2.1 核对 `specs/order-lifecycle/spec.md` 的六状态集合与 `takeout/order/models.py` 的 `STATUS_CHOICES` 一致；确认规格未声明退款状态，且模型中的 70/80 两个不可达状态已在 `proposal.md` 落差表登记
- [x] 2.2 核对"状态变化才写日志、日志可追溯"与 `takeout/order/views.py` 的 `order_pay` / `order_cancel`、`takeout/delivery/api_views.py` 的 `update_task_status`、`takeout/order/api_views.py` 的 `_change_status` 一致；确认规格未声明"非法迁移被拒绝"（商户端未做该校验，见落差表）
- [x] 2.3 核对"骑手接单时记录归属、状态仍为待接单"与 `takeout/delivery/api_views.py` 的 `accept_task` 一致；确认规格未把"接单即进入配送中"写入基线（该半句见落差表）

## 3. 商户端规格核对

- [x] 3.1 核对 `specs/merchant-console/spec.md` 的登录、分类、菜品、订单查看与状态推进、营业信息需求与 `takeout/merchant/api_views.py`、`takeout/product/api_views.py`、`takeout/order/api_views.py` 中的 `@merchant_login_required` 与 `merchant=request.merchant` 过滤一致
- [x] 3.2 核对 Purpose 下的说明与 `proposal.md` 落差表一致：F-B-01（商户注册与入驻申请）与 F-B-03（查看审核状态）确实无接口，`takeout/merchant/api_views.py` 只有 `login`、`current`、`update_info`、`update_status`、`upload_avatar`
- [x] 3.3 核对营业统计需求与 `takeout/order/api_views.py` 的 `stats_overview`、`stats_recent_orders`、`stats_order_status`、`stats_sales`、`stats_revenue_trend`、`stats_top_products` 一致；确认规格中没有写入商户端状态字符串映射（`STATUS_TO_M` / `TARGET_STATUS`），该口径属设计范畴

## 4. 骑手端规格核对

- [x] 4.1 核对 `specs/rider-delivery/spec.md` 的登录、待接单列表、承接订单、推进配送与确认送达、本人任务需求与 `takeout/delivery/api_views.py` 的 `login`、`pending_tasks`、`accept_task`、`update_task_status`、`rider_tasks` 一致
- [x] 4.2 核对个人工作量需求只声明"今日完成单数与累计完成单数"，与 `takeout/delivery/api_views.py` 的 `statistics` 一致；确认规格未声明 `rider_to_dict` 中硬编码的 `rating` 与 `todayEarnings`，也未声明"查看本人资料"里的评分与位置字段

## 5. 运营端规格核对

- [x] 5.1 核对 `specs/platform-ops/spec.md` 的登录（运营标识）、审核、查询、统计需求与 `takeout/platform_ops/api_views.py` 的 `login`、`merchant_audit`、`merchants`、`users`、`orders`、`statistics` 一致
- [x] 5.2 核对"骑手账号创建与维护"与 `takeout/delivery/admin.py` 的 `RiderAdmin` 一致（`list_display` 含姓名、电话、状态，`list_filter` 支持按状态筛选）
- [x] 5.3 核对操作日志需求只声明"AI 工具调用写日志 + 日志可查看与筛选"，与 `takeout/ai_service/tools.py` 的 `_audit`、`takeout/platform_ops/admin.py` 的 `OperationLogAdmin` 一致；确认规格未声明审核等运营操作写日志（见落差表）

## 6. AI 点餐助手规格核对

- [x] 6.1 核对 `specs/ai-ordering-assistant/spec.md` 的会话与多轮对话、工具检索、草稿生成、订单状态查询、催单、评价、审计需求与 `takeout/ai_service/views.py`、`tools.py`、`agent.py`、`llm.py` 一致
- [x] 6.2 核对规格未声明"会话以当前登录顾客的身份创建""仅能操作本人数据"（规则 R8），也未声明工具集合中的 `get_item_specs`；确认这三项分别在 `proposal.md` 落差表中登记
- [x] 6.3 核对确认草稿时的二次校验与金额重算，与 `takeout/ai_service/views.py` 的 `draft_confirm` 一致（取 `product.price` 与 `product.stock`）

## 7. 落差登记与口径确认

- [x] 7.1 逐条复现 `proposal.md` 落差表的 11 条（复核后由 12 条并至 11 条），例如 `grep -rn "api_login_required" takeout/ai_service/views.py` 无输出、`takeout/order/views.py` 的 `order_detail` 与 `order_pay` 中无 `user=` 过滤条件；任一条无法复现则修正落差表
- [x] 7.2 复核落差表与第 3 稿的"本期不包含"分列清晰：退款、规格与 SKU、真实支付、推送、复杂调度、骑手评分与结算、拒单退单、收藏、站内通知界面、系统参数配置、营业时间与打烊拦截等项作为**需求**不出现在落差表中；仅两条涉及这些项在代码中的**遗留物**（硬编码展示值、遗留表与遗留工具），属清理事项而非需求

## 8. 验收

- [x] 8.1 运行 `openspec validate establish-baseline-specs` 并通过；缺少英文 SHALL/MUST 的提示按 `openspec/config.yaml` 中已记录的约定接受
- [x] 8.2 运行 `openspec status --change establish-baseline-specs`，确认 proposal、specs、design、tasks 四项均为 done
- [x] 8.3 核对各 spec 的 Purpose 引用与 `thesis-docs/02-需求分析.md` 第 3 稿的编号对应：确认引用只指向进入基线的编号，未进入基线的 F-B-01、F-B-03、F-C-03 中的状态推进半句、F-E-01 只出现在 `proposal.md` 落差表中

## Workflow follow-up

- 归档本 change（`/opsx:archive`），归档时 6 份 delta 规格合并为 `openspec/specs/` 下的 main specs。
- 归档后运行 `openspec view`，确认 specs 数为 6、本 change 归入已完成。
