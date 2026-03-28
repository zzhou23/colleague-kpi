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
