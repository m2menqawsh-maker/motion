import React from "react";
import { MetricTicker } from "@/remotion/scenes/metric-ticker";
import type { TemplateProps } from "@registry/types";

const DEFAULT_METRICS = [
  { label: "Performance", value: 99.9, suffix: "%" },
  { label: "Throughput", value: 120, suffix: "x" },
  { label: "Reliability", value: 100, suffix: "%" },
];

export const MetricTickerWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const metrics = template_props.metrics || content?.metrics || DEFAULT_METRICS;
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
      <MetricTicker {...template_props} metrics={metrics} title={content?.text || undefined} />
    </div>
  );
};
