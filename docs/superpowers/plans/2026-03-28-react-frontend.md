# Phase 6: React Frontend Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a React management dashboard with 5 pages (Dashboard, Employee List, Employee Detail, Reports, Settings) backed by existing + new aggregation API endpoints.

**Architecture:** Vite + React 18 + TypeScript SPA with Ant Design for UI and ECharts for charts. Axios API layer talks to FastAPI backend. Vite dev proxy forwards `/api` to `localhost:8000`. Backend gets 2 new aggregation endpoints for dashboard data.

**Tech Stack:** React 18, TypeScript, Vite, Ant Design 5, echarts + echarts-for-react, React Router v6, Axios

---

### Task 1: Backend — Add Dashboard Aggregation Endpoints

**Files:**
- Create: `server/src/server/api/dashboard.py`
- Create: `server/tests/test_dashboard_api.py`
- Modify: `server/src/server/api/schemas.py`
- Modify: `server/src/server/api/router.py`

- [ ] **Step 1: Add response schemas**

In `server/src/server/api/schemas.py`, append:

```python
class DashboardSummaryResponse(BaseModel):
    total_employees: int
    avg_score: float
    max_score: float
    min_score: float
    grade_distribution: dict[str, int]


class RankingEntry(BaseModel):
    employee_id: int
    name: str
    department: str
    total_score: float
    grade: str


class EmployeeWithScoreResponse(EmployeeResponse):
    total_score: float | None = None
    grade: str | None = None
```

- [ ] **Step 2: Write the failing tests**

Create `server/tests/test_dashboard_api.py`:

```python
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from server.db.models import Base, Employee, MonthlyReport
from server.main import create_app
from server.config import Settings


@pytest.fixture()
def client():
    settings = Settings(
        database_url="sqlite:///test_dashboard.db",
        secret_key="test-secret",
    )
    app = create_app(settings)
    sync_url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(sync_url)
    Base.metadata.create_all(engine)
    session = Session(engine)
    # Seed 3 employees with reports
    for i, (name, dept, score, grade) in enumerate([
        ("Alice", "Engineering", 92.0, "S"),
        ("Bob", "Engineering", 78.0, "A"),
        ("Carol", "Design", 55.0, "C"),
    ], start=1):
        emp = Employee(id=i, name=name, email=f"{name.lower()}@test.com", department=dept)
        session.add(emp)
        session.flush()
        report = MonthlyReport(
            employee_id=i,
            year_month="2026-03",
            activity_score=score,
            quality_score=score,
            cognition_score=score,
            efficiency_score=score,
            resource_score=score,
            total_score=score,
            grade=grade,
        )
        session.add(report)
    session.commit()
    session.close()
    yield TestClient(app)
    import os
    engine.dispose()
    os.unlink("test_dashboard.db")


def test_dashboard_summary(client):
    resp = client.get("/api/dashboard/summary", params={"year_month": "2026-03"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_employees"] == 3
    assert data["grade_distribution"]["S"] == 1
    assert data["grade_distribution"]["A"] == 1
    assert data["grade_distribution"]["C"] == 1
    assert data["avg_score"] == pytest.approx(75.0, abs=0.1)
    assert data["max_score"] == pytest.approx(92.0)
    assert data["min_score"] == pytest.approx(55.0)


def test_dashboard_rankings_top(client):
    resp = client.get("/api/dashboard/rankings", params={
        "year_month": "2026-03", "order": "top", "limit": 2
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 2
    assert data[0]["name"] == "Alice"
    assert data[0]["total_score"] == pytest.approx(92.0)


def test_dashboard_rankings_bottom(client):
    resp = client.get("/api/dashboard/rankings", params={
        "year_month": "2026-03", "order": "bottom", "limit": 1
    })
    assert resp.status_code == 200
    data = resp.json()
    assert len(data) == 1
    assert data[0]["name"] == "Carol"


def test_dashboard_summary_no_data(client):
    resp = client.get("/api/dashboard/summary", params={"year_month": "2099-01"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_employees"] == 3
    assert data["avg_score"] == 0.0
    assert data["grade_distribution"] == {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `cd server && uv run pytest tests/test_dashboard_api.py -v`
Expected: FAIL — no dashboard module/routes

- [ ] **Step 4: Implement dashboard endpoints**

Create `server/src/server/api/dashboard.py`:

```python
from fastapi import APIRouter, Query
from sqlalchemy import create_engine, select, func
from sqlalchemy.orm import Session

from server.api.deps import get_settings
from server.api.schemas import DashboardSummaryResponse, RankingEntry
from server.db.models import Employee, MonthlyReport

router = APIRouter()


def _get_sync_session() -> Session:
    settings = get_settings()
    url = settings.database_url.replace("+asyncpg", "")
    engine = create_engine(url)
    return Session(engine)


@router.get("/dashboard/summary", response_model=DashboardSummaryResponse)
async def dashboard_summary(
    year_month: str = Query(..., description="Format: YYYY-MM"),
) -> DashboardSummaryResponse:
    session = _get_sync_session()
    total_employees = session.scalar(select(func.count(Employee.id)))

    reports = (
        session.execute(
            select(MonthlyReport).where(MonthlyReport.year_month == year_month)
        )
        .scalars()
        .all()
    )

    if not reports:
        return DashboardSummaryResponse(
            total_employees=total_employees or 0,
            avg_score=0.0,
            max_score=0.0,
            min_score=0.0,
            grade_distribution={"S": 0, "A": 0, "B": 0, "C": 0, "D": 0},
        )

    scores = [r.total_score for r in reports]
    grade_dist = {"S": 0, "A": 0, "B": 0, "C": 0, "D": 0}
    for r in reports:
        if r.grade in grade_dist:
            grade_dist[r.grade] += 1

    return DashboardSummaryResponse(
        total_employees=total_employees or 0,
        avg_score=round(sum(scores) / len(scores), 1),
        max_score=max(scores),
        min_score=min(scores),
        grade_distribution=grade_dist,
    )


