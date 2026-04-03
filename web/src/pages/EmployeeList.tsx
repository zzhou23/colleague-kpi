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
