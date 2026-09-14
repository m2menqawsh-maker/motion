import React from "react";
import { BRollStack } from "../../remotion-app/src/remotion/scenes/b-roll-stack";
import type { TemplateProps } from "../../../registry/types";

export const BRollStackWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <BRollStack items={content?.items ? content.items.map(i => ({title: i})) : undefined} title={content?.text || undefined} />
  );
};
