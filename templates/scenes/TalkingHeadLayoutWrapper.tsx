import React from "react";
import { TalkingHeadLayout } from "../../remotion-app/src/remotion/scenes/talking-head-layout";
import type { TemplateProps } from "../../../registry/types";

export const TalkingHeadLayoutWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <TalkingHeadLayout title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  );
};
