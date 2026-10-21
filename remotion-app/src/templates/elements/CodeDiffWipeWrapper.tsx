import React from "react";
import { CodeDiffWipe } from "@/remotion/scenes/code-diff-wipe";
import type { TemplateProps } from "@registry/types";

export const CodeDiffWipeWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CodeDiffWipe  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
