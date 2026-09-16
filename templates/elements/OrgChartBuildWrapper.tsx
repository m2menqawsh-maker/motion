import React from "react";
import { OrgChartBuild } from "@/remotion/scenes/org-chart-build";
import type { TemplateProps } from "@registry/types";

export const OrgChartBuildWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <OrgChartBuild  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
