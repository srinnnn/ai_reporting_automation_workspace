# REPORT_TASK_ROLLOUT_PLAN

## 1. 当前入口分析

目标入口：

- `POST /anta-reporting/meituan-daily/run`
- 当前处理函数：`intranet_app/app.py::_handle_anta_meituan_reporting_run(handler, user, "daily")`

当前路由分发：

```text
POST /anta-reporting/meituan-daily/run
-> _handle_anta_meituan_reporting_run(handler, context.user, "daily")
```

旧同步流程调用链：

```text
页面提交日报日期
-> _read_urlencoded(handler)
-> _selected_meituan_report_date(fields)
-> _sync_meituan_download_sources()
-> _ingest_meituan_plugin_files_to_foundation(user.username)
-> _load_anta_meituan_sources_from_foundation("daily", selected_report_date)
-> anta_meituan_reporting.build_meituan_daily_report(...)
-> write_csv(result_path, result.output_rows)
-> storage.save_job(...)
-> _result_page(user, job_id, result)
```

当前同步流程的特点：

- 一个 HTTP 请求内完成文件同步、基础层入库、基础层读取、日报生成、结果文件保存。
- 正式日报取数已经经过基础数据层，不应该直接从原始 CSV/Excel 生成。
- 报表结果通过 `write_csv` 写入 `runtime/results`，再通过 `storage.save_job` 记录下载任务。
- 失败时捕获 `ValidationError`、`ValueError`、`TypeError`、`FileNotFoundError`、`OSError`，返回原安踏报表页面并展示错误。

当前主要风险：

- 请求耗时随文件数量、基础层导入耗时、日报计算耗时增加。
- 用户关闭页面或请求超时后，任务状态不可追踪。
- 失败原因只服务于当前响应，不利于后续管理页面统一查看。
- 难以支持未来 20+ 用户同时提交报表任务。

## 2. 新 Task 流程接入点

目标接入链路：

```text
页面
-> Report Task Adapter
-> TaskSubmitter
-> TaskRequest
-> TaskRunner
-> ReportExecutor
-> ReportService
-> FoundationRepository
-> anta_meituan_reporting
-> TaskResult
-> TaskQueryService
```

建议第一阶段接入点：

```text
_handle_anta_meituan_reporting_run(..., "daily")
-> 读取表单日期
-> build_daily_report_task_payload(report_date, user)
-> TaskSubmitter.submit(TaskType.REPORT_GENERATE, payload, user.username)
-> 返回任务结果页或任务状态页
```

边界要求：

- Adapter 只做页面参数到 payload 的转换。
- TaskSubmitter 只负责任务提交、任务记录和调用 TaskRunner。
- TaskRunner 只按 `task_type` 选择 Executor。
- ReportExecutor 只调用 ReportService，不直接访问数据库或 processor。
- ReportService 只从基础数据层读取正式报表数据。
- 报表计算仍继续使用 `processors/anta_meituan_reporting.py`，不重写日报口径。

第一阶段不建议把“美团文件同步”和“基础层入库”强行塞入 ReportExecutor。更稳妥的路线是：

```text
短期：
页面仍可先触发现有同步和入库
-> REPORT_GENERATE 只负责任务化报表生成

中期：
文件同步和入库拆成 DATA_IMPORT 任务
-> DATA_IMPORT 成功后再触发 REPORT_GENERATE
```

最终目标：

```text
插件或上传目录产生文件
-> DATA_IMPORT
-> 基础数据层
-> REPORT_GENERATE
-> 结果保存
-> 页面通过 TaskQueryService 查询状态和下载结果
```

## 3. Feature Flag 设计

环境变量：

```text
REPORT_TASK_MODE
```

支持值：

- `legacy`
- `task`

默认值：

```text
legacy
```

读取规则：

```text
REPORT_TASK_MODE 未配置
-> legacy

REPORT_TASK_MODE=legacy
-> 继续使用旧同步流程

REPORT_TASK_MODE=task
-> 使用 TaskSubmitter 流程

REPORT_TASK_MODE 其他值
-> fail closed，记录 error log，并回退 legacy 或拒绝启动
```

建议第一阶段采用“请求级分支”，不要改变路由地址：

```text
POST /anta-reporting/meituan-daily/run
-> if REPORT_TASK_MODE == "task":
       task flow
   else:
       legacy flow
```

保留同一个入口的原因：

- 业务方页面操作不变。
- 灰度切换只依赖配置，不需要培训用户。
- 出现问题可以立即把环境变量切回 `legacy`。

灰度期间建议额外记录：

- `report_task_mode`
- `task_id`
- `created_by`
- `brand_id`
- `platform`
- `channel`
- `report_date`
- `source_policy`
- 旧流程输出 job_id
- 新流程输出 job_id 或 result_file

敏感信息限制：

- 不记录 API Key。
- 不记录账号密码、Cookie。
- 不把原始 CSV/Excel 全量内容写入任务 payload 或日志。
- 不允许 Task 模式绕过基础数据层直接读原始下载文件。

## 4. 灰度阶段

### 阶段1：开发验证

目标：

- 验证 Task 流程能在本地生成与旧流程一致的安踏美团日报。
- 默认仍为 `REPORT_TASK_MODE=legacy`。

执行方式：

```text
同一日期
-> legacy 生成日报
-> task 生成日报
-> 对比结果
```

验收标准：

- 同一日期下，日报核心字段一致。
- 输出行数一致。
- 销售额、订单量、商品 TOP、门店 TOP 等核心指标一致。
- TaskResult 能记录成功、失败、错误摘要。
- `source_policy` 固定为 `foundation_only`。

通过后再进入阶段2。

### 阶段2：内部用户

目标：

