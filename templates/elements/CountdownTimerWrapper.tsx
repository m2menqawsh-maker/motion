import React from "react";
import { CountdownTimer } from "../../remotion-app/src/remotion/scenes/countdown-timer";
import type { TemplateProps } from "../../../registry/types";

export const CountdownTimerWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <CountdownTimer label={content?.text || undefined} />
  );
};
