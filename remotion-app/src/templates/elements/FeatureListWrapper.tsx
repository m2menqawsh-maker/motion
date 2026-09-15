import React from "react";
import { FeatureList } from "../../remotion-app/src/remotion/scenes/feature-list";
import type { TemplateProps } from "../../../registry/types";

export const FeatureListWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <FeatureList  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
