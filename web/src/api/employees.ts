import client from "./client";
import type { Employee, EmployeeCreateResponse } from "../types";

export async function fetchEmployees(): Promise<Employee[]> {
  const { data } = await client.get<Employee[]>("/employees");
  return data;
}

export async function fetchEmployee(id: number): Promise<Employee> {
  const { data } = await client.get<Employee>(`/employees/${id}`);
  return data;
}

export async function createEmployee(body: {
  name: string;
  email: string;
  department: string;
  role?: string;
}): Promise<EmployeeCreateResponse> {
  const { data } = await client.post<EmployeeCreateResponse>("/employees", body);
  return data;
}
