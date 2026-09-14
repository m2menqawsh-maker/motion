import React from "react";
import { KanbanMove } from "../../remotion-app/src/remotion/scenes/kanban-move";
import type { TemplateProps } from "../../../registry/types";

export const KanbanMoveWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <KanbanMove  />
  );
};
