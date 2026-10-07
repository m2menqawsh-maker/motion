/**
 * remotion-app/src/BrandContext.tsx — React Brand Context & Provider for Remotion Runtime.
 * Decoupled from contracts layer in S28-R02.
 */
import React, { createContext, useContext } from "react";
import type { BrandKit } from "../../contracts/brand";

export type { BrandKit } from "../../contracts/brand";

/** سياق العلامة التجارية */
export const BrandContext = createContext<BrandKit | null>(null);

/**
 * المزود الذي يمرر الهوية البصرية لكامل المشروع
 */
export const BrandProvider = ({
  brand,
  children,
}: {
  brand: BrandKit;
  children: React.ReactNode;
}) => {
  return React.createElement(BrandContext.Provider, { value: brand }, children);
};

/**
 * خطاف للوصول إلى الهوية البصرية الحالية
 */
export function useBrand(): BrandKit {
  const ctx = useContext(BrandContext);
  if (!ctx) {
    throw new Error("useBrand must be used within a BrandProvider");
  }
  return ctx;
}
