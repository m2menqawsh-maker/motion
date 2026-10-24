import React from "react";
import { SplitScreen } from "@/remotion/scenes/split-screen";
import type { TemplateProps } from "@registry/types";

const DEFAULT_PANEL = {
  src: "data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHdpZHRoPSIxIiBoZWlnaHQ9IjEiPjwvc3ZnPg==",
  label: "",
};

export const SplitScreenWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const left = template_props.left || DEFAULT_PANEL;
  const right = template_props.right || DEFAULT_PANEL;
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
      <SplitScreen left={left} right={right} {...template_props} title={content?.text || undefined} />
    </div>
  );
};
