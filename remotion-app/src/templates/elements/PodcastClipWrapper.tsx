import React from "react";
import { PodcastClip } from "../../remotion-app/src/compositions/podcast-clip";
import type { TemplateProps } from "../../../registry/types";

export const PodcastClipWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <PodcastClip  {...template_props} title={content?.text || undefined} subtitle={content?.lines?.[0] || undefined} />
  </div>
  );
};
