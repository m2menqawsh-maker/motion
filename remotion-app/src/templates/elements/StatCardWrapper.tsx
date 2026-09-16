import React from "react";
import { StatCard } from "@/remotion/scenes/stat-card";
import type { TemplateProps } from "@registry/types";

export const StatCardWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
      <StatCard  {...template_props} 
        label={content?.lines?.[0] || surface?.text || "إحصائية"} 
        caption={content?.lines?.[1] || surface?.subtext || undefined}
        value={content?.numbers?.[0] || 98}
        max={content?.numbers?.[1] || undefined}
        backgroundColor={surface?.background}
        accentColor={surface?.color}
      />
    </div>
  );
};
