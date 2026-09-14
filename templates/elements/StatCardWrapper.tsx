import React from "react";
import { StatCard } from "../../remotion-app/src/remotion/scenes/stat-card";
import type { TemplateProps } from "../../../registry/types";

export const StatCardWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <StatCard label={content?.text || undefined} />
  );
};
