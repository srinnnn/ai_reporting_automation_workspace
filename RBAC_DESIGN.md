# RBAC_DESIGN

生成日期：2026-07-31

当前阶段：Step 6-P - RBAC Permission Design

执行边界：本阶段只生成设计文档，不修改 `app.py`、数据库、Repository 或 Task 流程。

## 1. 当前权限分析

### 1.1 当前登录机制

当前系统使用 `intranet_app/auth.py` 和 `intranet_app/storage.py` 实现基础登录。

当前能力：

- 用户密码通过 PBKDF2 哈希保存。
- 登录时使用 `verify_password()` 校验密码。
- 登录成功后通过 `new_session_token()` 生成随机 session token。
- session token 写入浏览器 Cookie：`intranet_session`。
- 后续请求通过 `_context(handler)` 读取 Cookie，并通过 `storage.get_session_user(token)` 找到当前用户。

当前 session 特征：

- session 存储在 SQLite `sessions` 表。
- session 表包含 `token`、`username`、`created_at`。
- 当前没有明确的 session 过期时间。
- 当前没有设备/IP/浏览器指纹绑定。
- 当前没有 CSRF token。
- 当前 API 暂时复用页面登录 session，不是独立 API Token。

### 1.2 当前用户模型

当前 `users` 表字段：

```text
id
username
display_name
role
password_salt
password_digest
created_at
```

当前 `UserRecord` 字段：

```text
id
username
display_name
role
password_hash
```

现状判断：

- 当前已有 `role` 字段，但只是用户记录上的文本字段。
- 目前没有独立的 `roles`、`permissions`、`role_bindings` 或 `resource_scopes` 表。
- 角色没有标准枚举和权限集合。
- 权限判断分散在 `app.py` 页面逻辑中。

### 1.3 当前 admin 能力

目前可确认的管理员判断主要是：

```text
user.role == "管理员"
```

当前管理员能力包括：

- 查看 AI 接口配置页面。
- 保存百炼 API Key。
- 测试 AI 连接。

当前非管理员限制：

- 非管理员不能配置 AI Key。
- 非管理员不能测试 AI 接口。

当前不足：

- 其他页面大多只要求“已登录”，没有进一步区分角色。
- `/tasks`、`/tasks/<task_id>`、`/api/tasks` 当前设计目标仍依赖已有登录态，尚未做品牌/部门隔离。
- 任务数据模型中已有 `created_by`、`brand_id`、`platform`、`channel`、`business_unit`、`owner` 等字段，但还没有统一权限规则使用这些字段。

## 2. 角色设计

目标角色至少包含：

```text
Admin
Business Owner
Operator
Viewer
```

建议采用英文稳定枚举作为系统内部角色编码，页面可显示中文名。

### 2.1 Admin

系统管理员。

权限范围：

- 查看全部任务。
- 提交全部任务。
- 下载全部任务结果。
- 查看全部品牌、平台、渠道、部门数据。
- 管理用户。
- 管理角色绑定。
- 管理品牌/部门资源范围。
- 管理 AI 配置。
- 查看系统审计日志。

限制：

- 仍不能绕过基础数据层生成正式 P1/P2 结果。
- 不能在页面/API 中看到 API Key 明文。
- 下载也必须通过 TaskResultService 或正式下载服务校验。

### 2.2 Business Owner

业务负责人。通常负责一个或多个品牌、业务线、渠道或部门。

权限范围：

- 查看自己负责范围内的任务。
- 提交自己负责范围内允许的任务。
- 下载自己负责范围内成功任务的结果文件。
- 查看自己负责范围内的报表和 AI 输出。
- 查看任务失败原因。
- 配置部分业务参数，例如品牌资料、业务资料模板、禁用词、投放场景等。

资源范围：

- `brand_scope`
- `department_scope`
- 可选：`platform_scope`
- 可选：`channel_scope`

限制：

- 不能管理其他业务方用户。
- 不能修改系统级 AI Key。
- 不能查看不在自己范围内的任务和下载文件。

### 2.3 Operator

运营执行人员。负责上传数据、触发日报/周报、查看自己提交的任务。

权限范围：

