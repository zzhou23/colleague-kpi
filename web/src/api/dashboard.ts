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
