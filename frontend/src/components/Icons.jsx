import React from 'react';

const shapes = {
  refresh: <><path d="M20 7v5h-5M4 17v-5h5" /><path d="M6.2 7a7 7 0 0 1 11.6-1L20 9M4 15l2.2 3A7 7 0 0 0 18 17" /></>,
  arrow: <path d="M4 12h16m-6-6 6 6-6 6" />,
  external: <path d="M8 5H5v14h14v-3M12 4h8v8M10 14 20 4" />,
  search: <><circle cx="10.5" cy="10.5" r="6.5" /><path d="m16 16 4 4" /></>,
  heart: <path d="M20.8 4.6a5.5 5.5 0 0 0-7.8 0L12 5.7l-1.1-1.1a5.5 5.5 0 0 0-7.8 7.8L12 21l8.8-8.6a5.5 5.5 0 0 0 0-7.8Z" />,
  close: <path d="m6 6 12 12M6 18 18 6" />,
  down: <path d="m6 9 6 6 6-6" />,
  plus: <path d="M12 4v16M4 12h16" />,
  check: <path d="m5 12 4 4L19 6" />,
  filter: <><path d="M4 7h16M4 17h16" /><circle cx="9" cy="7" r="3" /><circle cx="16" cy="17" r="3" /></>,
  pin: <><path d="M20 10c0 6-8 12-8 12S4 16 4 10a8 8 0 1 1 16 0Z" /><circle cx="12" cy="10" r="2.5" /></>,
  clock: <><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></>,
  laptop: <path d="M5 4h14v12H5zM2 19h20" />,
  user: <><circle cx="12" cy="8" r="4" /><path d="M4 21a8 8 0 0 1 16 0" /></>,
  settings: <><path d="m9 3-1 3-3 1-2 5 2 5 3 1 1 3h6l1-3 3-1 2-5-2-5-3-1-1-3Z" /><circle cx="12" cy="12" r="3" /></>,
  bell: <path d="M18 8a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" />,
  eye: <><path d="M2 12s4-7 10-7 10 7 10 7-4 7-10 7S2 12 2 12Z" /><circle cx="12" cy="12" r="3" /></>,
  share: <path d="M12 15V2m-4 4 4-4 4 4M5 11v10h14V11" />,
  flag: <path d="M5 22V3c5-4 9 4 15 0v11c-6 4-10-4-15 0" />,
  grid: <><rect x="3" y="3" width="7" height="7" rx="2" /><rect x="14" y="3" width="7" height="7" rx="2" /><rect x="3" y="14" width="7" height="7" rx="2" /><rect x="14" y="14" width="7" height="7" rx="2" /></>,
  spark: <path d="m12 2 2.6 7.4L22 12l-7.4 2.6L12 22l-2.6-7.4L2 12l7.4-2.6Z" />,
  logout: <path d="M10 4H4v16h6M10 12h12m-4-4 4 4-4 4" />,
  shield: <><path d="m12 2 8 4v6c0 6-8 10-8 10S4 18 4 12V6Z" /><path d="m8 12 3 3 5-6" /></>,
  help: <><circle cx="12" cy="12" r="9" /><path d="M9 8.5a3 3 0 1 1 4 2.8c-1 .4-1 1.2-1 2.2M12 17h.01" /></>,
};
export function Icon({name, className = ''}) {
  return <svg className={`icon ${className}`} viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">{shapes[name] || shapes.spark}</svg>;
}
export function Logo() {
  return <><span className="brand-symbol" aria-hidden="true"><svg viewBox="0 0 32 32" fill="none"><path d="M7 25V7l18 18V7M17 7h8v8" stroke="currentColor" strokeWidth="2.3" strokeLinecap="round" strokeLinejoin="round" /></svg></span><span>Future Now<span className="brand-dot">.</span></span></>;
}