- 提交自己被授权品牌/部门下的任务。
- 查看自己创建的任务。
- 查看被 Business Owner 授权共享的任务。
- 下载自己有权限任务的结果。
- 上传数据或触发数据入库。

资源范围：

- 默认受 `created_by` 限制。
- 可叠加 `brand_scope` 和 `department_scope`。

限制：

- 不能查看同部门内其他人的任务，除非显式授权。
- 不能配置 AI Key。
- 不能改用户权限。
- 不能越权下载文件。

### 2.4 Viewer

只读查看者。适合管理层、协同方、复盘人员。

权限范围：

- 查看授权范围内的任务状态。
- 查看授权范围内的结果摘要。
- 可选下载权限：默认关闭，按资源范围或任务级授权打开。

资源范围：

- `brand_scope`
- `department_scope`
- 可选：只允许看汇总，不允许看明细。

限制：

- 不能提交任务。
- 不能修改任务。
- 不能上传数据。
- 不能修改配置。

## 3. Task 权限模型

### 3.1 任务资源字段

任务权限判断建议基于以下字段：

```text
task_id
task_type
created_by
owner
business_unit
brand_id
brand_name
platform
channel
date_window
status
```

其中关键权限字段：

- `created_by`
- `owner`
- `brand_id`
- `business_unit`
- `platform`
- `channel`

### 3.2 查看规则

任务查看应满足以下任一条件：

```text
Admin
OR task.created_by == current_user.username
OR task.owner == current_user.username
OR current_user has brand_scope matching task.brand_id
OR current_user has department_scope matching task.business_unit
OR current_user has explicit task permission
```

建议封装为：

```text
PermissionService.can_view_task(user, task)
```

### 3.3 下载规则

任务下载应比查看更严格。

允许下载需同时满足：

```text
can_view_task(user, task) == true
AND task.status == "success"
AND task has result_asset
AND TaskResultService validates asset exists
AND path is inside allowed result root
AND user has "task.download" permission
```

禁止：

- 只靠前端隐藏按钮控制下载。
- API 直接拼接 `file_path` 下载。
- 使用 payload 中的原始路径下载。
- 下载失败任务或不存在文件。

### 3.4 提交规则

提交任务需同时满足：

```text
user has "task.submit" permission
AND task_type is allowed for user role
AND payload brand_id is within user brand_scope
AND payload business_unit is within user department_scope
AND payload platform/channel is within optional platform/channel scope
```

建议任务提交时写入权限上下文：

```text
created_by = current_user.username
submitted_role = current_user.active_role
scope_snapshot = matched brand/department/platform/channel scopes
```

注意：

`created_by` 不应完全信任客户端传入。未来 API 应以 session/API token 中的用户为准，客户端传入的 `created_by` 只能作为兼容字段或被忽略。

### 3.5 created_by、brand_scope、department_scope 的关系

推荐规则：

- `created_by`：个人可见边界，保证用户至少能看自己的任务。
- `brand_scope`：品牌维度授权，例如 `anta_kids`、`bosch`。
- `department_scope`：组织维度授权，例如 `anta_retail_team`、`crm_team`。

权限合并方式：

```text
effective_scope = own_tasks OR brand_scope OR department_scope OR explicit_resource_permission
```

当多个 scope 冲突时：

- Deny 优先于 Allow。
- 更具体的资源规则优先于泛资源规则。
- 下载权限独立于查看权限。

## 4. API 权限设计

### 4.1 POST /api/tasks

用途：提交任务。

当前输入：

```json
{
  "task_type": "REPORT_GENERATE",
  "payload": {},
  "created_by": "admin"
}
```

未来权限规则：

```text
1. 必须已登录或携带有效 API Token。
2. current_user must have task.submit.
3. task_type must be allowed by role.
4. payload.brand_id must be within brand_scope.
5. payload.business_unit must be within department_scope.
6. payload.platform/channel must be within optional scope.
7. created_by must be current_user.username, not trusted from client.
```

角色建议：

| 角色 | POST /api/tasks |
|---|---|
| Admin | 全部 task_type |
| Business Owner | 授权范围内 task_type |
| Operator | 授权范围内提交 |
| Viewer | 禁止 |

建议权限点：

```text
task.submit
task.submit.report_generate
task.submit.data_import
task.submit.ai_content_generate
```

