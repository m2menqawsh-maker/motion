/**
 * عقد المواضع (Positions)
 * يحسب الموضع بناءً على الارتكاز (Anchor) والإزاحة
 */

import type { Position } from "./StyleSurface";
import type { CSSProperties } from "react";

/**
 * تحويل الارتكاز والإزاحة إلى خصائص CSS للموضع
 * @param p الموضع والإزاحة
 * @param canvas أبعاد مساحة العمل
 * @returns خصائص CSS جاهزة للحقن
 */
export function usePosition(
  p: Position | undefined,
  canvas?: { w: number; h: number } // Added as optional since some users might not pass it directly or might not need canvas dimensions for CSS translate approach
): CSSProperties {
  if (!p) return {};

  const { anchor, x = 0, y = 0 } = p;
  
  // باستخدام CSS المطلق والتحويل (Transform) لضمان المركزية
  // تعتبر هذه الطريقة فعالة في Remotion دون الاعتماد على الأبعاد الثابتة للـ canvas هنا
  let top = "auto";
  let left = "auto";
  let bottom = "auto";
  let right = "auto";
  let transform = `translate(${x}px, ${y}px)`;

  switch (anchor) {
    case "top-left":
      top = "0%";
      left = "0%";
      break;
    case "top-center":
      top = "0%";
      left = "50%";
      transform = `translate(calc(-50% + ${x}px), ${y}px)`;
      break;
    case "top-right":
      top = "0%";
      right = "0%";
      break;
    case "center-left":
      top = "50%";
      left = "0%";
      transform = `translate(${x}px, calc(-50% + ${y}px))`;
      break;
    case "center":
      top = "50%";
      left = "50%";
      transform = `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`;
      break;
    case "center-right":
      top = "50%";
      right = "0%";
      transform = `translate(${x}px, calc(-50% + ${y}px))`;
      break;
    case "bottom-left":
      bottom = "0%";
      left = "0%";
      break;
    case "bottom-center":
      bottom = "0%";
      left = "50%";
      transform = `translate(calc(-50% + ${x}px), ${y}px)`;
      break;
    case "bottom-right":
      bottom = "0%";
      right = "0%";
      break;
  }

  const style: CSSProperties = { position: "absolute", transform };
  if (top !== "auto") style.top = top;
  if (left !== "auto") style.left = left;
  if (bottom !== "auto") style.bottom = bottom;
  if (right !== "auto") style.right = right;

  return style;
}
