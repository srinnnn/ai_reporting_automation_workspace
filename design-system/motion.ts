export const durationFast = 150;
export const durationNormal = 190;
export const durationPanel = 200;
export const durationDrawer = 240;
export const durationChartEnterMin = 300;
export const durationChartEnterMax = 500;

export const easeOut = "ease-out";
export const cardHoverTransform = "translateY(-2px)";
export const arrowHoverTransform = "translateX(3px)";

export const motionTokens = {
  durationFast,
  durationNormal,
  durationPanel,
  durationDrawer,
  durationChartEnterMin,
  durationChartEnterMax,
  easeOut,
  cardHoverTransform,
  arrowHoverTransform,
} as const;

export const reducedMotionCss = `
@media (prefers-reduced-motion: reduce) {
  *,
  *::before,
  *::after {
    animation-duration: 1ms !important;
    animation-iteration-count: 1 !important;
    scroll-behavior: auto !important;
    transition-duration: 1ms !important;
  }
}
`;