返回策略：

- 成功：返回 `task_id`、`status`。
- 无权限：403。
- 未登录：401。
- payload 越权：403。
- payload 格式错误：400。

### 4.2 GET /api/tasks/<task_id>

用途：查询任务安全结果信息。

未来权限规则：

```text
1. 必须已登录或携带有效 API Token。
2. TaskQueryService 获取任务 read model。
3. PermissionService.can_view_task(current_user, task) must be true.
4. TaskResultService.get_result(task_id) 返回安全结果信息。
5. 不返回真实服务器路径。
```

角色建议：

| 角色 | GET /api/tasks/<task_id> |
|---|---|
| Admin | 全部 |
| Business Owner | 负责范围 |
| Operator | 自己创建或授权范围 |
| Viewer | 授权范围只读 |

禁止返回：

- `runtime/...` 真实路径。
- 绝对路径。
- API Key。
- 原始文件敏感内容。
- 未授权品牌/部门的结果。

### 4.3 GET /api/tasks/<task_id>/download

用途：下载任务结果文件。

未来权限规则：

```text
1. 必须已登录或携带有效 API Token。
2. TaskQueryService 获取任务。
3. PermissionService.can_download_task(current_user, task) must be true.
4. TaskResultService.get_download_info(task_id) 校验文件存在和路径安全。
5. 后端流式返回文件。
```

角色建议：

| 角色 | download |
|---|---|
| Admin | 全部 |
| Business Owner | 负责范围 |
| Operator | 自己创建或授权范围 |
| Viewer | 默认禁止，按需授权 |

下载必须失败的情况：

- 任务不存在。
- 任务失败或未完成。
- 任务无结果资产。
- 文件不存在。
- 文件路径不在允许结果目录下。
- 当前用户无下载权限。

## 5. 页面权限设计

### 5.1 /tasks

用途：任务列表页。

未来数据规则：

```text
TaskQueryService.list_tasks()
-> PermissionService.filter_visible_tasks(current_user, tasks)
-> render page
```

不同角色看到的范围：

| 角色 | 可见任务 |
|---|---|
| Admin | 全部 |
| Business Owner | 负责品牌/部门 |
| Operator | 自己创建 + 授权范围 |
| Viewer | 授权只读范围 |

页面展示建议：

- 不展示不可见任务的数量。
- 不在前端隐藏后端仍可访问的 task_id。
- 下载按钮只在 `can_download_task == true` 且任务成功时出现。
- 失败原因按权限显示，避免跨业务暴露敏感字段。

### 5.2 /tasks/<task_id>

用途：任务详情页。

未来访问规则：

```text
1. 获取 task_id。
2. TaskQueryService.get_task(task_id)。
3. PermissionService.can_view_task(current_user, task)。
4. TaskResultService.get_result(task_id) only when task result is allowed.
5. Render detail.
```

无权限处理：

- 未登录：跳登录或 API 返回 401。
- 已登录但无权限：403。
- 任务不存在：404。
- 任务存在但结果不可下载：展示状态，不展示下载按钮。

下载按钮规则：

```text
show_download_button = can_download_task(user, task) AND task.status == "success" AND result_asset exists
```

## 6. 数据库演进建议

本阶段不修改现有 schema。以下是未来 PostgreSQL/SQLite schema 演进建议。

### 6.1 users

建议字段：

```text
id
username
display_name
email
status
password_hash
password_salt
last_login_at
created_at
updated_at
```

说明：

- 保留现有 `users` 兼容。
- `role` 字段未来不再作为唯一权限来源。
- 用户状态建议支持：`active`、`disabled`、`locked`。

### 6.2 roles

建议字段：

```text
id
code
name
description
is_system
created_at
updated_at
```

推荐初始角色：

```text
admin
business_owner
operator
viewer
```

### 6.3 permissions

建议字段：

```text
id
code
name
description
resource_type
action
created_at
updated_at
```

推荐权限点：

```text
task.submit
task.view
task.download
task.cancel
task.retry
task.admin
data.import
data.view
report.generate
report.view
report.download
ai.generate
ai.config.manage
user.manage
role.manage
```

### 6.4 role_permissions

