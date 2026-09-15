import React from "react";
import { Showcase } from "../../remotion-app/src/compositions/showcase";
import type { TemplateProps } from "../../../registry/types";

export const ShowcaseWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <Showcase  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
