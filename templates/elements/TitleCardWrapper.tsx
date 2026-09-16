import React from "react";
import { TitleCard } from "@/remotion/scenes/title-card";
import type { TemplateProps } from "@registry/types";

export const TitleCardWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <TitleCard  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