建议字段：

```text
role_id
permission_id
created_at
```

用途：

- 定义角色拥有哪些基础权限。

### 6.5 role_bindings

建议字段：

```text
id
user_id
role_id
scope_id
created_by
created_at
expires_at
status
```

用途：

- 把用户绑定到角色。
- 支持一个用户多个角色。
- 支持角色绑定在某个资源范围下生效。

### 6.6 resource_scopes

建议字段：

```text
id
scope_type
scope_value
parent_scope_id
description
created_at
updated_at
```

推荐 scope 类型：

```text
global
department
brand
platform
channel
project
task
```

示例：

```text
department: anta_retail_team
brand: anta_kids
platform: meituan
channel: instant_retail
task: 123
```

### 6.7 resource_scope_bindings

建议字段：

```text
id
user_id
scope_id
permission_id
effect
created_by
created_at
expires_at
```

`effect`：

```text
allow
deny
```

用途：

- 支持用户级临时授权。
- 支持显式拒绝。
- 支持跨部门临时协作。

### 6.8 task permission snapshot

建议在未来任务表或任务元数据中保留：

```text
created_by
owner
brand_id
business_unit
platform
channel
scope_snapshot_json
```

目的：

- 任务创建后，即使用户权限后来变化，也可以审计当时为什么允许创建。
- 下载时仍按最新权限判断，但审计保留历史上下文。

## 7. PermissionService 设计建议

建议新增：

```text
backend/services/permission_service.py
```

核心方法：

```text
can_submit_task(user, task_type, payload) -> bool
can_view_task(user, task) -> bool
can_download_task(user, task) -> bool
filter_visible_tasks(user, tasks) -> list
assert_permission(user, permission, resource) -> None
```

输入来源：

- `UserRepository`
- `RoleRepository`
- `PermissionRepository`
- `ResourceScopeRepository`
- `TaskQueryService`

返回策略：

- Service 层返回 bool。
- API/Controller 层决定返回 401、403、404。

## 8. 渐进实施顺序

建议分阶段实施，避免一次性改动任务系统。

### Step A：只读权限服务

- 新增 PermissionService。
- 使用当前 `UserRecord.role` + task 字段做最小判断。
- 不改数据库。
- `/tasks` 和 `/api/tasks/<id>` 先接入过滤。

### Step B：任务查看/下载权限接入

- `GET /api/tasks/<id>` 接入 `can_view_task`。
- `GET /api/tasks/<id>/download` 接入 `can_download_task`。
- `/tasks` 页面接入 `filter_visible_tasks`。

### Step C：任务提交权限接入

- `POST /api/tasks` 不再信任客户端 `created_by`。
- 使用 session user 作为提交人。
- 校验 payload 的 `brand_id`、`business_unit`、`platform`、`channel`。

### Step D：数据库表演进

- 增加 `roles`、`permissions`、`role_bindings`、`resource_scopes`。
- 不直接删除 users.role。
- users.role 作为兼容字段保留一个版本。

### Step E：后台管理页

- 新增用户管理。
- 新增角色管理。
- 新增品牌/部门授权管理。
- 新增任务权限审计。

## 9. 验收标准

RBAC 正式接入前必须满足：

- 普通用户不能看到非本人且非授权范围任务。
- 业务负责人只能看到授权品牌/部门任务。
- Viewer 默认不能提交任务。
- 下载权限独立于查看权限。
- 所有 Task API 都有 401/403/404 明确返回。
- 不通过前端隐藏按钮作为唯一权限控制。
- 不暴露真实服务器文件路径。
- 不绕过 TaskResultService 下载文件。
- Admin 权限仍可审计，不能看到 API Key 明文。

## 10. 当前阶段结论

当前系统已经具备 RBAC 的基础字段：

- `users.role`
- `AutomationTaskRecord.owner`
- `AutomationTaskRecord.brand_id`
- `AutomationTaskRecord.business_unit`
- `AutomationTaskRecord.platform`
- `AutomationTaskRecord.channel`
- `TaskReadModel.created_by`

但当前还不是完整 RBAC。下一步应先做 `PermissionService` 的最小实现，用现有字段完成任务查看和下载过滤，再逐步演进数据库表结构。
