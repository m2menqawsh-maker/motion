import React from "react";
import { OrgChartBuild } from "../../remotion-app/src/remotion/scenes/org-chart-build";
import type { TemplateProps } from "../../../registry/types";

export const OrgChartBuildWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <OrgChartBuild title={content?.text || undefined} />
  );
};
