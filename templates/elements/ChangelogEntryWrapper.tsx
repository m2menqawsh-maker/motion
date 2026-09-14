import React from "react";
import { ChangelogEntry } from "../../remotion-app/src/remotion/scenes/changelog-entry";
import type { TemplateProps } from "../../../registry/types";

export const ChangelogEntryWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <ChangelogEntry  />
  );
};
