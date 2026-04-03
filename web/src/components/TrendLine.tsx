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
