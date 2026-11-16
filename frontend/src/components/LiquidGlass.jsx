// Shared refraction for every modal backdrop and the account pop-up.
export function LiquidGlass() {
  return <svg className="liquid-glass-defs" width="0" height="0" aria-hidden="true" focusable="false">
    <defs>
      <filter id="fn-glass-refraction" x="-4%" y="-4%" width="108%" height="108%" colorInterpolationFilters="sRGB">
        <feTurbulence type="fractalNoise" baseFrequency="0.008 0.012" numOctaves="1" seed="7" stitchTiles="stitch" result="glass-noise"/>
        <feGaussianBlur in="glass-noise" stdDeviation="2" result="glass-flow"/>
        <feDisplacementMap in="SourceGraphic" in2="glass-flow" scale="16" xChannelSelector="R" yChannelSelector="G"/>
      </filter>
    </defs>
  </svg>;
}
