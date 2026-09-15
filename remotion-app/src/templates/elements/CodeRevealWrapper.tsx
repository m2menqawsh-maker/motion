import React from "react";
import { CodeReveal } from "../../remotion-app/src/remotion/scenes/code-reveal";
import type { TemplateProps } from "../../../registry/types";

export const CodeRevealWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CodeReveal  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
