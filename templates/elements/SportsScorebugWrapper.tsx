import React from "react";
import { SportsScorebug } from "../../remotion-app/src/remotion/scenes/sports-scorebug";
import type { TemplateProps } from "../../../registry/types";

export const SportsScorebugWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <SportsScorebug  />
  );
};
