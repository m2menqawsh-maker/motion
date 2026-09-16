import React from "react";
import { BRollStack } from "@/remotion/scenes/b-roll-stack";
import type { TemplateProps } from "@registry/types";

export const BRollStackWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <BRollStack  {...template_props} items={content?.items ? content.items.map((i: any) => ({title: i})) : undefined} title={content?.text || undefined} />
  </div>
  );
};
