import { DatePicker } from "antd";
import dayjs, { type Dayjs } from "dayjs";

interface MonthPickerProps {
  value: string; // "YYYY-MM"
  onChange: (value: string) => void;
}

function MonthPicker({ value, onChange }: MonthPickerProps) {
  return (
    <DatePicker
      picker="month"
      value={dayjs(value, "YYYY-MM")}
      onChange={(date: Dayjs | null) => {
        if (date) {
          onChange(date.format("YYYY-MM"));
        }
      }}
      allowClear={false}
    />
  );
}

export default MonthPicker;
