# Private Data Local Center Integration V1

## Context / 背景

业务需要从中台发现并打开已经独立开发的私域数据采集中心，同时保持“按项目分类、后台能力共享”的中台结构。

Business users need to discover and open the independently developed Private Data Local Center from the middle platform while preserving project-oriented navigation and shared backend capabilities.

V1 只接入现有需求收集能力，不实现真实采集、图片抓取、清洗、凭证管理或生产发布。

V1 integrates the existing request-intake capability only. Real collection, image scraping, cleaning, credential management, and production release are out of scope.

## Decision / 决策

两个仓库和运行进程保持独立。中台负责项目登记、健康检查和同源白名单代理；私域中心负责表单、业务校验、状态转换、幂等和 SQLite 持久化。

The repositories and runtime processes remain separate. The middle platform owns project registration, health discovery, and a same-origin allowlisted proxy. The private center owns the form, business validation, state transitions, idempotency, and SQLite persistence.

```text
USER_ENTRY
Middle platform /projects/private_data_local_center

PRODUCTION_ENTRY
http://127.0.0.1:8785

CALL_CHAIN
React project page
-> GET /api/v1/integrations/private-data-local-center/health
-> middle-platform gateway
-> private-data-local-center /health
-> enabled same-origin entry
-> existing private-center React form
-> four explicit /api/v1/collection-requests routes
-> existing private-center Service
-> existing private-center Repository
-> private-center SQLite
-> response/readback through the same route
```

## Ownership / 归属

| Concern | Authoritative owner |
| --- | --- |
| Project discovery and ANTA/P1 placement | Middle platform `PlatformService` |
| Integration origin | Middle platform server configuration |
| Live availability | Private center `/health`, observed by the middle platform |
| Form and validation contract | Private Data Local Center |
| Request status and version | Private Data Local Center |
| Durable request data | Private Data Local Center SQLite |
| Recovery and readback | Private Data Local Center request API |

中台不保存采集需求副本，因此不会形成第二个数据事实源。

The middle platform stores no collection-request copy, so it does not create a second data source of truth.

## Status Model / 状态模型

`CONFIGURED` 是项目目录状态，表示中台已登记并接线；`AVAILABLE` / `UNAVAILABLE` 是实时健康状态，表示独立服务当前是否可访问。目录状态不得冒充实时健康。

`CONFIGURED` is catalog state, meaning the project is registered and wired in the middle platform. `AVAILABLE` / `UNAVAILABLE` is live health state, meaning the separate service is currently reachable. Catalog state must not be presented as live health.

现有“已接项目”计数沿用项目目录口径，包含 `CONFIGURED` 项目；项目详情页必须以实时健康决定是否启用入口。

The existing connected-project count retains its catalog meaning and includes `CONFIGURED` projects. The project detail page must use live health to decide whether the entry action is enabled.

## Proxy Contract / 代理契约

允许的页面资源：

Allowed frontend resources:

- `GET /integrations/private-data-local-center`
- `GET /integrations/private-data-local-center/`
- `GET /integrations/private-data-local-center/assets/{asset_path}`

允许的业务 API：

Allowed business APIs:

- `POST /api/v1/collection-requests`
- `GET /api/v1/collection-requests/{request_id}`
- `POST /api/v1/collection-requests/{request_id}/draft`
- `POST /api/v1/collection-requests/{request_id}/submit`

任何其他 `/integrations/private-data-local-center/*` 路径返回 `404`，不得转发。上游不可达时，健康状态返回 `UNAVAILABLE`，入口按钮禁用，业务 API 返回 `502`。

Every other `/integrations/private-data-local-center/*` path returns `404` without upstream forwarding. When the upstream is unreachable, health reports `UNAVAILABLE`, the entry action is disabled, and business APIs return `502`.

## Runtime And Deployment / 运行与部署

`PRIVATE_DATA_LOCAL_CENTER_URL` 是服务端配置，只接受不含凭证、路径、查询或片段的 HTTP(S) origin。默认值为 `http://127.0.0.1:8000`。

`PRIVATE_DATA_LOCAL_CENTER_URL` is server-side configuration and accepts only an HTTP(S) origin without credentials, path, query, or fragment. The default is `http://127.0.0.1:8000`.

V1 不负责启动私域中心。运行中台前必须独立启动私域中心并确认 `/health`；否则中台保持可用，但集成入口 fail closed。

V1 does not start the private center. Operators must start it separately and verify `/health` before using the integration; otherwise the middle platform remains available while the integration entry fails closed.

## Security And Data / 安全与数据

```text
DATA_CLASSIFICATION = INTERNAL BUSINESS REQUEST DATA
ALLOWED_STORAGE = private-data-local-center configured SQLite only
MIDDLE_PLATFORM_PERSISTENCE = NONE
LOGGING_POLICY = no request body, credentials, cookies, tokens, or raw records
THIRD_PARTY_TRANSFER = NONE IN V1
RETENTION = OWNED BY PRIVATE DATA LOCAL CENTER; POLICY NOT DEFINED IN THIS PR
DELETION = OWNED BY PRIVATE DATA LOCAL CENTER; WORKFLOW NOT DEFINED IN THIS PR
```

本 PR 不新增鉴权。集成继承中台现有访问边界；在鉴权、隧道访问策略、保留和删除政策完成独立验收前，`RELEASE_GATE = NOT_READY`。

This PR adds no authentication. The integration inherits the middle platform's existing access boundary. Until authentication, tunnel access policy, retention, and deletion are independently accepted, `RELEASE_GATE = NOT_READY`.

禁止通过公开隧道暴露该集成来替代上述验收。

Do not expose this integration through a public tunnel as a substitute for those acceptance gates.

## Alternatives / 备选方案

1. `iframe`: rejected because it creates cross-origin routing and API complexity and weakens a single middle-platform entry.
2. Copy the form into the middle platform: rejected because it duplicates business rules and state ownership.
3. Merge both repositories or databases: rejected because V1 does not require a new shared persistence boundary.
4. Generic reverse proxy: rejected because it exposes unreviewed upstream paths.

## Consequences / 影响

- The user gets one middle-platform entry while the private center remains independently testable and deployable.
- Both processes must be running for the integrated form to be available.
- Upstream validation errors and status codes remain visible to the existing form.
- New private-center endpoints are not automatically exposed; each route requires an explicit middle-platform change and review.

## Rollback / 回滚

回滚本 PR 即可移除项目登记、健康检查和代理路由。私域中心数据库不受影响，因为中台从不迁移或写入该数据库之外的副本。

Reverting this PR removes project registration, health discovery, and proxy routes. The private-center database is unaffected because the middle platform never migrates it or writes a second copy.
