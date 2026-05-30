export const API = import.meta.env.VITE_API_URL;

export const STATUS_CONFIG = {
  starting: { label: "STARTING", color: "#71717a", bg: "rgba(113,113,122,0.12)" },
  researching: { label: "RESEARCH", color: "#38bdf8", bg: "rgba(56,189,248,0.1)" },
  strategizing: { label: "STRATEGY", color: "#a78bfa", bg: "rgba(167,139,250,0.1)" },
  drafting: { label: "DRAFTING", color: "#94a3b8", bg: "rgba(148,163,184,0.12)" },
  awaiting_reply: { label: "AWAITING", color: "#fbbf24", bg: "rgba(251,191,36,0.1)" },
  won: { label: "WON", color: "#4ade80", bg: "rgba(74,222,128,0.1)" },
  closed_no_deal: { label: "CLOSED", color: "#f87171", bg: "rgba(248,113,113,0.1)" },
};

export const FILTER_TABS = [
  { id: "all", label: "All" },
  { id: "active", label: "Active" },
  { id: "won", label: "Won" },
  { id: "closed", label: "Closed" },
];

export const FILTER_PAGE_META = {
  all: {
    title: "Total processed",
    subtitle: "Complete registry of bill negotiations in the system.",
  },
  won: {
    title: "Deals won",
    subtitle: "Closed negotiations with a reduced monthly rate.",
  },
  active: {
    title: "Active negotiations",
    subtitle: "Pipeline items currently in progress.",
  },
  closed: {
    title: "Closed negotiations",
    subtitle: "Sessions ended without a rate reduction.",
  },
};

export const SORT_OPTIONS = [
  { id: "newest", label: "Newest first" },
  { id: "savings", label: "Highest savings" },
  { id: "amount", label: "Bill amount" },
  { id: "provider", label: "Provider A–Z" },
];

export const NAV_ITEMS = [
  { id: "dashboard", label: "Overview" },
  { id: "negotiations", label: "Negotiations" },
  { id: "upload", label: "New bill" },
  { id: "settings", label: "Settings" },
];

export const STEP_CODES = {
  research: "RSH",
  strategy: "STR",
  email_draft: "EML",
  reply_received: "RPL",
  closed: "CLS",
};

export const STEP_LABELS = {
  research: "Market Research",
  strategy: "Strategy Built",
  email_draft: "Email Drafted",
  reply_received: "Reply Analyzed",
  closed: "Negotiation Closed",
};