@router.get("/dashboard/rankings", response_model=list[RankingEntry])
async def dashboard_rankings(
    year_month: str = Query(..., description="Format: YYYY-MM"),
    order: str = Query("top", description="top or bottom"),
    limit: int = Query(10, ge=1, le=100),
) -> list[RankingEntry]:
    session = _get_sync_session()

    query = (
        select(MonthlyReport, Employee)
        .join(Employee, MonthlyReport.employee_id == Employee.id)
        .where(MonthlyReport.year_month == year_month)
    )

    if order == "bottom":
        query = query.order_by(MonthlyReport.total_score.asc())
    else:
        query = query.order_by(MonthlyReport.total_score.desc())

    query = query.limit(limit)
    rows = session.execute(query).all()

    return [
        RankingEntry(
            employee_id=emp.id,
            name=emp.name,
            department=emp.department,
            total_score=report.total_score,
            grade=report.grade,
        )
        for report, emp in rows
    ]
```

- [ ] **Step 5: Register dashboard router**

In `server/src/server/api/router.py`, add:

```python
from server.api.dashboard import router as dashboard_router
```

And add this line after the existing includes:

```python
api_router.include_router(dashboard_router)
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `cd server && uv run pytest tests/test_dashboard_api.py -v`
Expected: All 4 tests PASS

- [ ] **Step 7: Commit**

```bash
git add server/src/server/api/dashboard.py server/src/server/api/schemas.py server/src/server/api/router.py server/tests/test_dashboard_api.py
git commit -m "feat: add dashboard aggregation API endpoints"
```

---

### Task 2: Vite Project Initialization

**Files:**
- Create: `web/package.json` (via npm init)
- Create: `web/vite.config.ts`
- Create: `web/tsconfig.json`
- Create: `web/index.html`
- Create: `web/src/main.tsx`
- Create: `web/src/App.tsx`

- [ ] **Step 1: Initialize Vite project**

```bash
cd web
npm create vite@latest . -- --template react-ts
```

If prompted about non-empty dir, confirm. This creates the base project structure.

- [ ] **Step 2: Install dependencies**

```bash
cd web
npm install antd @ant-design/icons echarts echarts-for-react react-router-dom axios dayjs
```

- [ ] **Step 3: Configure Vite proxy**

Replace `web/vite.config.ts`:

```typescript
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://localhost:8000",
        changeOrigin: true,
      },
    },
  },
});
```

- [ ] **Step 4: Create entry point**

Replace `web/src/main.tsx`:

```tsx
import React from "react";
import ReactDOM from "react-dom/client";
import { BrowserRouter } from "react-router-dom";
import { ConfigProvider } from "antd";
import zhCN from "antd/locale/zh_CN";
import App from "./App";
import "./index.css";

ReactDOM.createRoot(document.getElementById("root")!).render(
  <React.StrictMode>
    <ConfigProvider locale={zhCN}>
      <BrowserRouter>
        <App />
      </BrowserRouter>
    </ConfigProvider>
  </React.StrictMode>,
);
```

- [ ] **Step 5: Create App shell with router and layout**

Replace `web/src/App.tsx`:

```tsx
import { Routes, Route, useNavigate, useLocation } from "react-router-dom";
import { Layout, Menu } from "antd";
import {
  DashboardOutlined,
  TeamOutlined,
  BarChartOutlined,
  SettingOutlined,
} from "@ant-design/icons";
import Dashboard from "./pages/Dashboard";
import EmployeeList from "./pages/EmployeeList";
import EmployeeDetail from "./pages/EmployeeDetail";
import Reports from "./pages/Reports";
import Settings from "./pages/Settings";

const { Sider, Content } = Layout;

const menuItems = [
  { key: "/", icon: <DashboardOutlined />, label: "总览仪表盘" },
  { key: "/employees", icon: <TeamOutlined />, label: "员工列表" },
  { key: "/reports", icon: <BarChartOutlined />, label: "月度报告" },
  { key: "/settings", icon: <SettingOutlined />, label: "系统管理" },
];

function App() {
  const navigate = useNavigate();
  const location = useLocation();

  const selectedKey = menuItems
    .filter((item) => location.pathname.startsWith(item.key) && item.key !== "/")
    .sort((a, b) => b.key.length - a.key.length)[0]?.key ?? "/";

  return (
    <Layout style={{ minHeight: "100vh" }}>
      <Sider breakpoint="lg" collapsedWidth={80}>
        <div
          style={{
            height: 64,
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            color: "#fff",
            fontWeight: 700,
            fontSize: 18,
          }}
        >
          AI 绩效
        </div>
        <Menu
          theme="dark"
          mode="inline"
          selectedKeys={[selectedKey]}
          items={menuItems}
          onClick={({ key }) => navigate(key)}
        />
      </Sider>
      <Layout>
        <Content style={{ margin: 24 }}>
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/employees" element={<EmployeeList />} />
            <Route path="/employees/:id" element={<EmployeeDetail />} />
            <Route path="/reports" element={<Reports />} />
            <Route path="/settings" element={<Settings />} />
          </Routes>
        </Content>
      </Layout>
    </Layout>
  );
}

export default App;
```

- [ ] **Step 6: Create placeholder pages**

Create `web/src/pages/Dashboard.tsx`:

```tsx
function Dashboard() {
  return <div>Dashboard — 待实现</div>;
}
export default Dashboard;
```

Create `web/src/pages/EmployeeList.tsx`:

```tsx
function EmployeeList() {
  return <div>EmployeeList — 待实现</div>;
}
export default EmployeeList;
```

Create `web/src/pages/EmployeeDetail.tsx`:

