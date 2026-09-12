import React from "react";
import { TemplateWrapper } from "./TemplateWrapper";
import type { StyleSurface } from "../contracts/StyleSurface";
import { resolveBrandToken } from "./brand-resolver";
import { useBrand } from "../contracts/brand";

export interface LogoAssembleProps {
  surface: StyleSurface;
}

/**
 * قالب تجميع الشعار (Logo Assemble)
 * يعتمد على BrandProvider للحصول على الشعار الافتراضي إن لم يُحدد.
 */
export const LogoAssemble: React.FC<LogoAssembleProps> = ({ surface }) => {
  const brand = useBrand();

  return (
    <TemplateWrapper surface={surface}>
      {({ opacity, position, animation, styleOverride }) => {
        // إذا لم يكن هناك شعار مخصص في الـ surface، استخدم شعار الهوية
        const rawLogo = surface.logoSrc || "brand.logo";
        const finalLogo = resolveBrandToken(rawLogo, brand);

        if (!finalLogo) {
          return null; // لا يوجد شعار لعرضه
        }

        return (
          <div
            style={{
              ...position,
              opacity,
              // تطبيق الحركة (مثلاً zoom)
              transform: `${position.transform || ""} scale(${animation.progress})`,
              ...styleOverride,
            }}
          >
            <img 
              src={finalLogo} 
              alt="Logo" 
              style={{
                maxWidth: surface.width || 200,
                maxHeight: surface.height || 200,
                objectFit: "contain"
              }} 
            />
          </div>
        );
      }}
    </TemplateWrapper>
  );
};
