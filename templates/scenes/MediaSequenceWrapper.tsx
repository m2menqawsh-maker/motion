import React from "react";
import { MediaSequence } from "../../remotion-app/src/remotion/scenes/media-sequence";
import type { TemplateProps } from "../../../registry/types";

export const MediaSequenceWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <MediaSequence items={content?.items ? content.items.map(i => ({title: i})) : undefined} />
  );
};