- 让组内少量内部用户使用 Task 模式。
- 验证页面体验、错误提示、重复提交和权限边界。

建议范围：

- 仅开放安踏儿童美团日报。
- 仅开放管理员和指定业务负责人。
- 日期范围先限制为已有基础层数据日期。

执行方式：

```text
REPORT_TASK_MODE=task
-> 内部用户每日生成日报
-> 管理者查看任务状态
-> 记录失败原因和结果一致性
```

验收标准：

- 连续 5 个工作日任务成功率稳定。
- 单日报生成不阻塞其他用户浏览。
- 失败任务可以看到明确原因。
- 重复点击不会产生混乱结果。
- 旧流程仍可通过切换环境变量恢复。

### 阶段3：正式切换

目标：

- 安踏儿童美团日报默认进入 Task 模式。
- 旧流程保留为回滚路径，不删除。

切换条件：

- 阶段2无严重数据口径差异。
- 管理页面可以看到任务状态。
- 失败原因可追踪。
- 下载结果路径和旧流程兼容。
- 运维人员知道如何切换 `REPORT_TASK_MODE`。

正式配置：

```text
REPORT_TASK_MODE=task
```

保留项：

- 旧同步流程代码保留至少一个完整月报周期。
- 旧结果文件下载方式保留。
- 旧 job 记录兼容保留。

## 5. 回滚方案

回滚原则：

- 不删除旧流程。
- 不迁移数据库 schema。
- 不改变旧入口 URL。
- Task 模式失败时，可以立即恢复 legacy。

立即回滚方式：

```text
REPORT_TASK_MODE=legacy
重启应用
```

回滚触发条件：

- Task 模式生成结果与 legacy 出现核心指标差异。
- 日报任务无法稳定保存结果文件。
- 任务状态无法查询。
- 多用户提交导致任务覆盖或结果错乱。
- 页面无法给业务方展示清晰失败原因。

回滚后处理：

- 保留失败 Task 记录用于排查。
- 使用 legacy 重新生成当天日报。
- 对比失败任务 payload、基础层数据、ReportService 输出。
- 修复后重新进入阶段1验证。

禁止事项：

- 不允许为了回滚删除 TaskService、TaskRunner、ReportExecutor。
- 不允许用原始 CSV/Excel 绕过基础数据层临时生成正式日报。
- 不允许把真实业务数据写入 GitHub 或日志。

## 6. 测试方案

### 结果一致性

同一日期分别执行：

```text
legacy flow
task flow
```

比较项：

- 输出文件行数。
- 日报 summary。
- 总销售额。
- 总订单数。
- 商品 TOP 排名。
- 门店 TOP 排名。
- 近 7 天门店销售窗口。
- warnings 数量和内容。

通过标准：

- 核心金额字段完全一致。
- 核心数量字段完全一致。
- 排名字段在相同排序规则下完全一致。
- 差异必须能追溯到基础层数据刷新时间，而不是 Task 流程口径变化。

### 错误处理

测试场景：

- 日期为空。
- 日期格式错误。
- 当前用户为空。
- 选中日期没有基础层数据。
- 缺少商品订单基础表。
- 缺少门店财务或门店流量数据。
- ReportExecutor 抛出异常。

通过标准：

- TaskResult.status 为 `failed`。
- error 字段有可读原因。
- 页面不白屏。
- 不产生空的正式交付文件。
- 不降级为读取原始 CSV/Excel。

### 重复提交

测试场景：

- 同一用户、同一日期连续点击 2 次。
- 不同用户、同一日期同时提交。
- 第一次任务运行中再次提交。

建议策略：

- 第一阶段允许重复提交，但每次 task_id 独立。
- 第二阶段增加幂等键：

```text
brand_id + platform + channel + report_type + report_date + created_by
```

通过标准：

- 不覆盖已有结果文件。
- 不污染基础数据层。
- 用户能分清每一次任务结果。

### 权限

测试角色：

- 管理员。
- 业务负责人。
- 小组长。
- 普通用户。

测试规则：

- 管理员可以查看全部日报任务。
- 业务负责人可以生成和查看自己负责品牌。
- 小组长只能查看负责范围。
- 普通用户只能生成和查看自己的任务。

当前阶段说明：

- 如果 RBAC 尚未正式接入，本阶段只在方案和测试用例中预留权限验证。
- 不应在 Step 6-J 修改权限系统或数据库。

### 开关测试

测试配置：

```text
REPORT_TASK_MODE 未设置
REPORT_TASK_MODE=legacy
REPORT_TASK_MODE=task
REPORT_TASK_MODE=invalid
```

通过标准：

- 未设置时走 legacy。
- `legacy` 时旧流程行为不变。
- `task` 时进入 TaskSubmitter。
- 非法值不会静默进入未知流程。

## 7. 建议实施顺序

1. 增加只读配置读取：`REPORT_TASK_MODE`，默认 `legacy`。
2. 在日报入口加入最小分支，但保持旧流程完整。
3. Task 分支只接入安踏儿童美团日报。
4. 建立 legacy vs task 结果一致性测试。
5. 增加任务状态展示页面或复用现有 job 结果页。
6. 内部用户灰度。
7. 稳定后再把数据同步和基础层入库拆成 `DATA_IMPORT` 任务。

## 8. 验收标准

本灰度方案完成后的验收标准：

- `REPORT_TASK_MODE=legacy` 时，现有日报功能完全不变。
- `REPORT_TASK_MODE=task` 时，日报通过 TaskSubmitter、TaskRunner、ReportExecutor、ReportService 生成。
- Task 模式仍只从基础数据层取数。
- 同一天 legacy 和 task 输出结果一致。
- 失败任务可追踪。
- 切回 legacy 不需要代码回滚。
- 旧同步流程在正式稳定前不删除。
