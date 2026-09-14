import React from "react";
import { TeamGrid } from "../../remotion-app/src/remotion/scenes/team-grid";
import type { TemplateProps } from "../../../registry/types";

export const TeamGridWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <TeamGrid title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
