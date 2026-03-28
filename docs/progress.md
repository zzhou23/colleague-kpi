## 当前状态
- 已完成：Phase 1 全部（Task 1-5）、Phase 2 全部（Task 6-8）、Phase 3 全部（数据解析器）、Phase 4 全部（评分引擎）
- 进行中：无
- 未开始：Phase 5-7（Task 15-24）

## 完成进度

| Phase | Tasks | 状态 |
|-------|-------|------|
| Phase 1: 项目骨架 & Server 核心 | Task 1-5 | 全部完成 |
| Phase 2: 采集 Agent | Task 6-8 | 全部完成 |
| Phase 3: 数据解析器 | Task 9-12 | 全部完成 |
| Phase 4: 评分引擎 | Task 13-14 | 全部完成 |
| Phase 5: API 扩展 | Task 15-16 | 未开始 |
| Phase 6: React 前端 | Task 17-22 | 未开始 |
| Phase 7: Docker 部署 | Task 23-24 | 未开始 |

## 关键决策
- 使用 `bcrypt` 直接调用而非 `passlib.hash.bcrypt`，因为 bcrypt 5.x 移除了 `__about__` 模块导致 passlib 不兼容（Task 4 中发现并解决）
- DB 使用同步 SQLAlchemy Session（`create_engine` + `Session`），测试用 SQLite 内存数据库，生产用 PostgreSQL
- Uploader 使用 `httpx` 同步客户端，返回 frozen dataclass `UploadResult`
- Collector 在打包后自动清理 sanitized 临时目录，只保留 tar.gz
- **Parser 架构**：4 个独立 parser 模块 + 1 个 orchestrator
  - history / sessions 返回 `ParserResult`（per-month 指标）
  - config / tasks 返回 `dict`（snapshot 全局指标，应用到所有月份）
  - `merge_parser_results()` 合并为 `MonthlyMetrics` frozen dataclass
  - orchestrator 负责解压 tar.gz → 找到 claude 数据目录 → 运行 parser → 写入 DB
- **Session 数据结构**：session JSONL 中 `message.content` 包含 `tool_use` 块（不在 `data` 字段），`message.usage` 包含 token 统计
- **Config/Tasks 是快照指标**：不按月分组，整体作为当前状态应用到所有月份
- **评分引擎架构**：纯函数管线，无状态可测试
  - 5 种评分函数：linear, threshold, ratio, inverse, capped_linear
  - 25 个评分维度，5 类别（activity/quality/configuration/efficiency/resource）
  - 类别内权重归一（每类 sum=1.0），类别间权重：activity 25%, quality 25%, efficiency 25%, resource 15%, configuration 10%
  - 等级：S(>=90), A(>=75), B(>=60), C(>=40), D(<40)
  - DB 层使用 upsert 语义（先删后插），cognition_score 字段映射 configuration 类别
  - `score_employee_month()` 是顶层入口：读 ParsedMetrics → 转 MonthlyMetrics → score_metrics → persist

## 已知问题
- 原始设计文档和实施计划文件丢失（`docs/superpowers/specs/` 和 `docs/superpowers/plans/`）
- `pytest-httpx` 通过 `uv pip install` 安装，未写入 pyproject.toml（uv add 有权限问题）
- 部分高级指标暂用占位值：`large_file_reads`（需要 tool_result 数据判断文件大小）、`repeated_queries`（需要 NLP 相似度分析）、`error_recovery_avg_turns`（需要错误模式检测）、`rejected_commands`（需要更精确的命令失败判定）

## Commit 历史
- `1ca082e` — chore: initialize project structure
- `083ed1e` — feat: add server configuration with pydantic-settings
- `efba6b8` — feat: add database models
- `9907659` — feat: FastAPI app + upload endpoint
- `fd5d69e` — feat: employee CRUD API
- `8c16163` — docs: add progress tracking
- `89744b0` — feat: add data parsers and orchestrator (Phase 3)
- `22a57ea` — feat: add grade assignment (S/A/B/C/D) with boundaries
- `8830862` — feat: add pure scoring functions (linear, threshold, ratio, inverse, capped)
- `72a69e6` — feat: add 25 scoring dimensions across 5 categories
- `88805bb` — feat: add scoring engine with category aggregation and grading
- `1d6559a` — feat: add scoring persistence layer with upsert semantics
- `8dbea6b` — feat: add scoring orchestration — bridge ParsedMetrics to scoring engine

## 下一步
1. Task 15-16: API 扩展（评分查询 + 月度报告 API）
2. Task 17-22: React 前端（5 个核心页面）
3. Task 23-24: Docker 部署
