import React from "react";
import { BrowserFlow } from "@/compositions/browser-flow";
import type { TemplateProps } from "@registry/types";

export const BrowserFlowWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <BrowserFlow  {...template_props} url={content?.lines?.[1] || undefined} title={content?.text || undefined} />
  </div>
  );
};
