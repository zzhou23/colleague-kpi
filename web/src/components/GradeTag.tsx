import { Tag } from "antd";
import { GRADE_COLORS, type Grade } from "../types";

interface GradeTagProps {
  grade: string;
}

function GradeTag({ grade }: GradeTagProps) {
  const color = GRADE_COLORS[grade as Grade] ?? "default";
  return <Tag color={color}>{grade}</Tag>;
}

export default GradeTag;
