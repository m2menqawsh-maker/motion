import React from "react";
import { PricingCard } from "../../remotion-app/src/remotion/scenes/pricing-card";
import type { TemplateProps } from "../../../registry/types";

export const PricingCardWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
    <PricingCard  {...template_props}  />
  </div>
  );
};
