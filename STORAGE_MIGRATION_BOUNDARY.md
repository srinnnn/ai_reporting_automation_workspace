# STORAGE_MIGRATION_BOUNDARY

生成日期：2026-08-03

当前阶段：生产化基础 Step 1 - storage.py 冻结说明

## 1. 冻结目标

`intranet_app/storage.py` 当前仍承载用户、Session、Task、Job、Foundation 数据、Report 结果和 SQLite 初始化能力。短期内不删除、不重写、不迁移 schema，避免破坏现有日报、周报、AI 选品和 legacy 页面流程。

从本阶段开始，`storage.py` 被定义为 Legacy Adapter。

## 2. 允许范围

允许继续存在的调用：

- legacy 页面和历史流程的既有调用。
- SQLite Repository Adapter 内部对 `AppStorage` 的适配调用。
- 现有测试中验证 legacy 存储行为的直接调用。
- 数据迁移、诊断、回填和兼容性测试。

## 3. 禁止范围

新功能禁止直接调用：

```text
intranet_app.storage.AppStorage
```

新功能必须通过：

```text
Service
  -> Repository Interface
  -> SQLite/PostgreSQL Adapter
```

禁止在新的 Controller、Service、Executor、Worker 中新增直接 `AppStorage` 调用。

## 4. Repository 边界

新增数据库访问能力时，应先扩展：

```text
backend/repositories/interfaces.py
```

再实现对应 Adapter：

```text
backend/repositories/sqlite/
backend/repositories/postgresql/
```

Service 只能依赖接口，不能依赖 `storage.py`。

## 5. 迁移方向

目标结构：

```text
Controller
  -> Service
  -> Repository Interface
  -> Adapter
  -> Database
```

过渡期结构：

```text
Controller / Service
  -> Repository Interface
  -> SQLite Adapter
  -> AppStorage
  -> SQLite
```

最终目标：

```text
Controller / Service
  -> Repository Interface
  -> PostgreSQL Adapter
  -> PostgreSQL
```

## 6. 验收标准

后续 Step 修改应满足：

- 不在新文件里新增 `from intranet_app.storage import AppStorage`，除非文件是 Repository Adapter、legacy 兼容测试或明确迁移工具。
- 不修改现有 SQLite schema。
- 不删除 legacy 方法。
- 新增数据能力先定义 Repository 接口。
- `python -m intranet_app.app` 继续可运行。
- 现有测试继续通过。
