import React from "react";
import { MetricTicker } from "@/remotion/scenes/metric-ticker";
import type { TemplateProps } from "@registry/types";

export const MetricTickerWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <MetricTicker  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
