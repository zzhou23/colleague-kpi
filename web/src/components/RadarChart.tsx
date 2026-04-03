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
