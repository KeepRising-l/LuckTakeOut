# Tasks

## 1. 后端：注册与登录

- [x] 1.1 在 `takeout/merchant/models.py` 的 `MerchantInfo` 上补 `STATUS_PENDING`/`STATUS_APPROVED`/`STATUS_REJECTED` 常量，`status` 默认值改用常量；验证：`python manage.py makemigrations --check --dry-run` 显示无变更（取值未变，不应产生迁移）
- [x] 1.2 在 `takeout/merchant/api_views.py` 新增 `register`：校验必填项（账号、密码、店铺名称、联系电话、店铺地址）、密码长度、账号是否被占用，创建登录账号与状态为「待审核」的商户记录并签发令牌；验证：`test_register_creates_pending_merchant`、`test_register_rejects_taken_username`、`test_register_rejects_missing_required_fields`、`test_register_rejects_short_password`
- [x] 1.3 修改 `login`：删除"未过审即拒绝登录"的判断，返回值增加审核状态；验证：`test_pending_merchant_can_login_and_view_status`
- [x] 1.4 在 `takeout/config/urls.py` 增加 `merchant/register` 路由；验证：注册接口可被测试客户端访问到（返回 JSON 而非 404 页面）

## 2. 后端：经营门槛（R3）

- [x] 2.1 在 `takeout/common/auth.py` 新增 `merchant_approved_required`：未登录 401、未过审 403 并带当前状态、过审后注入 `request.merchant`；在文档串中写明"新增经营接口必须挂本装饰器"；验证：`test_pending_merchant_is_blocked_from_business_endpoints` 与 `test_approved_merchant_passes_the_gate`
- [x] 2.2 把 `takeout/product/api_views.py` 与 `takeout/order/api_views.py` 中的 22 处经营接口装饰器替换为 `merchant_approved_required`；验证：`grep -c merchant_approved_required` 在两个文件中各为 12（1 处导入 + 11 处使用），且 `test_pending_merchant_is_blocked_from_business_endpoints` 覆盖的五类接口全部返回 403
- [x] 2.3 把 `takeout/merchant/api_views.py` 的 `update_info`、`update_status`、`upload_avatar` 改挂 `merchant_approved_required`，`login` 与 `current` 保持 `merchant_login_required`；验证：上述测试用例中的 `PUT /api/merchant/info` 返回 403，而 `GET /api/merchant/current` 正常返回

## 3. 前端：入驻申请与审核状态

- [x] 3.1 在 `web/apps/merchant/src/api/index.ts` 增加 `register` 接口与 `status` 字段（`LoginResult`、`MerchantCurrent`）；在 `stores/auth.ts` 增加 `status` 字段、`setStatus` 动作与 `STATUS_APPROVED` 常量；验证：`npm run build -w @takeout/merchant` 通过
- [x] 3.2 新增 `web/apps/merchant/src/views/Register.vue`：账号、密码、确认密码、店铺名称、联系电话、店铺地址、店铺简介（选填）的表单，提交成功后按状态跳转；验证：构建通过，表单必填校验与两次密码一致校验生效
- [x] 3.3 新增 `web/apps/merchant/src/views/ReviewStatus.vue`：展示待审核/已通过/已驳回三种状态与已提交的入驻资料，支持刷新状态与退出登录；已被平台置为已通过时自动进入商户中心；验证：构建通过
- [x] 3.4 修改 `web/apps/merchant/src/router/index.ts`：增加 `/register` 与 `/review` 路由；守卫按审核状态分流——未登录去登录页，已登录未过审只能停留在审核状态页，过审后不可再停留在该页；验证：构建通过
- [x] 3.5 修改 `web/apps/merchant/src/views/Login.vue`：登录后按状态跳转（过审进 `/`，未过审进 `/review`），并加入入驻申请入口；验证：构建通过

## 4. 测试与验收

- [x] 4.1 在 `takeout/merchant/tests.py` 增加 `MerchantOnboardingTest`，覆盖注册成功、账号占用、必填缺失、密码过短、未过审可登录看状态、未过审被经营接口拒绝、过审后放行
- [x] 4.2 运行 `python manage.py test` 全部通过
- [x] 4.3 运行 `python manage.py check` 与 `python manage.py makemigrations --check --dry-run`，无错误、无待生成迁移
- [x] 4.4 运行 `npm run build`（三端一次构建）通过
- [x] 4.5 核对实现与 `thesis-docs/02-需求分析.md` 的 F-B-01、F-B-03、UC-03、R3 一致；若发现出入，先改文档再改代码

## Workflow follow-up

- 归档本 change（`openspec archive add-merchant-onboarding -y --json`），把增量合并进 `openspec/specs/merchant-console/`。
- 归档后在已归档基线 change 的 `proposal.md` 落差表中补充记录：最后一条落差（商户入驻链路）已消化，落差表归零。
- 同步 `openspec/specs/merchant-console/spec.md` 的 Purpose：移除"F-B-01 与 F-B-03 当前尚无接口，未纳入基线"这句已失效的说明。
