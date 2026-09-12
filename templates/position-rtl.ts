/**
 * عقد المواضع (Positions) مع دعم RTL
 * يحسب الموضع بناءً على الارتكاز والإزاحة، ويعكس الإزاحة الأفقية في وضع RTL.
 */

import React from "react";
import type { Position } from "../contracts/StyleSurface";

/**
 * تحويل الارتكاز والإزاحة إلى خصائص CSS للموضع (يدعم RTL)
 * @param p الموضع والإزاحة
 * @param canvas أبعاد مساحة العمل
 * @param rtl هل الاتجاه من اليمين لليسار؟
 * @returns خصائص CSS جاهزة
 */
export function usePosition(
  p: Position | undefined,
  canvas: { w: number; h: number },
  rtl?: boolean
): React.CSSProperties {
  if (!p) return {};
  
  const { anchor, x = 0, y = 0 } = p;
  
  // عكس x في RTL إذا كان الموضع على اليمين أو اليسار
  const effectiveX = rtl && (anchor.includes("right") || anchor.includes("left")) ? -x : x;
  
  let top = "auto";
  let left = "auto";
  let bottom = "auto";
  let right = "auto";
  let transform = `translate(${effectiveX}px, ${y}px)`;

  switch (anchor) {
    case "top-left":
      top = "0%"; left = "0%"; break;
    case "top-center":
      top = "0%"; left = "50%"; transform = `translate(calc(-50% + ${effectiveX}px), ${y}px)`; break;
    case "top-right":
      top = "0%"; right = "0%"; break;
    case "center-left":
      top = "50%"; left = "0%"; transform = `translate(${effectiveX}px, calc(-50% + ${y}px))`; break;
    case "center":
      top = "50%"; left = "50%"; transform = `translate(calc(-50% + ${effectiveX}px), calc(-50% + ${y}px))`; break;
    case "center-right":
      top = "50%"; right = "0%"; transform = `translate(${effectiveX}px, calc(-50% + ${y}px))`; break;
    case "bottom-left":
      bottom = "0%"; left = "0%"; break;
    case "bottom-center":
      bottom = "0%"; left = "50%"; transform = `translate(calc(-50% + ${effectiveX}px), ${y}px)`; break;
    case "bottom-right":
      bottom = "0%"; right = "0%"; break;
  }

  const style: React.CSSProperties = { position: "absolute", transform };
  if (top !== "auto") style.top = top;
  if (left !== "auto") style.left = left;
  if (bottom !== "auto") style.bottom = bottom;
  if (right !== "auto") style.right = right;

  return style;
}
