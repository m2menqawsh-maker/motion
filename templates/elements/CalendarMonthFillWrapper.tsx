import React from "react";
import { CalendarMonthFill } from "../../remotion-app/src/remotion/scenes/calendar-month-fill";
import type { TemplateProps } from "../../../registry/types";

export const CalendarMonthFillWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CalendarMonthFill  />
  );
};
