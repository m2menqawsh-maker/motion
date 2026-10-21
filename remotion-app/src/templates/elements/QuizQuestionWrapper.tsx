import React from "react";
import { QuizQuestion } from "@/remotion/scenes/quiz-question";
import type { TemplateProps } from "@registry/types";

export const QuizQuestionWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <QuizQuestion  {...template_props}  />
  </div>
  );
};