```tsx
function EmployeeDetail() {
  return <div>EmployeeDetail — 待实现</div>;
}
export default EmployeeDetail;
```

Create `web/src/pages/Reports.tsx`:

```tsx
function Reports() {
  return <div>Reports — 待实现</div>;
}
export default Reports;
```

Create `web/src/pages/Settings.tsx`:

```tsx
function Settings() {
  return <div>Settings — 待实现</div>;
}
export default Settings;
```

- [ ] **Step 7: Replace default CSS**

Replace `web/src/index.css`:

```css
body {
  margin: 0;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
}
```

- [ ] **Step 8: Verify dev server starts**

```bash
cd web && npm run dev
```

Expected: Vite dev server starts on `http://localhost:5173`, shows layout with sidebar and placeholder pages.

- [ ] **Step 9: Commit**

```bash
cd web && echo "node_modules" > .gitignore
git add web/
git commit -m "feat: initialize Vite React project with routing and layout"
```

---

### Task 3: API Layer and TypeScript Types

**Files:**
- Create: `web/src/types/index.ts`
- Create: `web/src/api/client.ts`
- Create: `web/src/api/dashboard.ts`
- Create: `web/src/api/employees.ts`
- Create: `web/src/api/scores.ts`

- [ ] **Step 1: Define shared types**

Create `web/src/types/index.ts`:

```typescript
export interface Employee {
  id: number;
  name: string;
  email: string;
  department: string;
  role: string;
}

export interface EmployeeCreateResponse extends Employee {
  api_key: string;
}

export interface DimensionScore {
  id: number;
  category: string;
  dimension_name: string;
  raw_value: number;
  score: number;
  year_month: string;
}

export interface MonthlyReport {
  id: number;
  employee_id: number;
  year_month: string;
  activity_score: number;
  quality_score: number;
  cognition_score: number;
  efficiency_score: number;
  resource_score: number;
  total_score: number;
  grade: string;
}

export interface DashboardSummary {
  total_employees: number;
  avg_score: number;
  max_score: number;
  min_score: number;
  grade_distribution: Record<string, number>;
}

export interface RankingEntry {
  employee_id: number;
  name: string;
  department: string;
  total_score: number;
  grade: string;
}

export type Grade = "S" | "A" | "B" | "C" | "D";

export const GRADE_COLORS: Record<Grade, string> = {
  S: "gold",
  A: "green",
  B: "blue",
  C: "orange",
  D: "red",
};

export const CATEGORY_LABELS: Record<string, string> = {
  activity: "活跃度",
  quality: "使用质量",
  configuration: "AI 认知",
  efficiency: "效率指标",
  resource: "资源合理性",
};

export const CATEGORY_WEIGHTS: Record<string, number> = {
  activity: 0.25,
  quality: 0.25,
  configuration: 0.10,
  efficiency: 0.25,
  resource: 0.15,
};
```

- [ ] **Step 2: Create Axios client**

Create `web/src/api/client.ts`:

```typescript
import axios from "axios";

const client = axios.create({
  baseURL: "/api",
  timeout: 15000,
});

export default client;
```

- [ ] **Step 3: Create dashboard API module**

Create `web/src/api/dashboard.ts`:

```typescript
import client from "./client";
import type { DashboardSummary, RankingEntry } from "../types";

export async function fetchSummary(yearMonth: string): Promise<DashboardSummary> {
  const { data } = await client.get<DashboardSummary>("/dashboard/summary", {
    params: { year_month: yearMonth },
  });
  return data;
}

export async function fetchRankings(
  yearMonth: string,
  order: "top" | "bottom",
  limit: number = 10,
): Promise<RankingEntry[]> {
  const { data } = await client.get<RankingEntry[]>("/dashboard/rankings", {
    params: { year_month: yearMonth, order, limit },
  });
  return data;
}
```

- [ ] **Step 4: Create employees API module**

Create `web/src/api/employees.ts`:

```typescript
import client from "./client";
import type { Employee, EmployeeCreateResponse } from "../types";

export async function fetchEmployees(): Promise<Employee[]> {
  const { data } = await client.get<Employee[]>("/employees");
  return data;
}

export async function fetchEmployee(id: number): Promise<Employee> {
  const { data } = await client.get<Employee>(`/employees/${id}`);
  return data;
}

export async function createEmployee(body: {
  name: string;
  email: string;
  department: string;
  role?: string;
}): Promise<EmployeeCreateResponse> {
  const { data } = await client.post<EmployeeCreateResponse>("/employees", body);
  return data;
}
```

- [ ] **Step 5: Create scores API module**

Create `web/src/api/scores.ts`:

```typescript
import client from "./client";
import type { DimensionScore, MonthlyReport } from "../types";

export async function fetchScores(
  employeeId: number,
  yearMonth?: string,
): Promise<DimensionScore[]> {
  const { data } = await client.get<DimensionScore[]>(
    `/employees/${employeeId}/scores`,
    { params: yearMonth ? { year_month: yearMonth } : {} },
  );
  return data;
}

export async function fetchReports(
  employeeId: number,
  yearMonth?: string,
): Promise<MonthlyReport[]> {
  const { data } = await client.get<MonthlyReport[]>(
    `/employees/${employeeId}/reports`,
    { params: yearMonth ? { year_month: yearMonth } : {} },
  );
  return data;
}

export async function triggerScoring(
  employeeId: number,
  yearMonth: string,
): Promise<MonthlyReport> {
  const { data } = await client.post<MonthlyReport>(
    `/employees/${employeeId}/score`,
    { year_month: yearMonth },
  );
  return data;
}
```

- [ ] **Step 6: Commit**

```bash
git add web/src/types/ web/src/api/
git commit -m "feat: add TypeScript types and API layer"
```

---

