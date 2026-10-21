import React from "react";
import { HookCard } from "@/remotion/scenes/hook-card";
import type { TemplateProps } from "@registry/types";

export const HookCardWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <HookCard  {...template_props} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
