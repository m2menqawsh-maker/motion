import React from "react";
import { TitleCard } from "../../remotion-app/src/remotion/scenes/title-card";
import type { TemplateProps } from "../../../registry/types";

export const TitleCardWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <TitleCard title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
