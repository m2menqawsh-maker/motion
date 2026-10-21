import React from "react";
import { TitleCard } from "@/remotion/scenes/title-card";
import type { TemplateProps } from "@registry/types";

export const TitleCardWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const title = content?.text || content?.title || template_props?.title || surface?.text || "العنوان";
  const subtitle = content?.subtitle || content?.lines?.[0] || template_props?.subtitle || surface?.subtitle;
  const bg = surface?.backgroundColor || template_props?.backgroundColor || "#1a2238";
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
      <TitleCard {...template_props} backgroundColor={bg} title={title} subtitle={subtitle} />
    </div>
  );
};
