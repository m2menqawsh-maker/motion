import React from "react";
import { MetricTicker } from "../../remotion-app/src/remotion/scenes/metric-ticker";
import type { TemplateProps } from "../../../registry/types";

export const MetricTickerWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <MetricTicker title={content?.text || undefined} />
  );
};
