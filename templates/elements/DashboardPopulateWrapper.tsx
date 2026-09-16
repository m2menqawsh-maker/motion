import React from "react";
import { DashboardPopulate } from "@/compositions/dashboard-populate";
import type { TemplateProps } from "@registry/types";

export const DashboardPopulateWrapper = ({ surface, content, ...rest }: any) => {
  const template_props = rest.template_props || {};
  const customMetrics = [
    {
      label: content?.lines?.[0] || "المستخدمين النشطين",
      value: content?.numbers?.[0] || 12400,
      delta: content?.lines?.[2] || "+18%",
      trend: [8.2, 9.1, 9.6, 10.4, 11.2, 11.9, 12.4],
    },
    {
      label: content?.lines?.[1] || "الإيرادات",
      value: content?.numbers?.[1] || 34800,
      delta: content?.lines?.[3] || "+9%",
      trend: [96, 104, 101, 112, 118, 124, 128],
    }
  ];

  return (
    <div style={{ direction: "rtl", width: "100%", height: "100%" }}>
      <DashboardPopulate  {...template_props} 
         metricsTitle={surface?.text || "لوحة القيادة"}
         chartTitle={surface?.subtext || "نظرة عامة"}
         backgroundColor={surface?.background || undefined}
         metrics={customMetrics}
      />
    </div>
  );
};
