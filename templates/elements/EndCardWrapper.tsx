import React from "react";
import { EndCard } from "../../remotion-app/src/remotion/scenes/end-card";
import type { TemplateProps } from "../../../registry/types";

export const EndCardWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <EndCard title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} url={content?.lines?.[1] || undefined} />
  );
};
