import React from "react";
import { NotificationStack } from "../../remotion-app/src/remotion/scenes/notification-stack";
import type { TemplateProps } from "../../../registry/types";

export const NotificationStackWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <NotificationStack  />
  );
};
