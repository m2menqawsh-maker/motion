import React from "react";
import { PricingFocus } from "../../remotion-app/src/compositions/pricing-focus";
import type { TemplateProps } from "../../../registry/types";

export const PricingFocusWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <PricingFocus  {...template_props}  />
  </div>
  );
};