### Task 4: Shared Components (GradeTag, RadarChart, TrendLine, MonthPicker)

**Files:**
- Create: `web/src/components/GradeTag.tsx`
- Create: `web/src/components/RadarChart.tsx`
- Create: `web/src/components/TrendLine.tsx`
- Create: `web/src/components/MonthPicker.tsx`

- [ ] **Step 1: Create GradeTag component**

Create `web/src/components/GradeTag.tsx`:

```tsx
import { Tag } from "antd";
import { GRADE_COLORS, type Grade } from "../types";

interface GradeTagProps {
  grade: string;
}

function GradeTag({ grade }: GradeTagProps) {
  const color = GRADE_COLORS[grade as Grade] ?? "default";
  return <Tag color={color}>{grade}</Tag>;
}

export default GradeTag;
```

- [ ] **Step 2: Create RadarChart component**

Create `web/src/components/RadarChart.tsx`:

```tsx
import ReactECharts from "echarts-for-react";
import { CATEGORY_LABELS } from "../types";

interface RadarChartProps {
  scores: Record<string, number>; // { activity: 80, quality: 70, ... }
}

function RadarChart({ scores }: RadarChartProps) {
  const categories = Object.keys(CATEGORY_LABELS);
  const indicators = categories.map((key) => ({
    name: CATEGORY_LABELS[key],
    max: 100,
  }));
  const values = categories.map((key) => scores[key] ?? 0);

  const option = {
    radar: {
      indicator: indicators,
      shape: "polygon" as const,
    },
    series: [
      {
        type: "radar" as const,
        data: [
          {
            value: values,
            name: "评分",
            areaStyle: { opacity: 0.2 },
          },
        ],
      },
    ],
    tooltip: {},
  };

  return <ReactECharts option={option} style={{ height: 350 }} />;
}

export default RadarChart;
```

- [ ] **Step 3: Create TrendLine component**

Create `web/src/components/TrendLine.tsx`:

```tsx
import ReactECharts from "echarts-for-react";
import { CATEGORY_LABELS } from "../types";
import type { MonthlyReport } from "../types";

interface TrendLineProps {
  reports: MonthlyReport[];
}

const LINE_COLORS: Record<string, string> = {
  total: "#1890ff",
  activity: "#52c41a",
  quality: "#722ed1",
  configuration: "#fa8c16",
  efficiency: "#13c2c2",
  resource: "#eb2f96",
};

function TrendLine({ reports }: TrendLineProps) {
  const sorted = [...reports].sort((a, b) => a.year_month.localeCompare(b.year_month));
  const months = sorted.map((r) => r.year_month);

  const series = [
    {
      name: "总分",
      type: "line" as const,
      data: sorted.map((r) => r.total_score),
      lineStyle: { width: 3 },
      color: LINE_COLORS.total,
    },
    ...Object.entries(CATEGORY_LABELS).map(([key, label]) => ({
      name: label,
      type: "line" as const,
      data: sorted.map((r) => {
        const scoreKey = key === "configuration" ? "cognition_score" : `${key}_score`;
        return (r as Record<string, unknown>)[scoreKey] as number;
      }),
      lineStyle: { width: 1.5, type: "dashed" as const },
      color: LINE_COLORS[key],
    })),
  ];

  const option = {
    tooltip: { trigger: "axis" as const },
    legend: { data: ["总分", ...Object.values(CATEGORY_LABELS)] },
    xAxis: { type: "category" as const, data: months },
    yAxis: { type: "value" as const, min: 0, max: 100 },
    series,
  };

  return <ReactECharts option={option} style={{ height: 350 }} />;
}

export default TrendLine;
```

- [ ] **Step 4: Create MonthPicker component**

Create `web/src/components/MonthPicker.tsx`:

```tsx
import { DatePicker } from "antd";
import dayjs, { type Dayjs } from "dayjs";

interface MonthPickerProps {
  value: string; // "YYYY-MM"
  onChange: (value: string) => void;
}

function MonthPicker({ value, onChange }: MonthPickerProps) {
  return (
    <DatePicker
      picker="month"
      value={dayjs(value, "YYYY-MM")}
      onChange={(date: Dayjs | null) => {
        if (date) {
          onChange(date.format("YYYY-MM"));
        }
      }}
      allowClear={false}
    />
  );
}

export default MonthPicker;
```

- [ ] **Step 5: Commit**

```bash
git add web/src/components/
git commit -m "feat: add shared components (GradeTag, RadarChart, TrendLine, MonthPicker)"
```

---

### Task 5: Dashboard Page

**Files:**
- Modify: `web/src/pages/Dashboard.tsx`

- [ ] **Step 1: Implement Dashboard page**

