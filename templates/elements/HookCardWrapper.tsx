import React from "react";
import { HookCard } from "../../remotion-app/src/remotion/scenes/hook-card";
import type { TemplateProps } from "../../../registry/types";

export const HookCardWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <HookCard subtitle={content?.lines?.[0] || undefined} />
  );
};
