import React from "react";
import { PodcastClip } from "../../remotion-app/src/compositions/podcast-clip";
import type { TemplateProps } from "../../../registry/types";

export const PodcastClipWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <PodcastClip title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