Replace `web/src/pages/Dashboard.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Card, Col, Row, Statistic, Table, Spin, Radio, message } from "antd";
import {
  TeamOutlined,
  TrophyOutlined,
  ArrowUpOutlined,
  ArrowDownOutlined,
} from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import dayjs from "dayjs";
import MonthPicker from "../components/MonthPicker";
import GradeTag from "../components/GradeTag";
import { fetchSummary, fetchRankings } from "../api/dashboard";
import { GRADE_COLORS, type DashboardSummary, type RankingEntry, type Grade } from "../types";

function Dashboard() {
  const [yearMonth, setYearMonth] = useState(dayjs().format("YYYY-MM"));
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [rankings, setRankings] = useState<RankingEntry[]>([]);
  const [rankOrder, setRankOrder] = useState<"top" | "bottom">("top");
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchSummary(yearMonth),
      fetchRankings(yearMonth, rankOrder),
    ])
      .then(([s, r]) => {
        setSummary(s);
        setRankings(r);
      })
      .catch(() => message.error("加载仪表盘数据失败"))
      .finally(() => setLoading(false));
  }, [yearMonth, rankOrder]);

  const pieOption = summary
    ? {
        tooltip: { trigger: "item" as const },
        legend: { bottom: 0 },
        series: [
          {
            type: "pie" as const,
            radius: ["40%", "70%"],
            data: (["S", "A", "B", "C", "D"] as Grade[]).map((g) => ({
              name: `${g} 级`,
              value: summary.grade_distribution[g] ?? 0,
              itemStyle: { color: GRADE_COLORS[g] === "gold" ? "#faad14" : GRADE_COLORS[g] === "green" ? "#52c41a" : GRADE_COLORS[g] === "blue" ? "#1890ff" : GRADE_COLORS[g] === "orange" ? "#fa8c16" : "#f5222d" },
            })),
          },
        ],
      }
    : {};

  const columns = [
    { title: "排名", render: (_: unknown, __: unknown, i: number) => i + 1, width: 60 },
    { title: "姓名", dataIndex: "name" },
    { title: "部门", dataIndex: "department" },
    { title: "总分", dataIndex: "total_score", render: (v: number) => v.toFixed(1) },
    { title: "等级", dataIndex: "grade", render: (g: string) => <GradeTag grade={g} /> },
  ];

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 16 }}>
        <h2 style={{ margin: 0 }}>总览仪表盘</h2>
        <MonthPicker value={yearMonth} onChange={setYearMonth} />
      </div>

      {summary && (
        <Row gutter={16} style={{ marginBottom: 24 }}>
          <Col span={6}>
            <Card><Statistic title="员工总数" value={summary.total_employees} prefix={<TeamOutlined />} /></Card>
          </Col>
          <Col span={6}>
            <Card><Statistic title="平均分" value={summary.avg_score} precision={1} prefix={<TrophyOutlined />} /></Card>
          </Col>
          <Col span={6}>
            <Card><Statistic title="最高分" value={summary.max_score} precision={1} valueStyle={{ color: "#52c41a" }} prefix={<ArrowUpOutlined />} /></Card>
          </Col>
          <Col span={6}>
            <Card><Statistic title="最低分" value={summary.min_score} precision={1} valueStyle={{ color: "#f5222d" }} prefix={<ArrowDownOutlined />} /></Card>
          </Col>
        </Row>
      )}

      <Row gutter={16}>
        <Col span={10}>
          <Card title="等级分布">
            {summary && <ReactECharts option={pieOption} style={{ height: 300 }} />}
          </Card>
        </Col>
        <Col span={14}>
          <Card
            title="排行榜"
            extra={
              <Radio.Group value={rankOrder} onChange={(e) => setRankOrder(e.target.value)} size="small">
                <Radio.Button value="top">Top 10</Radio.Button>
                <Radio.Button value="bottom">Bottom 10</Radio.Button>
              </Radio.Group>
            }
          >
            <Table
              dataSource={rankings}
              columns={columns}
              rowKey="employee_id"
              pagination={false}
              size="small"
            />
          </Card>
        </Col>
      </Row>
    </Spin>
  );
}

export default Dashboard;
```

- [ ] **Step 2: Verify in browser**

Run: `cd web && npm run dev`
Navigate to `http://localhost:5173/`. Should render Dashboard layout (data will be empty without backend running).

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Dashboard.tsx
git commit -m "feat: implement Dashboard page with stats, pie chart, and rankings"
```

---

### Task 6: Employee List Page

**Files:**
- Modify: `web/src/pages/EmployeeList.tsx`

- [ ] **Step 1: Implement Employee List page**

Replace `web/src/pages/EmployeeList.tsx`:

```tsx
import { useEffect, useState, useMemo } from "react";
import { useNavigate } from "react-router-dom";
import { Table, Input, Select, Spin, message } from "antd";
import { SearchOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import dayjs from "dayjs";
import GradeTag from "../components/GradeTag";
import MonthPicker from "../components/MonthPicker";
import { fetchEmployees } from "../api/employees";
import { fetchReports } from "../api/scores";
import type { Employee, MonthlyReport } from "../types";

interface EmployeeRow extends Employee {
  total_score: number | null;
  grade: string | null;
}

function EmployeeList() {
  const navigate = useNavigate();
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [reports, setReports] = useState<Map<number, MonthlyReport>>(new Map());
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState("");
  const [deptFilter, setDeptFilter] = useState<string | null>(null);
  const [yearMonth, setYearMonth] = useState(dayjs().format("YYYY-MM"));

  useEffect(() => {
    setLoading(true);
    fetchEmployees()
      .then(setEmployees)
      .catch(() => message.error("加载员工列表失败"))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    if (employees.length === 0) return;
    const loadReports = async () => {
      const reportMap = new Map<number, MonthlyReport>();
      const results = await Promise.allSettled(
        employees.map((e) => fetchReports(e.id, yearMonth)),
      );
      results.forEach((result, idx) => {
        if (result.status === "fulfilled" && result.value.length > 0) {
          reportMap.set(employees[idx].id, result.value[0]);
        }
      });
      setReports(reportMap);
    };
    loadReports();
  }, [employees, yearMonth]);

  const departments = useMemo(
    () => [...new Set(employees.map((e) => e.department))],
    [employees],
  );

  const rows: EmployeeRow[] = useMemo(() => {
    return employees
      .filter((e) => {
        if (deptFilter && e.department !== deptFilter) return false;
        if (search && !e.name.toLowerCase().includes(search.toLowerCase())) return false;
        return true;
      })
      .map((e) => {
        const report = reports.get(e.id);
        return {
          ...e,
          total_score: report?.total_score ?? null,
          grade: report?.grade ?? null,
        };
      });
  }, [employees, reports, search, deptFilter]);

  const columns: ColumnsType<EmployeeRow> = [
    { title: "姓名", dataIndex: "name", sorter: (a, b) => a.name.localeCompare(b.name) },
    { title: "部门", dataIndex: "department" },
    {
      title: "总分",
      dataIndex: "total_score",
      sorter: (a, b) => (a.total_score ?? 0) - (b.total_score ?? 0),
      render: (v: number | null) => (v !== null ? v.toFixed(1) : "—"),
    },
    {
      title: "等级",
      dataIndex: "grade",
      sorter: (a, b) => (a.grade ?? "Z").localeCompare(b.grade ?? "Z"),
      render: (g: string | null) => (g ? <GradeTag grade={g} /> : "—"),
    },
  ];

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 16 }}>
        <h2 style={{ margin: 0 }}>员工列表</h2>
        <MonthPicker value={yearMonth} onChange={setYearMonth} />
      </div>

      <div style={{ marginBottom: 16, display: "flex", gap: 12 }}>
        <Input
          placeholder="搜索姓名..."
          prefix={<SearchOutlined />}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ width: 240 }}
          allowClear
        />
        <Select
          placeholder="筛选部门"
          value={deptFilter}
          onChange={setDeptFilter}
          allowClear
          style={{ width: 180 }}
          options={departments.map((d) => ({ label: d, value: d }))}
        />
      </div>

      <Table
        dataSource={rows}
        columns={columns}
        rowKey="id"
        onRow={(record) => ({
          onClick: () => navigate(`/employees/${record.id}`),
          style: { cursor: "pointer" },
        })}
        pagination={{ pageSize: 20 }}
      />
    </Spin>
  );
}

