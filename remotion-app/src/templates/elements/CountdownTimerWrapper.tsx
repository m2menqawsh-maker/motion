import React from "react";
import { CountdownTimer } from "../../remotion-app/src/remotion/scenes/countdown-timer";
import type { TemplateProps } from "../../../registry/types";

export const CountdownTimerWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <CountdownTimer  {...template_props} label={content?.text || undefined} />
  </div>
  );
};
