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
