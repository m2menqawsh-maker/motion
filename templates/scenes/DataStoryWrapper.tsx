import React from "react";
import { DataStory } from "../../remotion-app/src/compositions/data-story";
import type { TemplateProps } from "../../../registry/types";

export const DataStoryWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <DataStory title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