export default EmployeeList;
```

- [ ] **Step 2: Verify in browser**

Navigate to `http://localhost:5173/employees`. Should render table structure.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/EmployeeList.tsx
git commit -m "feat: implement Employee List page with search, filter, and sorting"
```

---

### Task 7: Employee Detail Page

**Files:**
- Modify: `web/src/pages/EmployeeDetail.tsx`

- [ ] **Step 1: Implement Employee Detail page**

Replace `web/src/pages/EmployeeDetail.tsx`:

```tsx
import { useEffect, useState } from "react";
import { useParams } from "react-router-dom";
import { Card, Col, Row, Spin, Descriptions, message } from "antd";
import ReactECharts from "echarts-for-react";
import dayjs from "dayjs";
import GradeTag from "../components/GradeTag";
import RadarChart from "../components/RadarChart";
import TrendLine from "../components/TrendLine";
import MonthPicker from "../components/MonthPicker";
import { fetchEmployee } from "../api/employees";
import { fetchScores, fetchReports } from "../api/scores";
import { CATEGORY_LABELS } from "../types";
import type { Employee, DimensionScore, MonthlyReport } from "../types";

const DIMENSION_LABELS: Record<string, string> = {
  active_days: "活跃天数",
  session_count: "会话数",
  total_turns: "对话轮数",
  avg_session_duration: "平均时长",
  project_count: "项目覆盖",
  tool_diversity: "工具多样性",
  complex_sessions: "复杂任务",
  tasks_created: "任务创建",
  tasks_completed: "任务完成",
  plans_created: "规划使用",
  model_switches: "模型切换",
  rules_count: "规则配置",
  memory_files: "记忆使用",
  custom_settings: "自定义设置",
  hooks_usage: "Hook 配置",
  skills_used: "技能使用",
  low_abandonment: "低放弃率",
  git_commits: "Git 产出",
  low_repeated_queries: "低重复提问",
  error_recovery: "错误恢复",
  token_efficiency: "Token 效率",
  low_empty_sessions: "低空转",
  low_large_file_reads: "低大文件读取",
  low_repeated_ops: "低重复操作",
  low_rejected_commands: "低失败命令",
};

function EmployeeDetail() {
  const { id } = useParams<{ id: string }>();
  const [employee, setEmployee] = useState<Employee | null>(null);
  const [scores, setScores] = useState<DimensionScore[]>([]);
  const [reports, setReports] = useState<MonthlyReport[]>([]);
  const [currentReport, setCurrentReport] = useState<MonthlyReport | null>(null);
  const [yearMonth, setYearMonth] = useState(dayjs().format("YYYY-MM"));
  const [loading, setLoading] = useState(false);

  const empId = Number(id);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchEmployee(empId),
      fetchReports(empId),
    ])
      .then(([emp, reps]) => {
        setEmployee(emp);
        setReports(reps);
      })
      .catch(() => message.error("加载员工信息失败"))
      .finally(() => setLoading(false));
  }, [empId]);

  useEffect(() => {
    fetchScores(empId, yearMonth).then(setScores).catch(() => {});
    const report = reports.find((r) => r.year_month === yearMonth) ?? null;
    setCurrentReport(report);
  }, [empId, yearMonth, reports]);

  const radarScores = currentReport
    ? {
        activity: currentReport.activity_score,
        quality: currentReport.quality_score,
        configuration: currentReport.cognition_score,
        efficiency: currentReport.efficiency_score,
        resource: currentReport.resource_score,
      }
    : {};

  // Group dimension scores by category for bar chart
  const barOption = {
    tooltip: {},
    grid: { left: 120, right: 20 },
    xAxis: { type: "value" as const, min: 0, max: 100 },
    yAxis: {
      type: "category" as const,
      data: scores.map((s) => DIMENSION_LABELS[s.dimension_name] ?? s.dimension_name).reverse(),
    },
    series: [
      {
        type: "bar" as const,
        data: [...scores].reverse().map((s) => ({
          value: s.score,
          itemStyle: {
            color:
              s.category === "activity" ? "#52c41a" :
              s.category === "quality" ? "#722ed1" :
              s.category === "configuration" ? "#fa8c16" :
              s.category === "efficiency" ? "#13c2c2" :
              "#eb2f96",
          },
        })),
      },
    ],
  };

  return (
    <Spin spinning={loading}>
      {employee && (
        <>
          <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 16 }}>
            <h2 style={{ margin: 0 }}>{employee.name}</h2>
            {currentReport && <GradeTag grade={currentReport.grade} />}
            <MonthPicker value={yearMonth} onChange={setYearMonth} />
          </div>

          <Card style={{ marginBottom: 16 }}>
            <Descriptions column={4}>
              <Descriptions.Item label="邮箱">{employee.email}</Descriptions.Item>
              <Descriptions.Item label="部门">{employee.department}</Descriptions.Item>
              <Descriptions.Item label="角色">{employee.role}</Descriptions.Item>
              <Descriptions.Item label="总分">
                {currentReport ? currentReport.total_score.toFixed(1) : "—"}
              </Descriptions.Item>
            </Descriptions>
          </Card>

          <Row gutter={16} style={{ marginBottom: 16 }}>
            <Col span={10}>
              <Card title="五维雷达图">
                <RadarChart scores={radarScores} />
              </Card>
            </Col>
            <Col span={14}>
              <Card title="各维度得分">
                {scores.length > 0 ? (
                  <ReactECharts option={barOption} style={{ height: Math.max(350, scores.length * 28) }} />
                ) : (
                  <div style={{ textAlign: "center", padding: 40, color: "#999" }}>暂无数据</div>
                )}
              </Card>
            </Col>
          </Row>

          <Card title="趋势（最近 6 个月）">
            {reports.length > 0 ? (
              <TrendLine reports={reports.slice(0, 6)} />
            ) : (
              <div style={{ textAlign: "center", padding: 40, color: "#999" }}>暂无历史数据</div>
            )}
          </Card>
        </>
      )}
    </Spin>
  );
}

