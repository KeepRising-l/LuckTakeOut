# Tasks

> 本 change 不含代码改动：对应的实现在此之前已完成并验证。任务的实际内容是**核对规格描述与已落地的行为一致**，核对通过的写入增量，对不上的回头修正实现。

## 1. 顾客端规格核对

- [x] 1.1 核对「浏览已通过审核的商户」：`takeout/merchant/views.py` 的 `merchant_to_dict` 以 `Avg('reviews__rating')` 计算评分、无评价返回空值、配送费取 `settings.DELIVERY_FEE`，且响应不含 `monthlySales`、`sales`、`tags`、`distance`、`deliveryTime`；由 `merchant/tests.py` 的列表与详情用例覆盖
- [x] 1.2 核对「提交订单」的配送费口径：`takeout/order/views.py` 的 `create_order` 取平台常量、`delivery_fee` 单独落库、请求携带的 `deliveryFee` 被忽略；由 `order/tests.py` 的 `test_platform_delivery_fee_is_persisted` 与 `test_client_supplied_delivery_fee_is_ignored` 覆盖

## 2. 订单生命周期规格核对

- [x] 2.1 核对「配送阶段的状态推进」：`takeout/delivery/api_views.py` 的 `accept_task` 在记录骑手的同时把状态推进为配送中，`update_task_status` 只接受送达；由 `delivery/tests.py` 的 `test_accept_moves_order_to_delivering` 与 `test_intermediate_status_is_rejected` 覆盖
- [x] 2.2 核对新增的「状态迁移合法性」：`takeout/order/state.py` 的 `ALLOWED_TRANSITIONS` 与 `change_status` 是唯一变更入口，顾客支付与取消、商户更新与取消、骑手接单与送达全部改走它；由 `order/tests.py` 的 `MerchantStatusTransitionTest` 四个用例覆盖

## 3. 商户端规格核对

- [x] 3.1 核对「商户推进订单处理状态」：目标状态集合为 `MERCHANT_TARGET_STATUSES`，非法迁移返回"当前订单状态不允许该操作"且状态不变，配送中的订单不可取消；由 `MerchantStatusTransitionTest` 覆盖
- [x] 3.2 核对商户端订单状态以整数取值返回：`takeout/order/api_views.py` 的 `order_to_dict` 直接返回 `o.status`，`STATUS_TO_M` 已删除

## 4. 骑手端规格核对

- [x] 4.1 核对「承接订单」的接单即进入配送中，以及重复接单时归属与状态保持不变
- [x] 4.2 核对「推进配送与确认送达」：`rider_to_dict` 不含评分、收入与位置，`task_to_dict` 不含距离与预计时长；由 `delivery/tests.py` 的 `test_rider_info_has_no_fabricated_fields` 覆盖

## 5. 运营端规格核对

- [x] 5.1 核对「商户入驻审核」写审计：`takeout/platform_ops/api_views.py` 的 `merchant_audit` 写入 `OperationLog`，记录操作者标识、角色 platform 与审核前后的状态；未知审核动作被拒绝时不写日志
- [x] 5.2 核对「操作日志查看」：AI 工具调用的审计记录带所属顾客标识（`ai_service/tools.py` 的 `_audit`），运营审核记录带运营人员标识与角色 platform；由 `ai_service/tests.py` 的 `test_audit_records_customer_as_actor` 覆盖

## 6. 验收

- [x] 6.1 运行 `python manage.py test` 全部通过（29 项）
- [x] 6.2 运行 `python manage.py check` 与 `python manage.py makemigrations --check --dry-run`，无错误、无待生成迁移
- [x] 6.3 运行 `openspec validate sync-specs-to-implementation` 通过；归档后运行 `openspec validate --specs`，6 个 capability 全部通过

## Workflow follow-up

- 归档本 change（`openspec archive sync-specs-to-implementation -y --json`），把 5 份增量合并进 `openspec/specs/`。
- 归档后在已归档基线 change 的 `proposal.md` 落差表中补充消化记录：本 change 覆盖落差 5–11（骑手接单状态口径、商户端状态迁移校验、配送费落库、假展示字段真值化、运营操作审计、AI 页面文案统一、遗留物清理），落差表仅剩落差 4「商户入驻链路」1 条。
