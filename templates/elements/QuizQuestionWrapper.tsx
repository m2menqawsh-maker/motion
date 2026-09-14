import React from "react";
import { QuizQuestion } from "../../remotion-app/src/remotion/scenes/quiz-question";
import type { TemplateProps } from "../../../registry/types";

export const QuizQuestionWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <QuizQuestion  />
  );
};
