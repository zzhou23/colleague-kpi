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
