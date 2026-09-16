import React from "react";
import { CalendarMonthFill } from "@/remotion/scenes/calendar-month-fill";
import type { TemplateProps } from "@registry/types";

export const CalendarMonthFillWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CalendarMonthFill  {...template_props}  />
  </div>
  );
};
