# Proposal

## Why

`thesis-docs/02-需求分析.md` 已完成第 3 稿：范围按最小可行收敛（取消"可选"档、商户注册与入驻合并为一步、骑手接单即进入配送中、配送费为平台固定值），并把未进入三条主线的功能统一移入"本期不包含"。仓库里的 OpenSpec 规格仍停留在第 2 稿口径，`openspec/specs/` 尚无任何 main spec。

本 change 建立规格链路的起点：把第 3 稿中**代码已经满足**的行为固化成 6 个 capability 的基线规格，让后续每条落差都有一个干净的比较基准，答辩与验收时每条需求都能指向对应的实现与验收场景。

## What Changes

- 新增 6 个 capability 的基线规格（`openspec/specs/<capability>/spec.md`），只覆盖第 3 稿中代码已达标的行为。
- 建立口径映射：每条规格需求标注其来源编号（`F-A-xx` / `F-B-xx` / `F-C-xx` / `F-D-xx` / `F-E-xx`、`UC-xx`、`R1–R8`），使 02 与 specs 可以双向对照。
- **不改动任何代码**（`takeout/`、`web/` 均在范围外），**不改动 `thesis-docs/`**（02 是需求权威源，specs 是它的投影，不进入论文交付物）。

**明确不写入基线的落差**（共 11 条）：第 3 稿要求、但当前代码未达标的部分。每条留给后续独立 change。

| 落差 | 涉及需求编号 | 归属 |
| --- | --- | --- |
| AI 相关接口无认证装饰器；会话未绑定当前登录顾客，审计日志的 `actor_id` 因取 `session.cs_user_id` 而恒为空 | F-E-01、R8、4.2 | 后续 change：AI 助手的身份绑定 |
| `GET /orders/<pk>` 与 `POST /orders/<pk>/pay` 有登录校验但缺归属过滤 | F-A-06、F-A-07、R4、4.2 | 后续 change：顾客订单作用域 |
| 未选择收货地址时后端仍可建单（`address_snapshot` 写空串） | UC-01 异常流 3a、F-A-05 | 后续 change：下单前置校验 |
| 商户注册与入驻申请（F-B-01）、查看入驻审核状态（F-B-03）均无接口；未过审商户被直接拒绝登录（`merchant/api_views.py` 的 `login` 校验 `status == 20`），与 UC-03「商户可登录并查看审核状态」相冲突 | F-B-01、F-B-03、R3、UC-03 | 后续 change：入驻申请链路（含审核期间的可登录状态页） |
| 骑手接单只记录归属、未把订单推进为「配送中」 | F-C-03、UC-08 | 后续 change：接单状态口径 |
| 商户端订单状态更新不校验迁移合法性；商户可取消任意状态的订单 | R2、F-B-06、UC-07 | 后续 change：状态迁移校验 |
| 订单不单独持久化配送费；配送费由请求携带而非平台固定值 | F-A-05、UC-01 后置条件、2.3 | 后续 change：配送费落库 |
| 商户列表评分为硬编码值而非评价均值；商户列表的销量与距离、骑手端的评分与收入均为硬编码展示值 | F-A-02、F-C-06、第七章展示口径 | 后续 change：展示字段真值化 |
| 运营侧操作不写审计日志，仅 AI 工具调用写 | F-D-08、UC-04 后置条件 | 后续 change：运营操作审计 |
| 顾客端页面标题仍为「AI 客服」（`web/apps/customer/src/router/index.ts` 的路由标题与 `AiChat.vue` 的导航栏标题），与口径不一致 | —（命名一致性） | 后续 change：前端文案统一 |
| 遗留物：`shopping_cart`、`refund_record`、`product_spec`、`product_sku`、`system_config` 五张表，`OrderItem.spec_text` 字段，以及 AI 工具集中的 `get_item_specs` | 02 第 2.3、第七章 | 后续 change：遗留物清理 |

> **消化记录**：
> ① 落差 1–3（AI 接口认证与会话绑定、订单详情与支付的归属过滤、下单收货地址前置校验）由 change `enforce-server-side-scope` 消化，2026-10-11 归档。
> ② 落差 5–11（骑手接单状态口径、商户端状态迁移校验、配送费落库、假展示字段真值化、运营操作审计、AI 页面文案统一、遗留物清理）由 2026-10-11 的直接实现消化，规格侧由 change `sync-specs-to-implementation` 补齐并归档。
> ③ 落差 4（商户入驻链路：注册与入驻申请、查看审核状态、未过审的经营门槛）由 change `add-merchant-onboarding` 消化，2026-10-11 归档。
> 三份记录分别位于 `openspec/changes/archive/` 下对应的归档目录。
> **落差表已归零：11 条落差全部消化。**

**不进基线也不进落差表的部分**：第 3 稿已把退款、菜品规格与 SKU、真实支付、推送、优惠券与积分、复杂配送调度、骑手评分与收入结算、拒单退单、收藏、站内通知阅读界面、系统参数配置、营业时间与打烊拦截、商户列表销量与距离等项移入"本期不包含"。它们不属于落差，落差表只登记"本期要求但未达标"的项。

## Capabilities

### New Capabilities

- `customer-ordering`: 顾客端基础交易——手机号验证码登录、浏览商户与菜品、购物车、下单与模拟支付、订单列表与详情查询、取消订单、收货地址管理、订单评价。
- `order-lifecycle`: 订单状态集合（待支付 / 已支付 / 待接单 / 配送中 / 已完成 / 已取消）、状态迁移与状态变更日志。
- `merchant-console`: 商户端——账号密码登录、菜品分类管理、菜品管理（含上下架与可售数量调整）、订单查看与状态推进、营业信息维护、营业统计。
- `rider-delivery`: 骑手端——账号密码登录、待接单列表、承接订单、推进配送与确认送达、本人任务与工作量查询。
- `platform-ops`: 平台运营——运营账号登录、商户入驻审核、商户/用户/订单查询、骑手账号维护、平台数据统计、操作日志查看。
- `ai-ordering-assistant`: 顾客端内置的 AI 点餐助手——会话与多轮对话、槽位收集、草稿生成、后端重校验、顾客确认转正式订单、订单状态查询、催单、辅助评价、关键操作审计。

### Modified Capabilities

<!-- 当前 openspec/specs 为空，无既有 capability 的需求被修改。 -->

（无）

## Impact

- **新增文件**：`openspec/specs/customer-ordering/spec.md`、`openspec/specs/order-lifecycle/spec.md`、`openspec/specs/merchant-console/spec.md`、`openspec/specs/rider-delivery/spec.md`、`openspec/specs/platform-ops/spec.md`、`openspec/specs/ai-ordering-assistant/spec.md`。
- **代码**：无改动。`takeout/`（Django 后端）与 `web/`（三端 SPA）仅作为核实现状的读取对象。
- **文档**：`thesis-docs/02-需求分析.md` 保持权威地位，本 change 不修改它；后续需求变更先改 02，再同步 specs。
- **接口**：本 change 不引入接口变更，规格中的接口口径取自现状（如 `common/auth.py` 的四套 token 盐值、`common/response.py` 的 ResultAPI 格式）。
- **风险**：基线只覆盖已达标行为，因此基线会明显比 02 窄（12 条落差 + 全部"本期不包含"项）。这是刻意的选择：让 `openspec validate` 通过、并让后续落差各自有独立而干净的增量。
