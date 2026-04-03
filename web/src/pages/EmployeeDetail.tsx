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

          <Card title={`趋势（最近 6 个月）`}>
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
