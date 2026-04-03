import { useEffect, useState } from "react";
import { Tabs, Table, Button, Modal, Form, Input, Select, Alert, Spin, message } from "antd";
import { PlusOutlined, CopyOutlined } from "@ant-design/icons";
import type { ColumnsType } from "antd/es/table";
import { fetchEmployees, createEmployee } from "../api/employees";
import { CATEGORY_LABELS, CATEGORY_WEIGHTS } from "../types";
import type { Employee } from "../types";

function Settings() {
  const [employees, setEmployees] = useState<Employee[]>([]);
  const [loading, setLoading] = useState(false);
  const [modalOpen, setModalOpen] = useState(false);
  const [newApiKey, setNewApiKey] = useState<string | null>(null);
  const [form] = Form.useForm();

  const loadEmployees = () => {
    setLoading(true);
    fetchEmployees()
      .then(setEmployees)
      .catch(() => message.error("加载失败"))
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadEmployees();
  }, []);

  const handleCreate = async () => {
    const values = await form.validateFields();
    const result = await createEmployee(values);
    setNewApiKey(result.api_key);
    setModalOpen(false);
    form.resetFields();
    loadEmployees();
    message.success("员工创建成功");
  };

  const copyKey = () => {
    if (newApiKey) {
      navigator.clipboard.writeText(newApiKey);
      message.success("已复制到剪贴板");
    }
  };

  const empColumns: ColumnsType<Employee> = [
    { title: "ID", dataIndex: "id", width: 60 },
    { title: "姓名", dataIndex: "name" },
    { title: "邮箱", dataIndex: "email" },
    { title: "部门", dataIndex: "department" },
    { title: "角色", dataIndex: "role" },
  ];

  const weightData = Object.entries(CATEGORY_LABELS).map(([key, label]) => ({
    key,
    category: label,
    weight: `${(CATEGORY_WEIGHTS[key] * 100).toFixed(0)}%`,
  }));

  const weightColumns = [
    { title: "类别", dataIndex: "category" },
    { title: "英文标识", dataIndex: "key" },
    { title: "权重", dataIndex: "weight" },
  ];

  return (
    <Spin spinning={loading}>
      <h2 style={{ marginBottom: 16 }}>系统管理</h2>

      {newApiKey && (
        <Alert
          message="API Key 已生成（仅显示一次）"
          description={
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <code style={{ fontSize: 14 }}>{newApiKey}</code>
              <Button icon={<CopyOutlined />} size="small" onClick={copyKey}>复制</Button>
            </div>
          }
          type="success"
          closable
          onClose={() => setNewApiKey(null)}
          style={{ marginBottom: 16 }}
        />
      )}

      <Tabs
        items={[
          {
            key: "employees",
            label: "员工管理",
            children: (
              <>
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => setModalOpen(true)}
                  style={{ marginBottom: 16 }}
                >
                  新增员工
                </Button>
                <Table dataSource={employees} columns={empColumns} rowKey="id" pagination={{ pageSize: 20 }} />
              </>
            ),
          },
          {
            key: "weights",
            label: "评分权重",
            children: (
              <Table dataSource={weightData} columns={weightColumns} rowKey="key" pagination={false} />
            ),
          },
        ]}
      />

      <Modal
        title="新增员工"
        open={modalOpen}
        onOk={handleCreate}
        onCancel={() => setModalOpen(false)}
        okText="创建"
        cancelText="取消"
      >
        <Form form={form} layout="vertical">
          <Form.Item name="name" label="姓名" rules={[{ required: true, message: "请输入姓名" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="email" label="邮箱" rules={[{ required: true, type: "email", message: "请输入有效邮箱" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="department" label="部门" rules={[{ required: true, message: "请输入部门" }]}>
            <Input />
          </Form.Item>
          <Form.Item name="role" label="角色" initialValue="employee">
            <Select options={[{ label: "员工", value: "employee" }, { label: "管理员", value: "admin" }]} />
          </Form.Item>
        </Form>
      </Modal>
    </Spin>
  );
}

export default Settings;
