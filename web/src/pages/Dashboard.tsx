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
