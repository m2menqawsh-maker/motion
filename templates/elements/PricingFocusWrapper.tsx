import React from "react";
import { PricingFocus } from "../../remotion-app/src/compositions/pricing-focus";
import type { TemplateProps } from "../../../registry/types";

export const PricingFocusWrapper: React.FC<TemplateProps> = ({ surface, content }) => {
  return (
    <PricingFocus  />
  );
};
