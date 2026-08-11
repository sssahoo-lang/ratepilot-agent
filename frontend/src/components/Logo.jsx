import React from "react";

export const BRAND_NAME = "RatePilot";
export const BRAND_TAGLINE = "AI Bill Negotiation";

export function Logo({ size = 32 }) {
  return (
    <svg
      width={size}
      height={size}
      viewBox="0 0 32 32"
      fill="none"
      xmlns="http://www.w3.org/2000/svg"
      aria-hidden
      className="logo-mark"
    >
      <rect x="0.5" y="0.5" width="31" height="31" rx="6" stroke="currentColor" strokeOpacity="0.35" />
      <path
        d="M8 22V12L16 8L24 12V22"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <path
        d="M12 22V16H20V22"
        stroke="currentColor"
        strokeWidth="1.5"
        strokeLinejoin="round"
      />
      <circle cx="16" cy="13" r="1.5" fill="currentColor" />
    </svg>
  );
}

export function NavIcon({ name }) {
  const stroke = { stroke: "currentColor", strokeWidth: 1.5, fill: "none" };
  const paths = {
    dashboard: (
      <>
        <rect x="3" y="3" width="8" height="8" rx="1" {...stroke} />
        <rect x="13" y="3" width="8" height="8" rx="1" {...stroke} />
        <rect x="3" y="13" width="8" height="8" rx="1" {...stroke} />
        <rect x="13" y="13" width="8" height="8" rx="1" {...stroke} />
      </>
    ),
    negotiations: (
      <path d="M4 7h16M4 12h16M4 17h10" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
    ),
    upload: (
      <path d="M12 16V8M12 8L9 11M12 8L15 11M6 18h12" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" fill="none" />
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" {...stroke} />
        <path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M17 7l-1.4 1.4M7 17l-1.4 1.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </>
    ),
  };
  return (
    <svg className="nav-icon-svg" width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden>
      {paths[name] || paths.dashboard}
    </svg>
  );
}