export default EmployeeDetail;
```

- [ ] **Step 2: Verify in browser**

Navigate to `http://localhost:5173/employees/1`. Should render detail layout (empty data without backend).

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/EmployeeDetail.tsx
git commit -m "feat: implement Employee Detail page with radar, bar chart, and trend line"
```

---

### Task 8: Monthly Reports Page

**Files:**
- Modify: `web/src/pages/Reports.tsx`

- [ ] **Step 1: Implement Reports page**

Replace `web/src/pages/Reports.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Table, Card, Row, Col, Spin, message, Button } from "antd";
import { DownloadOutlined } from "@ant-design/icons";
import ReactECharts from "echarts-for-react";
import dayjs from "dayjs";
import type { ColumnsType } from "antd/es/table";
import MonthPicker from "../components/MonthPicker";
import GradeTag from "../components/GradeTag";
import { fetchSummary, fetchRankings } from "../api/dashboard";
import type { DashboardSummary, RankingEntry, Grade } from "../types";
import { GRADE_COLORS } from "../types";

function Reports() {
  const [yearMonth, setYearMonth] = useState(dayjs().format("YYYY-MM"));
  const [summary, setSummary] = useState<DashboardSummary | null>(null);
  const [allEmployees, setAllEmployees] = useState<RankingEntry[]>([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    setLoading(true);
    Promise.all([
      fetchSummary(yearMonth),
      fetchRankings(yearMonth, "top", 100),
    ])
      .then(([s, r]) => {
        setSummary(s);
        setAllEmployees(r);
      })
      .catch(() => message.error("加载报告数据失败"))
      .finally(() => setLoading(false));
  }, [yearMonth]);

  const columns: ColumnsType<RankingEntry> = [
    { title: "排名", render: (_: unknown, __: unknown, i: number) => i + 1, width: 60 },
    { title: "姓名", dataIndex: "name", sorter: (a, b) => a.name.localeCompare(b.name) },
    { title: "部门", dataIndex: "department" },
    {
      title: "总分",
      dataIndex: "total_score",
      sorter: (a, b) => a.total_score - b.total_score,
      render: (v: number) => v.toFixed(1),
    },
    {
      title: "等级",
      dataIndex: "grade",
      sorter: (a, b) => a.grade.localeCompare(b.grade),
      render: (g: string) => <GradeTag grade={g} />,
    },
  ];

  const exportCSV = () => {
    const header = "排名,姓名,部门,总分,等级\n";
    const rows = allEmployees
      .map((e, i) => `${i + 1},${e.name},${e.department},${e.total_score.toFixed(1)},${e.grade}`)
      .join("\n");
    const blob = new Blob(["\uFEFF" + header + rows], { type: "text/csv;charset=utf-8;" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `月度报告_${yearMonth}.csv`;
    a.click();
    URL.revokeObjectURL(url);
  };

  const pieOption = summary
    ? {
        series: [
          {
            type: "pie" as const,
            radius: "65%",
            data: (["S", "A", "B", "C", "D"] as Grade[]).map((g) => ({
              name: `${g} 级`,
              value: summary.grade_distribution[g] ?? 0,
              itemStyle: { color: GRADE_COLORS[g] === "gold" ? "#faad14" : GRADE_COLORS[g] === "green" ? "#52c41a" : GRADE_COLORS[g] === "blue" ? "#1890ff" : GRADE_COLORS[g] === "orange" ? "#fa8c16" : "#f5222d" },
            })),
          },
        ],
        tooltip: { trigger: "item" as const },
      }
    : {};

  return (
    <Spin spinning={loading}>
      <div style={{ marginBottom: 16, display: "flex", alignItems: "center", gap: 16 }}>
        <h2 style={{ margin: 0 }}>月度报告</h2>
        <MonthPicker value={yearMonth} onChange={setYearMonth} />
        <Button icon={<DownloadOutlined />} onClick={exportCSV} disabled={allEmployees.length === 0}>
          导出 CSV
        </Button>
      </div>

      {summary && (
        <Row gutter={16} style={{ marginBottom: 16 }}>
          <Col span={16}>
            <Card title="评分汇总">
              <Row>
                <Col span={8}><strong>平均分：</strong>{summary.avg_score.toFixed(1)}</Col>
                <Col span={8}><strong>最高分：</strong>{summary.max_score.toFixed(1)}</Col>
                <Col span={8}><strong>最低分：</strong>{summary.min_score.toFixed(1)}</Col>
              </Row>
            </Card>
          </Col>
          <Col span={8}>
            <Card title="等级分布">
              <ReactECharts option={pieOption} style={{ height: 200 }} />
            </Card>
          </Col>
        </Row>
      )}

      <Card title="全员评分">
        <Table
          dataSource={allEmployees}
          columns={columns}
          rowKey="employee_id"
          pagination={{ pageSize: 20 }}
        />
      </Card>
    </Spin>
  );
}

export default Reports;
```

- [ ] **Step 2: Verify in browser**

Navigate to `http://localhost:5173/reports`.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Reports.tsx
git commit -m "feat: implement Monthly Reports page with CSV export"
```

---

### Task 9: System Settings Page

**Files:**
- Modify: `web/src/pages/Settings.tsx`

- [ ] **Step 1: Implement Settings page**

Replace `web/src/pages/Settings.tsx`:

```tsx
import { useEffect, useState } from "react";
import { Tabs, Table, Button, Modal, Form, Input, Select, Alert, Popconfirm, Spin, message } from "antd";
import { PlusOutlined, CopyOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchEmployees, createEmployee } from "../api/employees";
import { CATEGORY_LABELS, CATEGORY_WEIGHTS } from "../types";
import type { Employee } from "../types";

function Settings() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [form] = Form.useForm();

  const loadEmployees = () => {
    setLoading(true);
    fetchEmployees()
      .then(setEmployees)
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadEmployees();
  }, []);

  const handleCreate = async () => {
    const values = await form.validateFields();
    const result = await createEmployee(values);
    setNewApiKey(result.api_key);
    setModalOpen(false);
    form.resetFields();
    loadEmployees();
    message.success("员工创建成功");
  };

  const copyKey = () => {
    if (newApiKey) {
      navigator.clipboard.writeText(newApiKey);
      message.success("已复制到剪贴板");
    }
  };

  const empColumns: ColumnsType<Employee> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "姓名", dataIndex: "name" },
    { title: "邮箱", dataIndex: "email" },
    { title: "部门", dataIndex: "department" },
    { title: "角色", dataIndex: "role" },
  ];

  const weightData = Object.entries(CATEGORY_LABELS).map(([key, label]) => ({
    key,
    category: label,
    weight: `${(CATEGORY_WEIGHTS[key] * 100).toFixed(0)}%`,
  }));

  const weightColumns = [
    { title: "类别", dataIndex: "category" },
    { title: "英文标识", dataIndex: "key" },
    { title: "权重", dataIndex: "weight" },
  ];

  return (
    <Spin spinning={loading}>
      <h2 style={{ marginBottom: 16 }}>系统管理</h2>

      {newApiKey && (
        <Alert
          message="API Key 已生成（仅显示一次）"
          description={
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <code style={{ fontSize: 14 }}>{newApiKey}</code>
              <Button icon={<CopyOutlined />} size="small" onClick={copyKey}>复制</Button>
            </div>
          }
          type="success"
          closable
          onClose={() => setNewApiKey(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        items={[
          {
            key: "employees",
            label: "员工管理",
            children: (
              <>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setModalOpen(true)}
                  style={{ marginBottom: 16 }}
                >
                  新增员工
                </Button>
                <Table dataSource={employees} columns={empColumns} rowKey="id" pagination={{ pageSize: 20 }} />
              </>
            ),
          },
          {
            key: "weights",
            label: "评分权重",
            children: (
              <Table dataSource={weightData} columns={weightColumns} rowKey="key" pagination={false} />
            ),
          },
        ]}
      />

      <Modal
        title="新增员工"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: "请输入姓名" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: "email", message: "请输入有效邮箱" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department" label="部门" rules={[{ required: true, message: "请输入部门" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="employee">
            <Select options={[{ label: "员工", value: "employee" }, { label: "管理员", value: "admin" }]} />
          </Form.Item>
        </Form>
      </Modal>
    </Spin>
  );
}

export default Settings;
```

- [ ] **Step 2: Verify in browser**

Navigate to `http://localhost:5173/settings`.

- [ ] **Step 3: Commit**

```bash
git add web/src/pages/Settings.tsx
git commit -m "feat: implement Settings page with employee CRUD and weight display"
```

---

### Task 10: Final Cleanup and Integration Verification

**Files:**
- Delete: `web/src/App.css` (unused Vite default)
- Delete: `web/src/assets/react.svg` (unused Vite default)
- Modify: `web/index.html` (update title)
- Modify: `docs/progress.md`

- [ ] **Step 1: Clean up Vite defaults**

```bash
rm -f web/src/App.css web/src/assets/react.svg
```

- [ ] **Step 2: Update HTML title**

In `web/index.html`, change `<title>Vite + React + TS</title>` to:

```html
<title>AI 绩效评估系统</title>
```

- [ ] **Step 3: Verify TypeScript compiles cleanly**

```bash
cd web && npx tsc --noEmit
```

Expected: No errors.

- [ ] **Step 4: Verify dev server runs**

```bash
cd web && npm run dev
```

Expected: Vite starts, all pages render without console errors.

- [ ] **Step 5: Update progress.md**

Update `docs/progress.md` to reflect Phase 6 completion:
- Phase 6 status → 完成
- 下一步 → Phase 7 Docker 部署

- [ ] **Step 6: Commit**

```bash
git add web/ docs/progress.md
git commit -m "feat: complete Phase 6 React frontend — 5 core pages with charts"
```
