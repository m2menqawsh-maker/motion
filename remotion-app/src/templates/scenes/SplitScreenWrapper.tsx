import React from "react";
import { SplitScreen } from "@/remotion/scenes/split-screen";
import type { TemplateProps } from "@registry/types";

export const SplitScreenWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <SplitScreen  {...template_props} title={content?.text || undefined} />
  </div>
  );
};
