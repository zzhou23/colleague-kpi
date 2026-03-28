# Phase 6: React Frontend Design

## Overview

Web management dashboard for the AI Performance Review system. 5 core pages providing company-wide analytics, employee scoring details, and system management.

## Tech Stack

| Layer | Choice | Reason |
|-------|--------|--------|
| Framework | React 18 + TypeScript | Type safety, ecosystem |
| Build | Vite | Fast dev experience |
| UI Components | Ant Design 5 | Enterprise-grade, rich components |
| Charts | ECharts + echarts-for-react | Best radar/heatmap/line support |
| Routing | React Router v6 | Standard React routing |
| HTTP | Axios | Interceptors, clean API |
| Language | Code in English, UI in Chinese | Maintainable code, user-friendly UI |
| Auth | None (MVP) | Internal deployment, add later |

## New Backend Endpoints Required

Before building the frontend, add these aggregation endpoints:

### `GET /api/dashboard/summary?year_month=YYYY-MM`

Response:
```json
{
  "total_employees": 50,
  "avg_score": 72.5,
  "max_score": 95.0,
  "min_score": 35.0,
  "grade_distribution": {"S": 5, "A": 12, "B": 18, "C": 10, "D": 5}
}
```

### `GET /api/dashboard/rankings?year_month=YYYY-MM&order=top&limit=10`

Response:
```json
[
  {"employee_id": 1, "name": "Alice", "department": "Engineering", "total_score": 95.0, "grade": "S"}
]
```

### Extend `GET /api/employees`

Add optional `year_month` query param. When provided, include latest report data (total_score, grade) in response for list sorting/display.

## Pages

### 1. Dashboard (`/`)

- **Top row**: 4 Ant Design Statistic cards (total employees, avg score, highest score, lowest score)
- **Middle left**: ECharts pie chart showing S/A/B/C/D grade distribution with colors (S=gold, A=green, B=blue, C=orange, D=red)
- **Middle right**: Top 10 / Bottom 10 toggle, Ant Design Table with rank, name, department, score, grade tag
- **Controls**: MonthPicker at top to switch data period
- **Data source**: `/api/dashboard/summary`, `/api/dashboard/rankings`

### 2. Employee List (`/employees`)

- **Table columns**: Name, Department, Total Score, Grade (colored Tag), Trend arrow (up/down/flat vs last month)
- **Filters**: Department dropdown (Select), search input (Input.Search)
- **Sorting**: All columns sortable via Ant Design Table sorter
- **Action**: Click row navigates to `/employees/:id`
- **Data source**: Extended `GET /api/employees?year_month=`

### 3. Employee Detail (`/employees/:id`)

- **Header**: Card with name, email, department, role, current grade (large colored badge)
- **Left**: Five-dimension radar chart (Activity, Quality, Configuration, Efficiency, Resource)
- **Right**: Horizontal bar chart grouped by category, showing each dimension's score (0-100)
- **Bottom**: 6-month trend line chart (total score + 5 category lines, different colors)
- **Controls**: MonthPicker for radar/bar data; trend chart always shows latest 6 months
- **Data source**: `GET /api/employees/{id}`, `GET /api/employees/{id}/scores`, `GET /api/employees/{id}/reports`

### 4. Monthly Reports (`/reports`)

- **Controls**: MonthPicker
- **Summary row**: Avg score, grade distribution mini-chart
- **Main table**: All employees with scores and grades, sortable
- **Grade changes**: Comparison with previous month (upgrade/downgrade indicators)
- **Export**: CSV download button (PDF deferred to later phase)
- **Data source**: `/api/dashboard/summary`, `/api/dashboard/rankings?limit=0` (all employees)

### 5. System Settings (`/settings`)

- **Tab 1 - Employee Management**:
  - Ant Design Table with CRUD operations
  - "Add Employee" button opens Modal with form (name, email, department, role)
  - On create success: display generated API Key in a copyable Alert (shown only once)
  - Delete with Popconfirm
- **Tab 2 - Scoring Weights**:
  - Read-only display of current dimension weights by category
  - Ant Design Descriptions or Table showing category name, weight percentage, dimensions
- **Data source**: `GET/POST /api/employees`

## Shared Components

| Component | Purpose |
|-----------|---------|
| `GradeTag` | Colored Ant Design Tag for S/A/B/C/D grades |
| `RadarChart` | Five-dimension radar chart wrapper |
| `TrendLine` | Multi-line trend chart for score history |
| `MonthPicker` | Ant Design DatePicker in month mode with controlled state |

## Project Structure

```
web/src/
├── main.tsx                 # Entry point
├── App.tsx                  # Router + Ant Layout (Sider + Content)
├── api/
│   ├── client.ts            # Axios instance (baseURL: /api)
│   ├── dashboard.ts         # Dashboard aggregation APIs
│   ├── employees.ts         # Employee CRUD APIs
│   └── scores.ts            # Score and report APIs
├── pages/
│   ├── Dashboard.tsx
│   ├── EmployeeList.tsx
│   ├── EmployeeDetail.tsx
│   ├── Reports.tsx
│   └── Settings.tsx
├── components/
│   ├── GradeTag.tsx
│   ├── RadarChart.tsx
│   ├── TrendLine.tsx
│   └── MonthPicker.tsx
└── types/
    └── index.ts             # Shared TypeScript interfaces
```

## Layout

Ant Design Pro-style layout:
- **Sider** (left): Logo + Menu with 5 navigation items (icons + Chinese labels)
- **Content** (right): Page content with top padding
- **Responsive**: Sider collapses on small screens

## Implementation Order

1. Backend: Add dashboard aggregation endpoints + extend employees endpoint
2. Vite project init + install dependencies
3. Router + Layout skeleton
4. API layer + TypeScript types
5. Pages in order: Dashboard -> Employee List -> Employee Detail -> Reports -> Settings

## Grade Color Mapping

| Grade | Color | Ant Design Tag Color |
|-------|-------|---------------------|
| S | Gold | `gold` |
| A | Green | `green` |
| B | Blue | `blue` |
| C | Orange | `orange` |
| D | Red | `red` |

## API Base URL

Development: Vite proxy `/api` -> `http://localhost:8000/api` (configured in `vite.config.ts`)

Production: Served behind reverse proxy (nginx in Docker), same origin.
