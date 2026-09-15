import React from "react";
import { AutoFitTitle } from "../../remotion-app/src/remotion/scenes/auto-fit-title";
import type { TemplateProps } from "../../../registry/types";

export const AutoFitTitleWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <AutoFitTitle  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
