import React, { useState, useEffect, useCallback, useMemo, useRef } from "react";
import { createPortal } from "react-dom";
import jsPDF from "jspdf";
import { Logo, NavIcon, BRAND_NAME, BRAND_TAGLINE } from "./components/Logo.jsx";
import {
  API,
  STATUS_CONFIG,
  FILTER_TABS,
  FILTER_PAGE_META,
  SORT_OPTIONS,
  NAV_ITEMS,
  STEP_CODES,
  STEP_LABELS,
} from "./constants.js";
import { getMonthlySavings, getBestOfferSavings } from "./utils/savings.js";

function exportNegotiationPDF(negotiation) {
  const doc = new jsPDF({ orientation: "portrait", unit: "mm", format: "a4" });
  const margin = 20;
  const maxWidth = 170;
  const bottomY = 270;
  const lineHeight = 6;
  let y = margin;

  const asObject = (value) => {
    if (!value) return {};
    if (typeof value === "object") return value;
    try { return JSON.parse(value); } catch { return {}; }
  };
  const asText = (value) => typeof value === "string" ? value : "";
  const money = (value) => value == null || value === "" ? "—" : "$" + Number(value).toFixed(2);
  const plainMoney = (value) => "$" + (Number(value) || 0).toFixed(2);
  const titleCase = (value) => String(value || "").replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
  const research = asObject(negotiation.research_findings);
  const strategy = asObject(negotiation.strategy);
  const strategyText = asText(negotiation.strategy);
  const steps = negotiation.steps || [];
  const firstEmail = steps.find((step) => step.step_type === "email_draft");
  const emailContent = firstEmail?.content && typeof firstEmail.content === "object" ? firstEmail.content : asObject(firstEmail?.content);
  const monthlySavings = Math.max(getMonthlySavings(negotiation), getBestOfferSavings(negotiation));
  const providerSlug = (negotiation.provider || "provider").toLowerCase().replace(/[^a-z0-9]+/g, "-").replace(/^-|-$/g, "");

  const ensureSpace = (needed = lineHeight) => {
    if (y + needed > bottomY) {
      doc.addPage();
      y = margin;
    }
  };
  const writeLines = (text, options = {}) => {
    const {
      size = 10,
      style = "normal",
      color = [35, 35, 35],
      indent = 0,
      gapAfter = 0,
    } = options;
    doc.setFont("helvetica", style);
    doc.setFontSize(size);
    doc.setTextColor(...color);
    const lines = doc.splitTextToSize(String(text || "—"), maxWidth - indent);
    lines.forEach((line) => {
      ensureSpace(lineHeight);
      doc.text(line, margin + indent, y);
      y += lineHeight;
    });
    y += gapAfter;
  };
  const section = (label) => {
    y += 6;
    ensureSpace(8);
    doc.setFont("helvetica", "bold");
    doc.setFontSize(11);
    doc.setTextColor(20, 20, 20);
    doc.text(label, margin, y);
    y += 7;
  };
  const bulletList = (items) => {
    (items || []).slice(0, 4).forEach((item) => writeLines("• " + item, { indent: 3 }));
  };

  doc.setFont("helvetica", "bold");
  doc.setFontSize(18);
  doc.setTextColor(20, 20, 20);
  doc.text("BillFight — Negotiation Summary", margin, y);
  y += 9;
  doc.setFont("helvetica", "normal");
  doc.setFontSize(12);
  doc.setTextColor(100, 100, 100);
  doc.text(`${negotiation.provider || "Unknown Provider"} — ${titleCase(negotiation.bill_type || "bill")}`, margin, y);
  y += 7;
  doc.setFontSize(10);
  doc.text("Date: " + new Date(negotiation.created_at || Date.now()).toLocaleDateString(), margin, y);
  y += 5;
  doc.setDrawColor(200, 200, 200);
  doc.line(margin, y, margin + maxWidth, y);

  section("Original Bill");
  writeLines("Original monthly amount: " + money(negotiation.current_amount) + " / month");
  writeLines("Target price: " + money(negotiation.target_price) + " / month");
  writeLines("Walkaway threshold: " + money(negotiation.walkaway_threshold) + " / month");

  section("Market Research");
  writeLines(research.research_summary || "No market research summary available.");
  (research.competitor_prices || []).slice(0, 3).forEach((item) => {
    writeLines(`${item.provider || "Competitor"}: ${money(item.price)} / month${item.plan ? " — " + item.plan : ""}`);
  });
  writeLines("Market average price: " + money(research.market_average) + " / month");
  bulletList(research.leverage_points || []);

  section("Negotiation Strategy");
  if (strategyText && Object.keys(strategy).length === 0) {
    writeLines(strategyText);
  } else {
    const opening = strategy.opening_position || strategy.opening_ask || strategy.primary_leverage || strategy.strategy_summary;
    writeLines(opening || "No strategy summary available.");
    bulletList(strategy.key_arguments || strategy.leverage_points || strategy.key_phrases || []);
  }

  section("Negotiation Email Sent");
  if (emailContent?.subject) writeLines("Subject: " + emailContent.subject, { style: "bold" });
  const emailBody = emailContent?.body ? (emailContent.body.length > 800 ? emailContent.body.slice(0, 800) + "..." : emailContent.body) : "No email draft found.";
  writeLines(emailBody);

  section("Outcome");
  const outcome = negotiation.status === "won" ? "Won" : negotiation.status === "closed_no_deal" ? "No Deal" : "In Progress";
  writeLines("Status: " + outcome);
  if (negotiation.best_offer_received != null) writeLines("Best offer received: " + money(negotiation.best_offer_received) + " / month");
  writeLines("Monthly savings: " + plainMoney(monthlySavings) + " saved per month");
  writeLines("Annual savings: " + plainMoney(monthlySavings * 12) + " saved per year");
  writeLines("Rounds of negotiation: " + (negotiation.rounds_count || steps.filter((step) => step.step_type === "email_draft").length || 0) + " rounds");
  if (negotiation.status === "won") writeLines("✓ Successfully negotiated a lower rate", { style: "bold", color: [40, 140, 80] });

  const today = new Date().toLocaleDateString();
  const pages = doc.getNumberOfPages();
  for (let page = 1; page <= pages; page += 1) {
    doc.setPage(page);
    doc.setFont("helvetica", "normal");
    doc.setFontSize(8);
    doc.setTextColor(120, 120, 120);
    doc.text(`Generated by BillFight • billfight.app • ${today}`, margin, 287);
  }

  doc.save(`billfight-${providerSlug}-${negotiation.id}.pdf`);
}

function providerInitials(name) {
  if (!name) return "?";
  const words = name.trim().split(/\s+/);
  if (words.length >= 2) return (words[0][0] + words[1][0]).toUpperCase();
  return name.slice(0, 2).toUpperCase();
}

function StatusBadge({ status }) {
  const cfg = STATUS_CONFIG[status] || STATUS_CONFIG.starting;
  return (
    <span className="status-badge" style={{ background: cfg.bg, color: cfg.color }}>
      {cfg.label}
    </span>
  );
}

function useToast() {
  const [toast, setToast] = useState(null);
  const show = (msg, type = "info") => {
    setToast({ message: msg, type });
    setTimeout(() => setToast(null), 2800);
  };
  return { toast, show };
}

function ActionMenu({ items, onClose, anchorRect }) {
  const ref = useRef(null);
  const [position, setPosition] = useState(null);

  useEffect(() => {
    const handler = (e) => {
      if (ref.current && !ref.current.contains(e.target)) onClose();
    };
    document.addEventListener("mousedown", handler);
    return () => document.removeEventListener("mousedown", handler);
  }, [onClose]);

  useEffect(() => {
    if (!anchorRect) return;
    const menuHeight = items.length * 38 + 16;
    const menuWidth = 200;
    const gap = 6;
    let top = anchorRect.bottom + gap;
    let left = anchorRect.right - menuWidth;

    if (top + menuHeight > window.innerHeight - 12) {
      top = anchorRect.top - menuHeight - gap;
    }
    if (left < 12) left = 12;
    if (left + menuWidth > window.innerWidth - 12) {
      left = window.innerWidth - menuWidth - 12;
    }
    setPosition({ top, left, width: menuWidth });
  }, [anchorRect, items.length]);

  if (!anchorRect || !position) return null;

  return createPortal(
    <div
      className="dropdown dropdown-portal"
      ref={ref}
      style={{
        position: "fixed",
        top: position.top,
        left: position.left,
        minWidth: position.width,
        zIndex: 10000,
      }}
    >
      {items.map((item) => (
        <button
          key={item.label}
          type="button"
          className={item.danger ? "danger" : ""}
          onClick={() => { item.onClick(); onClose(); }}
        >
          {item.label}
        </button>
      ))}
    </div>,
    document.body
  );
}

function pctOf(part, total) {
  if (!total || total <= 0) return 0;
  return Math.round((part / total) * 100);
}

function StatCard({ label, value, sub, pct, barClass, accent, onClick }) {
  const className = "stat-card" + (accent ? " stat-card-accent" : "") + (onClick ? " stat-card-clickable" : "");
  const inner = (
    <>
      <p className="stat-label">{label}</p>
      <p className={"stat-value mono" + (accent ? " accent" : "")}>{value}</p>
      {sub && <p className="stat-sub">{sub}</p>}
      {pct != null && pct > 0 && (
        <div className="stat-bar-wrap">
          <div className="stat-bar">
            <div className={"stat-bar-fill " + (barClass || "")} style={{ width: pct + "%" }} />
          </div>
          <span className="stat-pct mono">{pct}%</span>
        </div>
      )}
      {pct === 0 && sub && <span className="stat-pct mono stat-pct-zero">0%</span>}
      {onClick && <p className="stat-hint">View breakdown</p>}
    </>
  );
  if (onClick) {
    return (
      <button type="button" className={className} onClick={onClick}>
        {inner}
      </button>
    );
  }
  return <div className={className}>{inner}</div>;
}

function PipelineBreakdown({ total, won, active, closed, totalSavings }) {
  if (total === 0) {
    return (
      <div className="pipeline-panel pipeline-panel-empty">
        <p className="mono">No negotiation data yet — upload a bill to populate metrics.</p>
      </div>
    );
  }

  const wonPct = pctOf(won, total);
  const activePct = pctOf(active, total);
  const closedPct = pctOf(closed, total);
  const winRate = wonPct;
  const avgSavingsPerWon = won > 0 ? totalSavings / won : 0;

  return (
    <div className="pipeline-panel">
      <div className="pipeline-header">
        <div>
          <h3>Pipeline breakdown</h3>
          <p>{total} negotiations · figures as % of total volume</p>
        </div>
        <div className="pipeline-summary mono">
          <span className="pipeline-summary-label">Win rate</span>
          <span className="pipeline-summary-value">{winRate}%</span>
        </div>
      </div>
      <div className="pipeline-bar" role="img" aria-label={"Won " + wonPct + "%, Active " + activePct + "%, Closed " + closedPct + "%"}>
        {won > 0 && <div className="pipeline-seg pipeline-seg-won" style={{ width: wonPct + "%" }} title={"Won " + won + " (" + wonPct + "%)"} />}
        {active > 0 && <div className="pipeline-seg pipeline-seg-active" style={{ width: activePct + "%" }} title={"Active " + active + " (" + activePct + "%)"} />}
        {closed > 0 && <div className="pipeline-seg pipeline-seg-closed" style={{ width: closedPct + "%" }} title={"Closed " + closed + " (" + closedPct + "%)"} />}
      </div>
      <div className="pipeline-legend">
        <div className="pipeline-legend-item">
          <span className="pipeline-dot pipeline-dot-won" />
          <span>Won</span>
          <strong className="mono">{won}</strong>
          <span className="mono pipeline-pct">{wonPct}%</span>
        </div>
        <div className="pipeline-legend-item">
          <span className="pipeline-dot pipeline-dot-active" />
          <span>Active</span>
          <strong className="mono">{active}</strong>
          <span className="mono pipeline-pct">{activePct}%</span>
        </div>
        <div className="pipeline-legend-item">
          <span className="pipeline-dot pipeline-dot-closed" />
          <span>Closed</span>
          <strong className="mono">{closed}</strong>
          <span className="mono pipeline-pct">{closedPct}%</span>
        </div>
      </div>
      <div className="pipeline-figures">
        <div className="pipeline-figure">
          <span className="pipeline-figure-label">Total volume</span>
          <span className="pipeline-figure-value mono">{total}</span>
        </div>
        <div className="pipeline-figure">
          <span className="pipeline-figure-label">Win rate</span>
          <span className="pipeline-figure-value mono">{winRate}%</span>
        </div>
        <div className="pipeline-figure">
          <span className="pipeline-figure-label">Avg savings / won deal</span>
          <span className="pipeline-figure-value mono">
            {won > 0 ? "$" + avgSavingsPerWon.toFixed(0) + "/mo" : "—"}
          </span>
        </div>
        <div className="pipeline-figure">
          <span className="pipeline-figure-label">Active share</span>
          <span className="pipeline-figure-value mono">{activePct}%</span>
        </div>
      </div>
    </div>
  );
}

function SavingsOverview({ negotiations }) {
  if (negotiations.length === 0) {
    return (
      <section className="savings-overview">
        <div className="page-header savings-overview-header">
          <h2 style={{ fontSize: 16 }}>Savings Overview</h2>
        </div>
        <div className="savings-empty mono">No negotiations yet — upload a bill to start saving</div>
      </section>
    );
  }

  const wonNegotiations = negotiations.filter((n) => n.status === "won");
  const monthlySavings = wonNegotiations.reduce((sum, n) => sum + (Number(n.savings_achieved) || 0), 0);
  const annualSavings = monthlySavings * 12;
  const winRate = negotiations.length > 0 ? (wonNegotiations.length / negotiations.length) * 100 : 0;
  const winRateLabel = winRate.toFixed(0) + "%";
  const avgSavings = wonNegotiations.length > 0 ? monthlySavings / wonNegotiations.length : null;
  const sortedRows = [...negotiations].sort((a, b) => (Number(b.savings_achieved) || 0) - (Number(a.savings_achieved) || 0));
  const fmtMoney = (n) => "$" + (Number(n) || 0).toFixed(0);

  return (
    <section className="savings-overview">
      <div className="page-header savings-overview-header">
        <h2 style={{ fontSize: 16 }}>Savings Overview</h2>
      </div>
      <div className="savings-grid">
        <div className="savings-hero">
          <p className="stat-label">Total savings</p>
          <p className="savings-hero-value mono">{fmtMoney(monthlySavings)}</p>
          <p className="savings-hero-label">saved per month</p>
          <div className="savings-annual">
            <span className="mono">{fmtMoney(annualSavings)}</span>
            <small>projected annual savings</small>
          </div>
        </div>
        <div className={"savings-mini-card " + (winRate >= 50 ? "positive" : "warning")}>
          <p className="stat-label">Success Rate</p>
          <p className="savings-mini-value mono">{wonNegotiations.length} / {negotiations.length}</p>
          <p className="savings-mini-sub mono">{winRateLabel}</p>
        </div>
        <div className="savings-mini-card">
          <p className="stat-label">Avg monthly savings per win</p>
          <p className="savings-mini-value mono">{avgSavings == null ? "—" : fmtMoney(avgSavings)}</p>
        </div>
      </div>
      <div className="savings-table-wrap">
        <table className="savings-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Original Bill</th>
              <th>Best Offer</th>
              <th>Monthly Saved</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {sortedRows.map((n) => {
              const savings = Number(n.savings_achieved) || 0;
              const isActive = !["won", "closed_no_deal"].includes(n.status);
              return (
                <tr key={n.id}>
                  <td>{n.provider || "Unknown"}</td>
                  <td className="mono">{fmtMoney(n.current_amount)}</td>
                  <td className="mono">{n.best_offer_received == null ? "—" : fmtMoney(n.best_offer_received)}</td>
                  <td className={"mono " + (n.status === "won" ? "savings-positive" : isActive ? "savings-warning" : "savings-muted")}>
                    {n.status === "won" ? "−" + fmtMoney(savings) : isActive ? "In Progress" : "—"}
                  </td>
                  <td><StatusBadge status={n.status} /></td>
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

function PageBackButton({ onClick, label }) {
  return (
    <button type="button" className="btn-back" onClick={onClick} aria-label={"Back to " + label}>
      <span className="btn-back-icon">←</span>
      <span>{label}</span>
    </button>
  );
}

function AppShell({ view, onNavigate, children, breadcrumbs, topbarExtra, totalSavings, showBack, onBack, backLabel }) {
  return (
    <div className="app-layout">
      <aside className="sidebar">
        <div className="sidebar-brand">
          <div className="logo-wrap">
            <Logo size={28} />
          </div>
          <div>
            <h1>{BRAND_NAME}</h1>
            <span>{BRAND_TAGLINE}</span>
          </div>
        </div>
        <nav className="sidebar-nav">
          <p className="nav-section-label">Platform</p>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.id}
              type="button"
              className={`nav-item ${view === item.id || (view === "detail" && item.id === "negotiations") ? "active" : ""}`}
              onClick={() => onNavigate(item.id)}
            >
              <NavIcon name={item.id} />
              {item.label}
            </button>
          ))}
        </nav>
        <div className="sidebar-footer">
          <div className="sidebar-stat">
            <p className="sidebar-stat-label">Lifetime savings</p>
            <p className="sidebar-stat-value mono">${totalSavings.toFixed(0)}<span className="unit">/mo</span></p>
          </div>
          <p className="sidebar-version">Engine v1.0</p>
        </div>
      </aside>
      <div className="main-area">
        <header className="topbar">
          {showBack && onBack && <PageBackButton onClick={onBack} label={backLabel} />}
          <div className="breadcrumbs">{breadcrumbs}</div>
          <div className="topbar-spacer" />
          {topbarExtra}
        </header>
        <main className="page-content">{children}</main>
      </div>
    </div>
  );
}

function StepCard({ step, onCopyEmail, emailAction }) {
  const [expanded, setExpanded] = useState(false);
  const content = typeof step.content === "object" ? step.content : {};

  return (
    <div className="step-item">
      <div className="step-marker mono">{STEP_CODES[step.step_type] || "LOG"}</div>
      <div className="step-content">
        <h4>{STEP_LABELS[step.step_type] || step.step_type}</h4>
        <span className="step-time">{new Date(step.created_at).toLocaleString()}</span>
        {step.reasoning && <p className="step-body-text">{step.reasoning}</p>}
        {step.decision && (
          <p className="step-body-text" style={{ color: "var(--accent)", fontWeight: 600 }}>
            → {step.decision}
          </p>
        )}
        {step.step_type === "email_draft" && content.body && (
          <div style={{ marginTop: 8 }}>
            <button type="button" className="btn btn-secondary btn-sm" onClick={() => setExpanded(!expanded)}>
              {expanded ? "Hide" : "View email"}
            </button>
            {expanded && (
              <div className="email-preview">
                <strong>Subject:</strong> {content.subject}
                {"\n\n"}
                {content.body}
              </div>
            )}
            <button
              type="button"
              className="btn btn-ghost btn-sm"
              style={{ marginLeft: 6 }}
              onClick={() => onCopyEmail(content)}
            >
              Copy email
            </button>
            {emailAction}
          </div>
        )}
        {step.step_type === "research" && content.competitor_prices?.slice(0, 3).map((c, i) => (
          <span key={i} className="chip">{c.provider}: ${c.price}/mo</span>
        ))}
      </div>
    </div>
  );
}

function NegotiationDetail({ negotiation, onBack, onRefresh, onRestart, onDelete, onRetry, onSendEmail, showToast }) {
  const [replyText, setReplyText] = useState("");
  const [sending, setSending] = useState(false);
  const [msg, setMsg] = useState("");
  const [tab, setTab] = useState("activity");
  const [restarting, setRestarting] = useState(false);
  const [deleting, setDeleting] = useState(false);
  const [retrying, setRetrying] = useState(false);
  const [emailSending, setEmailSending] = useState(false);
  const [manualEmailPrompt, setManualEmailPrompt] = useState(false);
  const [manualEmail, setManualEmail] = useState("");
  const [emailError, setEmailError] = useState("");

  const steps = negotiation.steps || [];
  const savings = getMonthlySavings(negotiation);
  const lastEmail = steps.filter((s) => s.step_type === "email_draft").slice(-1)[0];
  const emailContent = lastEmail?.content && typeof lastEmail.content === "object" ? lastEmail.content : null;
  const hasEmailSent = steps.some((s) => s.step_type === "email_sent");
  const canSendEmail = ["awaiting_reply", "drafting"].includes(negotiation.status) && lastEmail && !hasEmailSent;

  const exportTranscript = () => {
    exportNegotiationPDF(negotiation);
    showToast("PDF summary exported");
  };

  const copySummary = () => {
    const text = [
      `${negotiation.provider} — ${negotiation.bill_type}`,
      `Status: ${STATUS_CONFIG[negotiation.status]?.label || negotiation.status}`,
      `Original: $${negotiation.current_amount}/mo`,
      negotiation.target_price ? `Target: $${negotiation.target_price}/mo` : null,
      savings > 0 ? `Saved: $${savings.toFixed(0)}/mo` : null,
    ].filter(Boolean).join("\n");
    navigator.clipboard.writeText(text);
    showToast("Summary copied");
  };

  const handleSimulateReply = async () => {
    if (!replyText.trim()) return;
    setSending(true);
    setMsg("");
    try {
      const r = await fetch(`${API}/agent/simulate-reply`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ negotiation_id: negotiation.id, reply_text: replyText }),
      });
      const data = await r.json();
      setMsg(`Agent: ${data.decision}`);
      setReplyText("");
      setTimeout(onRefresh, 1000);
      showToast("Reply processed");
    } catch {
      setMsg("Failed to send");
    }
    setSending(false);
  };

  const handleRestart = async () => {
    if (!negotiation.bill_id) return;
    setRestarting(true);
    try {
      await onRestart(negotiation.bill_id);
      showToast("New negotiation started");
    } catch {
      showToast("Could not restart");
    }
    setRestarting(false);
  };

  const handleDelete = async () => {
    if (!window.confirm("Delete this negotiation? This cannot be undone.")) return;
    setDeleting(true);
    try {
      await onDelete(negotiation.id);
    } catch {
      showToast("Could not delete");
      setDeleting(false);
    }
  };

  const handleRetry = async () => {
    if (!onRetry || retrying) return;
    setRetrying(true);
    try {
      await onRetry(negotiation.id);
      showToast("Negotiation restarted", "success");
    } catch (err) {
      showToast(err.message || "Could not retry negotiation", "error");
    }
    setRetrying(false);
  };

  const handleSendEmailClick = async (emailAddress) => {
    if (!onSendEmail || emailSending) return;
    setEmailSending(true);
    setEmailError("");
    const result = await onSendEmail(negotiation.id, negotiation.provider, emailAddress);
    setEmailSending(false);
    if (result?.needsEmail) {
      setManualEmailPrompt(true);
      return;
    }
    if (result?.sent) {
      setManualEmailPrompt(false);
      setManualEmail("");
      return;
    }
    if (result?.error) setEmailError(result.error);
  };

  const handleManualEmailSubmit = (e) => {
    e.preventDefault();
    if (!manualEmail.trim()) {
      setEmailError("Enter the provider email address");
      return;
    }
    handleSendEmailClick(manualEmail);
  };

  return (
    <>
      <div className="detail-layout">
        <aside className="detail-sidebar">
          <div className="table-provider" style={{ marginBottom: 12 }}>
            <div className="avatar">{providerInitials(negotiation.provider)}</div>
            <div>
              <h3>{negotiation.provider}</h3>
              <p className="detail-meta">{negotiation.bill_type}</p>
            </div>
          </div>
          <StatusBadge status={negotiation.status} />
          <div className="detail-stats" style={{ marginTop: 16 }}>
            <div className="detail-stat-row"><span>Original</span><span>${negotiation.current_amount}/mo</span></div>
            <div className="detail-stat-row"><span>Target</span><span>{negotiation.target_price ? `$${negotiation.target_price}/mo` : "—"}</span></div>
            <div className="detail-stat-row"><span>Savings</span><span className="mono" style={{ color: "var(--success)" }}>{savings > 0 ? "$" + savings.toFixed(0) + "/mo" : "—"}</span></div>
            <div className="detail-stat-row"><span>Rounds</span><span>{steps.filter((s) => s.step_type === "email_draft").length}</span></div>
            <div className="detail-stat-row"><span>File</span><span>{negotiation.filename || "—"}</span></div>
          </div>
          <div className="detail-actions">
            {negotiation.status === "failed" && negotiation.error_message && (
              <div className="failure-panel">
                <strong>Pipeline failed</strong>
                <span>{negotiation.error_message}</span>
              </div>
            )}
            {negotiation.status === "failed" && (
              <button type="button" className="btn btn-secondary" onClick={handleRetry} disabled={retrying}>
                {retrying ? "Retrying..." : "Retry Negotiation"}
              </button>
            )}
            <button type="button" className="btn btn-secondary" onClick={exportTranscript}>Export PDF Summary</button>
            <button type="button" className="btn btn-secondary" onClick={copySummary}>Copy summary</button>
            {emailContent?.body && (
              <button
                type="button"
                className="btn btn-secondary"
                onClick={() => {
                  navigator.clipboard.writeText(`Subject: ${emailContent.subject}\n\n${emailContent.body}`);
                  showToast("Email copied");
                }}
              >
                Copy latest email
              </button>
            )}
            {negotiation.bill_id && (
              <button type="button" className="btn btn-secondary" onClick={handleRestart} disabled={restarting}>
                {restarting ? "Starting…" : "Restart negotiation"}
              </button>
            )}
            <button type="button" className="btn btn-secondary" onClick={handleDelete} disabled={deleting} style={{ color: "var(--rose)", borderColor: "var(--rose)" }}>
              {deleting ? "Deleting…" : "Delete negotiation"}
            </button>
            <button type="button" className="btn btn-ghost" onClick={onBack}>← Back to list</button>
          </div>
        </aside>
        <div className="detail-main">
          <div className="detail-tabs">
            <button type="button" className={`detail-tab ${tab === "activity" ? "active" : ""}`} onClick={() => setTab("activity")}>Activity</button>
            <button type="button" className={`detail-tab ${tab === "actions" ? "active" : ""}`} onClick={() => setTab("actions")}>Actions</button>
          </div>
          {tab === "activity" && (
            steps.length === 0 ? (
              <p style={{ color: "var(--text-muted)" }}>Agent is working…</p>
            ) : (
              <>
                <div className="timeline">
                  {steps.map((step) => (
                    <StepCard
                      key={step.id}
                      step={step}
                      onCopyEmail={(c) => {
                        navigator.clipboard.writeText(`Subject: ${c.subject}\n\n${c.body}`);
                        showToast("Email copied");
                      }}
                      emailAction={canSendEmail && step.id === lastEmail?.id ? (
                        <div className="email-send-panel">
                          <button
                            type="button"
                            className="btn btn-primary btn-sm"
                            onClick={() => handleSendEmailClick()}
                            disabled={emailSending}
                          >
                            {emailSending ? "Sending..." : "Send Email"}
                          </button>
                          {manualEmailPrompt && (
                            <form className="manual-email-form" onSubmit={handleManualEmailSubmit}>
                              <input
                                type="email"
                                value={manualEmail}
                                onChange={(e) => setManualEmail(e.target.value)}
                                placeholder="provider@example.com"
                                aria-label="Provider email address"
                              />
                              <button type="submit" className="btn btn-secondary btn-sm" disabled={emailSending}>
                                Confirm
                              </button>
                            </form>
                          )}
                          {emailError && <p className="email-send-error">{emailError}</p>}
                        </div>
                      ) : null}
                    />
                  ))}
                </div>
                {["won","closed_no_deal","awaiting_reply"].includes(negotiation.status) && (
                  <NegotiationOutcomeCard negotiation={negotiation} />
                )}
              </>
            )
          )}
          {tab === "actions" && (
            <div>
              <div style={{ display: "flex", flexWrap: "wrap", gap: 8, marginBottom: 16 }}>
                <button type="button" className="btn btn-secondary btn-sm" onClick={exportTranscript}>Export PDF Summary</button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={copySummary}>Copy summary</button>
                <button type="button" className="btn btn-secondary btn-sm" onClick={handleDelete} disabled={deleting} style={{ color: "var(--rose)" }}>
                  {deleting ? "Deleting…" : "Delete"}
                </button>
              </div>
              {negotiation.status === "awaiting_reply" ? (
                <div className="reply-panel">
                  <h4 style={{ margin: "0 0 4px" }}>Simulate company reply</h4>
                  <p style={{ margin: 0, fontSize: 12, color: "var(--text-muted)" }}>
                    Paste the provider's response for the agent to analyze.
                  </p>
                  <textarea
                    value={replyText}
                    onChange={(e) => setReplyText(e.target.value)}
                    placeholder='e.g. "We can offer $65/month for 12 months..."'
                  />
                  <div style={{ display: "flex", gap: 8, marginTop: 10, alignItems: "center" }}>
                    <button type="button" className="btn btn-primary" onClick={handleSimulateReply} disabled={sending || !replyText.trim()}>
                      {sending ? "Processing…" : "Send to agent"}
                    </button>
                    {msg && <span style={{ fontSize: 12, color: "var(--accent)" }}>{msg}</span>}
                  </div>
                </div>
              ) : (
                <p style={{ color: "var(--text-muted)", fontSize: 13 }}>
                  No actions available for status "{STATUS_CONFIG[negotiation.status]?.label}". Use Refresh to check for updates.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </>
  );
}

const ACCEPTED_UPLOAD_TYPES = new Set([
  "application/pdf",
  "text/plain",
  "image/jpeg",
  "image/png",
  "image/webp",
]);

function formatFileSize(size) {
  if (size >= 1024 * 1024) return (size / (1024 * 1024)).toFixed(1) + " MB";
  return Math.max(1, Math.round(size / 1024)) + " KB";
}

function getFileKind(file) {
  const name = file?.name?.toLowerCase() || "";
  if (file?.type?.startsWith("image/") || /\.(jpg|jpeg|png|webp)$/.test(name)) return "Image";
  if (file?.type === "application/pdf" || name.endsWith(".pdf")) return "PDF";
  return "Text";
}

function isAcceptedBillFile(file) {
  const name = file?.name?.toLowerCase() || "";
  return ACCEPTED_UPLOAD_TYPES.has(file?.type) || /\.(pdf|txt|jpg|jpeg|png|webp)$/.test(name);
}

function UploadView({ onDone, showToast }) {
  const [dragging, setDragging] = useState(false);
  const [uploading, setUploading] = useState(false);
  const [status, setStatus] = useState("");
  const [extracted, setExtracted] = useState(null);
  const [billId, setBillId] = useState(null);
  const [starting, setStarting] = useState(false);
  const [selectedFile, setSelectedFile] = useState(null);
  const [previewUrl, setPreviewUrl] = useState("");

  useEffect(() => {
    if (!selectedFile || getFileKind(selectedFile) !== "Image") {
      setPreviewUrl("");
      return;
    }
    const url = URL.createObjectURL(selectedFile);
    setPreviewUrl(url);
    return () => URL.revokeObjectURL(url);
  }, [selectedFile]);

  const selectFile = (file) => {
    if (!file) return;
    if (!isAcceptedBillFile(file)) {
      setStatus("Error: Supported formats are PDF, TXT, JPG, PNG, and WEBP");
      return;
    }
    setSelectedFile(file);
    setStatus("");
    setExtracted(null);
    setBillId(null);
  };

  const clearSelectedFile = () => {
    setSelectedFile(null);
    setPreviewUrl("");
    setStatus("");
    setExtracted(null);
    setBillId(null);
    const input = document.getElementById("file-input");
    if (input) input.value = "";
  };

  const uploadSelectedFile = async () => {
    if (!selectedFile) return;
    setUploading(true);
    setStatus("Uploading bill...");
    setExtracted(null);
    const timers = [
      setTimeout(() => setStatus("Reading bill contents..."), 1500),
      setTimeout(() => setStatus("Extracting details with AI..."), 3000),
    ];
    const form = new FormData();
    form.append("file", selectedFile);
    try {
      const r = await fetch(`${API}/bills/upload`, { method: "POST", body: form });
      const data = await r.json();
      if (data.bill_id) {
        setBillId(data.bill_id);
        setExtracted(data.extracted);
        setStatus("Ready to negotiate");
        showToast("Bill parsed");
      } else {
        setStatus("Error: " + (data.detail || "Could not parse"));
      }
    } catch {
      setStatus("Backend unavailable");
    }
    timers.forEach(clearTimeout);
    setUploading(false);
  };

  const startNegotiation = async () => {
    setStarting(true);
    try {
      const r = await fetch(`${API}/agent/start`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ bill_id: billId }),
      });
      const data = await r.json();
      if (data.negotiation_id) onDone(data.negotiation_id);
    } catch {
      setStatus("Failed to start agent");
    }
    setStarting(false);
  };

  const fileKind = selectedFile ? getFileKind(selectedFile) : "";

  return (
    <div className="upload-grid">
      <div>
        <div
          className={`dropzone ${dragging ? "dragging" : ""}`}
          onDragOver={(e) => { e.preventDefault(); setDragging(true); }}
          onDragLeave={() => setDragging(false)}
          onDrop={(e) => { e.preventDefault(); setDragging(false); selectFile(e.dataTransfer.files[0]); }}
          onClick={() => document.getElementById("file-input")?.click()}
          role="button"
          tabIndex={0}
        >
          <div className="dropzone-icon" aria-hidden />
          <p className="dropzone-title">Drop your bill here or click to browse</p>
          <p style={{ fontSize: 12, color: "var(--text-muted)", margin: 0 }}>PDF, TXT, JPG, PNG, and WEBP supported</p>
          <input id="file-input" type="file" accept=".pdf,.txt,.jpg,.jpeg,.png,.webp" hidden onChange={(e) => selectFile(e.target.files[0])} />
        </div>
        {selectedFile && (
          <div className="file-preview-card">
            {previewUrl ? <img src={previewUrl} alt="Selected bill preview" /> : <div className="file-preview-icon mono">{fileKind}</div>}
            <div className="file-preview-meta">
              <strong>{selectedFile.name}</strong>
              <span>{formatFileSize(selectedFile.size)} · {fileKind}</span>
            </div>
            <button type="button" className="file-preview-remove" onClick={clearSelectedFile} aria-label="Remove selected file">×</button>
          </div>
        )}
        {selectedFile && !extracted && (
          <button type="button" className="btn btn-primary upload-submit" onClick={uploadSelectedFile} disabled={uploading}>
            {uploading ? "Uploading..." : "Upload bill"}
          </button>
        )}
        {status && (
          <p style={{ marginTop: 12, fontSize: 13, color: status.includes("Error") || status.includes("Failed") ? "var(--rose)" : "var(--text-muted)" }}>
            {uploading ? "⏳ " : ""}{status}
          </p>
        )}
        {extracted && (
          <div className="extracted-panel">
            <p style={{ fontWeight: 600, margin: "0 0 10px" }}>Extracted details</p>
            <div className="extracted-grid">
              {[["Provider", extracted.provider], ["Type", extracted.bill_type], ["Amount", "$" + extracted.current_amount + "/mo"], ["Tenure", extracted.account_tenure]]
                .filter(([, v]) => v)
                .map(([k, v]) => (
                  <div key={k}><span style={{ color: "var(--text-muted)" }}>{k}: </span><strong>{v}</strong></div>
                ))}
            </div>
            <button type="button" className="btn btn-primary" style={{ width: "100%", marginTop: 14 }} onClick={startNegotiation} disabled={starting}>
              {starting ? "Launching…" : "Start negotiation"}
            </button>
          </div>
        )}
      </div>
      <div className="upload-tips">
        <h4>Supported bills</h4>
        <ul>
          <li>PDF bills (most providers)</li>
          <li>TXT plain text exports</li>
          <li>Photos of paper bills (JPG, PNG, WEBP)</li>
          <li>You can photograph a paper bill and upload the image</li>
        </ul>
        <h4 style={{ marginTop: 16 }}>What happens next</h4>
        <ul>
          <li>Agent researches competitor pricing</li>
          <li>Builds a negotiation strategy</li>
          <li>Drafts emails to your provider</li>
          <li>Responds when you paste replies</li>
        </ul>
      </div>
    </div>
  );
}

function buildMenuItems(n, { onOpen, onRestart, onRetry, onDelete, showToast }) {
  return [
    { label: "View details", onClick: () => onOpen(n.id) },
    {
      label: "Copy summary",
      onClick: () => {
        navigator.clipboard.writeText(n.provider + " · " + n.status + " · $" + n.current_amount + "/mo");
        showToast("Copied");
      },
    },
    {
      label: "Export JSON",
      onClick: () => {
        fetch(API + "/negotiations/" + n.id)
          .then((r) => r.json())
          .then((data) => {
            const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
            const a = document.createElement("a");
            a.href = URL.createObjectURL(blob);
            a.download = "negotiation-" + n.id + ".json";
            a.click();
            showToast("Exported");
          });
      },
    },
    ...(n.status === "failed" ? [{
      label: "Retry",
      onClick: () => onRetry(n.id)
        .then(() => showToast("Negotiation restarted", "success"))
        .catch((err) => showToast(err.message || "Could not retry negotiation", "error")),
    }] : []),
    ...(n.bill_id ? [{
      label: "Restart negotiation",
      onClick: () => onRestart(n.bill_id).then(() => showToast("Restarted")),
    }] : []),
    {
      label: "Delete",
      danger: true,
      onClick: () => {
        if (window.confirm("Delete this negotiation? This cannot be undone.")) {
          onDelete(n.id);
        }
      },
    },
  ];
}

function NegotiationsTable({ negotiations, loading, filter, sort, search, onOpen, onRefresh, onFilterChange, onSortChange, showToast, onRestart, onRetry, onDelete, compact }) {
  const [openMenuId, setOpenMenuId] = useState(null);
  const [menuAnchor, setMenuAnchor] = useState(null);

  const closeMenu = () => {
    setOpenMenuId(null);
    setMenuAnchor(null);
  };

  const openMenuFor = (n, buttonEl) => {
    if (openMenuId === n.id) {
      closeMenu();
      return;
    }
    setOpenMenuId(n.id);
    setMenuAnchor(buttonEl.getBoundingClientRect());
  };

  const menuNegotiation = openMenuId ? negotiations.find((n) => n.id === openMenuId) : null;

  const filtered = useMemo(() => {
    let list = [...negotiations];
    if (filter === "active") list = list.filter((n) => !["won", "closed_no_deal"].includes(n.status));
    else if (filter === "won") list = list.filter((n) => n.status === "won");
    else if (filter === "closed") list = list.filter((n) => n.status === "closed_no_deal");
    if (search.trim()) {
      const q = search.toLowerCase();
      list = list.filter((n) =>
        n.provider?.toLowerCase().includes(q) ||
        n.bill_type?.toLowerCase().includes(q) ||
        String(n.id).includes(q)
      );
    }
    if (sort === "savings") list.sort((a, b) => getMonthlySavings(b) - getMonthlySavings(a));
    else if (sort === "amount") list.sort((a, b) => (b.current_amount || 0) - (a.current_amount || 0));
    else if (sort === "provider") list.sort((a, b) => (a.provider || "").localeCompare(b.provider || ""));
    return list;
  }, [negotiations, filter, sort, search]);

  const exportAll = () => {
    const blob = new Blob([JSON.stringify(filtered, null, 2)], { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `ratepilot-negotiations-${Date.now()}.json`;
    a.click();
    showToast(`Exported ${filtered.length} negotiations`);
  };

  if (loading) {
    return <div className="table-panel" style={{ padding: 16 }}>{[1, 2, 3, 4].map((i) => <div key={i} className="skeleton-row" />)}</div>;
  }

  if (negotiations.length === 0) {
    return (
      <div className="empty-panel">
        <h3>No negotiations yet</h3>
        <p>Upload a bill to start your first automated negotiation.</p>
      </div>
    );
  }

  return (
    <>
      {!compact && (
        <div className="toolbar">
          <div className="filter-tabs">
            {FILTER_TABS.map((t) => (
              <button key={t.id} type="button" className={`filter-tab ${filter === t.id ? "active" : ""}`} onClick={() => onFilterChange(t.id)}>
                {t.label}
              </button>
            ))}
          </div>
          <select value={sort} onChange={(e) => onSortChange(e.target.value)}>
            {SORT_OPTIONS.map((o) => <option key={o.id} value={o.id}>{o.label}</option>)}
          </select>
          <button type="button" className="btn btn-secondary btn-sm" onClick={onRefresh}>Refresh</button>
          <button type="button" className="btn btn-secondary btn-sm" onClick={exportAll}>Export list</button>
        </div>
      )}
      <div className="table-panel">
        <table className="data-table">
          <thead>
            <tr>
              <th>Provider</th>
              <th>Status</th>
              <th>Bill</th>
              <th>Savings</th>
              <th style={{ textAlign: "right" }}>Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr><td colSpan={5} style={{ textAlign: "center", color: "var(--text-muted)" }}>No matches</td></tr>
            ) : filtered.map((n) => (
              <tr key={n.id}>
                <td>
                  <div className="table-provider">
                    <div className="avatar">{providerInitials(n.provider)}</div>
                    <div>
                      <strong>{n.provider}</strong>
                      <small>{n.bill_type} · #{n.id}</small>
                    </div>
                  </div>
                </td>
                <td><StatusBadge status={n.status} /></td>
                <td>
                  {"$" + n.current_amount + "/mo"}
                  {n.best_offer_received
                    ? <span style={{color:"#4ade80"}}> → ${Math.round(n.best_offer_received)}/mo</span>
                    : n.target_price ? " → $" + n.target_price : ""}
                </td>
                <td className={Math.max(getMonthlySavings(n), getBestOfferSavings(n)) > 0 ? "savings-cell" : ""}>
                  {Math.max(getMonthlySavings(n), getBestOfferSavings(n)) > 0
                    ? "−$" + Math.max(getMonthlySavings(n), getBestOfferSavings(n)).toFixed(0) + "/mo"
                    : "—"}
                </td>
                <td>
                  <div className="table-actions">
                    <button type="button" className="btn btn-secondary btn-sm" onClick={() => onOpen(n.id)}>View</button>
                    <div className="menu-wrap">
                      <button
                        type="button"
                        className={"menu-trigger" + (openMenuId === n.id ? " active" : "")}
                        onClick={(e) => { e.stopPropagation(); openMenuFor(n, e.currentTarget); }}
                        aria-expanded={openMenuId === n.id}
                        aria-haspopup="menu"
                      >
                        ⋯
                      </button>
                    </div>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {menuNegotiation && menuAnchor && (
        <ActionMenu
          anchorRect={menuAnchor}
          onClose={closeMenu}
          items={buildMenuItems(menuNegotiation, { onOpen, onRestart, onRetry, onDelete, showToast })}
        />
      )}
    </>
  );
}

function SettingsView({ theme, setTheme, autoRefresh, setAutoRefresh }) {
  return (
    <div className="settings-grid">
      <div className="setting-row">
        <div>
          <label>Appearance</label>
          <span>Switch between light and dark mode</span>
        </div>
        <button type="button" className={`toggle ${theme === "dark" ? "on" : ""}`} onClick={() => setTheme(theme === "dark" ? "light" : "dark")} aria-label="Toggle theme" />
      </div>
      <div className="setting-row">
        <div>
          <label>Auto-refresh active deals</label>
          <span>Poll every 3s while agent is working</span>
        </div>
        <button type="button" className={`toggle ${autoRefresh ? "on" : ""}`} onClick={() => setAutoRefresh(!autoRefresh)} aria-label="Toggle auto-refresh" />
      </div>
      <div className="setting-row">
        <div>
          <label>API endpoint</label>
          <span>{API}</span>
        </div>
      </div>
    </div>
  );
}

const BACK_LABELS = {
  dashboard: "Dashboard",
  negotiations: "Negotiations",
  upload: "New bill",
  settings: "Settings",
};


function OutcomeStat({ label, value, highlight }) {
  return (
    <div style={{
      background: highlight ? "rgba(74,222,128,0.07)" : "rgba(255,255,255,0.03)",
      border: "1px solid " + (highlight ? "rgba(74,222,128,0.18)" : "rgba(255,255,255,0.07)"),
      borderRadius: 8, padding: "10px 12px",
    }}>
      <div style={{ fontSize: 10, color: "var(--text-muted)", textTransform: "uppercase", letterSpacing: "0.06em", marginBottom: 4 }}>{label}</div>
      <div style={{ fontSize: 18, fontWeight: 700, color: highlight ? "#4ade80" : "var(--text-primary, #fff)", fontFamily: "monospace" }}>{value}</div>
    </div>
  );
}

function NegotiationOutcomeCard({ negotiation }) {
  const [copied, setCopied] = React.useState(false);
  const original = Number(negotiation.current_amount) || 0;
  const best = negotiation.best_offer_received != null ? Number(negotiation.best_offer_received) : null;
  const savings = Number(negotiation.savings_achieved) || 0;
  const dealClosed = negotiation.status === "won" && savings > 0;
  const hasOffer = best !== null;
  const savingsMonth = hasOffer ? Math.round(original - best) : 0;
  const savingsYear = savingsMonth * 12;
  const savingsPct = original > 0 && hasOffer ? Math.round((savingsMonth / original) * 100) : 0;
  const rounds = negotiation.rounds_count || 0;
  const statusMap = {
    won: { label: "Deal accepted", dot: "#4ade80" },
    closed_no_deal: { label: "Closed — no deal", dot: "#f87171" },
    awaiting_reply: { label: "Offer pending", dot: "#fbbf24" },
  };
  const sc = statusMap[negotiation.status] || { label: negotiation.status, dot: "#71717a" };
  const fmt = (n) => n != null ? "$" + Math.round(n).toLocaleString() : "—";
  const handleCopy = () => {
    const lines = [
      negotiation.provider + " — RatePilot Negotiation",
      "Original: " + fmt(original) + "/mo",
      hasOffer ? "Best offer: " + fmt(best) + "/mo" : "No offer received",
      hasOffer ? "Savings: " + fmt(savingsMonth) + "/mo · " + fmt(savingsYear) + "/yr (" + savingsPct + "% off)" : "",
      "Status: " + sc.label,
      "Rounds: " + rounds,
    ].filter(Boolean).join("\n");
    navigator.clipboard.writeText(lines);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };
  return (
    <div style={{ background: "rgba(255,255,255,0.04)", border: "1px solid rgba(255,255,255,0.1)", borderRadius: 12, padding: "18px 20px", marginTop: 24 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 14, flexWrap: "wrap", gap: 8 }}>
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 11, fontWeight: 600, letterSpacing: "0.08em", color: "var(--text-muted)" }}>NEGOTIATION OUTCOME</span>
          <span style={{ display: "flex", alignItems: "center", gap: 5, fontSize: 11, color: sc.dot, background: sc.dot + "20", padding: "2px 8px", borderRadius: 20 }}>
            <span style={{ width: 6, height: 6, borderRadius: "50%", background: sc.dot, display: "inline-block" }} />
            {sc.label}
          </span>
          {rounds > 0 && <span style={{ fontSize: 11, color: "var(--text-muted)" }}>{rounds} round{rounds !== 1 ? "s" : ""}</span>}
        </div>
        <button type="button" className="btn btn-ghost btn-sm" onClick={handleCopy} style={{ fontSize: 11 }}>
          {copied ? "Copied!" : "Copy summary"}
        </button>
      </div>
      <div style={{ display: "grid", gridTemplateColumns: "repeat(auto-fit, minmax(110px, 1fr))", gap: 8, marginBottom: 14 }}>
        <OutcomeStat label="Original bill" value={fmt(original) + "/mo"} />
        <OutcomeStat label={hasOffer ? "Best offer" : "No offer"} value={hasOffer ? fmt(best) + "/mo" : "—"} highlight={hasOffer} />
        {hasOffer && <OutcomeStat label="Monthly savings" value={"−" + fmt(savingsMonth) + "/mo"} highlight />}
        {hasOffer && <OutcomeStat label="Annual savings" value={fmt(savingsYear) + "/yr"} highlight />}
        {hasOffer && <OutcomeStat label="Reduction" value={savingsPct + "%"} highlight />}
      </div>
      {hasOffer && !dealClosed && (
        <div style={{ background: "rgba(74,222,128,0.08)", border: "1px solid rgba(74,222,128,0.2)", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#4ade80", lineHeight: 1.5 }}>
          💡 <strong>{negotiation.provider}</strong> offered <strong>{fmt(best)}/mo</strong> — saving you <strong>{fmt(savingsYear)}/year</strong>. This offer is still on the table. Call their retention line to lock it in.
        </div>
      )}
      {dealClosed && (
        <div style={{ background: "rgba(74,222,128,0.08)", border: "1px solid rgba(74,222,128,0.2)", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#4ade80", lineHeight: 1.5 }}>
          ✅ Deal closed — saving <strong>{fmt(savings)}/mo</strong> · <strong>{fmt(savings * 12)}/year</strong>.
        </div>
      )}
      {!hasOffer && (
        <div style={{ background: "rgba(251,191,36,0.08)", border: "1px solid rgba(251,191,36,0.2)", borderRadius: 8, padding: "10px 14px", fontSize: 13, color: "#fbbf24", lineHeight: 1.5 }}>
          ⚠️ No concrete offer was made. Try calling {negotiation.provider} directly — phone agents have more flexibility.
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [view, setView] = useState("dashboard");
  const [previousView, setPreviousView] = useState("dashboard");
  const [negotiations, setNegotiations] = useState([]);
  const [selected, setSelected] = useState(null);
  const [loading, setLoading] = useState(true);
  const [filter, setFilter] = useState("all");
  const [sort, setSort] = useState("newest");
  const [search, setSearch] = useState("");
  const [theme, setTheme] = useState(() => localStorage.getItem("ratepilot-theme") || "dark");
  const [autoRefresh, setAutoRefresh] = useState(() => localStorage.getItem("ratepilot-autorefresh") !== "false");
  const { toast, show: showToast } = useToast();

  useEffect(() => {
    document.documentElement.setAttribute("data-theme", theme);
    localStorage.setItem("ratepilot-theme", theme);
  }, [theme]);

  useEffect(() => {
    localStorage.setItem("ratepilot-autorefresh", autoRefresh);
  }, [autoRefresh]);

  const fetchNegotiations = useCallback(async () => {
    setLoading(true);
    try {
      const r = await fetch(`${API}/negotiations/`);
      setNegotiations(await r.json());
    } catch {
      setNegotiations([]);
    }
    setLoading(false);
  }, []);

  const fetchNegotiation = useCallback(async (id) => {
    const r = await fetch(`${API}/negotiations/${id}`);
    setSelected(await r.json());
  }, []);

  const handleSendEmail = useCallback(async (negotiationId, providerName, emailAddress = "") => {
    try {
      let to = emailAddress.trim();
      if (!to) {
        const lookup = await fetch(`${API}/email/provider-email/${encodeURIComponent(providerName || "")}`);
        const lookupData = await lookup.json();
        if (!lookup.ok) throw new Error(lookupData.detail || "Could not look up provider email");
        if (!lookupData.found || !lookupData.email) {
          return { needsEmail: true };
        }
        to = lookupData.email;
      }

      const response = await fetch(`${API}/email/send`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ negotiation_id: negotiationId, to }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(data.detail || "Failed to send email");

      showToast(`Email sent to ${providerName}`, "success");
      await fetchNegotiation(negotiationId);
      return { sent: true, to };
    } catch (err) {
      const message = err.message || "Failed to send email";
      showToast(message, "error");
      return { error: message };
    }
  }, [fetchNegotiation, showToast]);

  const retryNegotiation = useCallback(async (id) => {
    const r = await fetch(`${API}/agent/retry`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ negotiation_id: id }),
    });
    const data = await r.json();
    if (!r.ok) throw new Error(data.detail || "Could not retry negotiation");
    await fetchNegotiations();
    await fetchNegotiation(id);
    return data;
  }, [fetchNegotiations, fetchNegotiation]);

  const deleteNegotiation = useCallback(async (id) => {
    const r = await fetch(`${API}/negotiations/${id}`, { method: "DELETE" });
    if (!r.ok) throw new Error("Delete failed");
    if (selected?.id === id) {
      setSelected(null);
      setView("negotiations");
    }
    await fetchNegotiations();
    showToast("Negotiation deleted");
  }, [selected, fetchNegotiations, showToast]);

  const startFromBill = useCallback(async (billId) => {
    const r = await fetch(`${API}/agent/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ bill_id: billId }),
    });
    const data = await r.json();
    if (data.negotiation_id) {
      await fetchNegotiations();
      await fetchNegotiation(data.negotiation_id);
      setView("detail");
    }
    return data;
  }, [fetchNegotiations, fetchNegotiation]);

  useEffect(() => { fetchNegotiations(); }, [fetchNegotiations]);

  useEffect(() => {
    if (!autoRefresh || !selected) return;
    if (["researching", "strategizing", "drafting", "starting"].includes(selected.status)) {
      const t = setInterval(() => fetchNegotiation(selected.id), 3000);
      return () => clearInterval(t);
    }
  }, [selected, fetchNegotiation, autoRefresh]);

  const total = negotiations.length;
  const totalSavings = negotiations.reduce((a, n) => a + Math.max(getMonthlySavings(n), getBestOfferSavings(n)), 0);
  const won = negotiations.filter((n) => n.status === "won").length;
  const active = negotiations.filter((n) => !["won", "closed_no_deal"].includes(n.status)).length;
  const closed = negotiations.filter((n) => n.status === "closed_no_deal").length;
  const wonPct = pctOf(won, total);
  const activePct = pctOf(active, total);
  const savingsPctOfBill = (() => {
    const wonDeals = negotiations.filter((n) => n.status === "won");
    if (wonDeals.length === 0) return 0;
    let totalOriginal = 0;
    let totalSaved = 0;
    wonDeals.forEach((n) => {
      const orig = Number(n.current_amount) || 0;
      const saved = getMonthlySavings(n);
      if (orig > 0) {
        totalOriginal += orig;
        totalSaved += saved;
      }
    });
    return totalOriginal > 0 ? Math.round((totalSaved / totalOriginal) * 100) : 0;
  })();

  const navigate = (v) => {
    if (v !== "detail") setSelected(null);
    setView(v);
  };

  const openFilteredList = (filterId) => {
    setPreviousView(view);
    setFilter(filterId);
    navigate("negotiations");
  };

  const goBack = () => {
    if (view === "detail") {
      setSelected(null);
      setView(previousView);
      return;
    }
    navigate("dashboard");
  };

  const openNegotiation = async (id) => {
    setPreviousView(view);
    await fetchNegotiation(id);
    setView("detail");
  };

  const showBack = view !== "dashboard";
  const backLabel = view === "detail"
    ? (BACK_LABELS[previousView] || "Negotiations")
    : "Overview";

  const pageTitle = {
    dashboard: "Overview",
    negotiations: (FILTER_PAGE_META[filter] || FILTER_PAGE_META.all).title,
    upload: "New bill",
    settings: "Settings",
    detail: selected?.provider || "Negotiation",
  }[view];

  const topbarExtra = (
    <div className="topbar-actions">
      <div className="search-box">
        <span style={{ color: "var(--text-subtle)" }}>⌕</span>
        <input
          placeholder="Search negotiations…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
        />
      </div>
      <button type="button" className="btn btn-secondary btn-sm" onClick={fetchNegotiations} title="Refresh">↻</button>
      <button type="button" className="btn btn-primary" onClick={() => navigate("upload")}>+ New bill</button>
    </div>
  );

  const breadcrumbs = view === "detail" ? null : (
    <>
      <strong>{pageTitle}</strong>
      {view === "dashboard" && <span className="breadcrumb-meta">Operations summary</span>}
    </>
  );

  let content;
  if (view === "upload") {
    content = (
      <>
        <div className="page-header">
          <h2>Upload a bill</h2>
          <p>Start a new automated negotiation from your monthly statement.</p>
        </div>
        <UploadView
          onDone={(id) => {
            fetchNegotiations();
            setPreviousView("upload");
            fetchNegotiation(id).then(() => setView("detail"));
          }}
          showToast={showToast}
        />
      </>
    );
  } else if (view === "detail" && selected) {
    content = (
      <NegotiationDetail
        negotiation={selected}
        onBack={goBack}
        onRefresh={() => fetchNegotiation(selected.id)}
        onRestart={startFromBill}
        onDelete={deleteNegotiation}
        onRetry={retryNegotiation}
        onSendEmail={handleSendEmail}
        showToast={showToast}
      />
    );
  } else if (view === "settings") {
    content = (
      <>
        <div className="page-header">
          <h2>Settings</h2>
          <p>Configure appearance and agent behavior.</p>
        </div>
        <SettingsView theme={theme} setTheme={setTheme} autoRefresh={autoRefresh} setAutoRefresh={setAutoRefresh} />
      </>
    );
  } else if (view === "negotiations") {
    const pageMeta = FILTER_PAGE_META[filter] || FILTER_PAGE_META.all;
    content = (
      <>
        <div className="page-header">
          <h2>{pageMeta.title}</h2>
          <p>{pageMeta.subtitle}</p>
        </div>
        <NegotiationsTable
          negotiations={negotiations}
          loading={loading}
          filter={filter}
          sort={sort}
          search={search}
          onOpen={openNegotiation}
          onRefresh={fetchNegotiations}
          onFilterChange={setFilter}
          onSortChange={setSort}
          showToast={showToast}
          onRestart={startFromBill}
          onRetry={retryNegotiation}
          onDelete={deleteNegotiation}
        />
      </>
    );
  } else {
    content = (
      <>
        <div className="page-header">
          <h2>Operations overview</h2>
          <p>Real-time metrics across the negotiation pipeline.</p>
        </div>
        <div className="stats-row">
          <StatCard
            label="Total savings"
            value={"$" + totalSavings.toFixed(0) + "/mo"}
            sub={
              total > 0
                ? "$" + (totalSavings * 12).toFixed(0) + "/yr · " + (won > 0 ? savingsPctOfBill + "% off original bills" : "no won deals yet")
                : "—"
            }
            pct={won > 0 ? savingsPctOfBill : null}
            barClass="bar-savings"
            accent={totalSavings > 0}
            onClick={() => openFilteredList("won")}
          />
          <StatCard
            label="Deals won"
            value={won + " / " + total}
            sub={won + " of " + total + " negotiations closed successfully"}
            pct={wonPct}
            barClass="bar-won"
            accent={won > 0}
            onClick={() => openFilteredList("won")}
          />
          <StatCard
            label="Active"
            value={active + " / " + total}
            sub={active + " in progress · " + activePct + "% of pipeline"}
            pct={activePct}
            barClass="bar-active"
            onClick={() => openFilteredList("active")}
          />
          <StatCard
            label="Total processed"
            value={String(total)}
            sub={total > 0 ? "100% · full negotiation volume" : "—"}
            pct={total > 0 ? 100 : null}
            barClass="bar-total"
            onClick={() => openFilteredList("all")}
          />
        </div>
        <SavingsOverview negotiations={negotiations} />
        <PipelineBreakdown
          total={total}
          won={won}
          active={active}
          closed={closed}
          totalSavings={totalSavings}
        />
        <div className="page-header" style={{ marginTop: 8 }}>
          <h2 style={{ fontSize: 16 }}>Recent negotiations</h2>
        </div>
        <NegotiationsTable
          negotiations={negotiations.slice(0, 5)}
          loading={loading}
          filter="all"
          sort={sort}
          search={search}
          onOpen={openNegotiation}
          onRefresh={fetchNegotiations}
          onFilterChange={setFilter}
          onSortChange={setSort}
          showToast={showToast}
          onRestart={startFromBill}
          onRetry={retryNegotiation}
          onDelete={deleteNegotiation}
          compact
        />
        {negotiations.length > 5 && (
          <button type="button" className="btn btn-ghost" style={{ marginTop: 12 }} onClick={() => navigate("negotiations")}>
            View all {negotiations.length} negotiations →
          </button>
        )}
      </>
    );
  }

  return (
    <>
      <AppShell
        view={view}
        onNavigate={navigate}
        showBack={showBack}
        onBack={goBack}
        backLabel={backLabel}
        breadcrumbs={view === "detail" ? (
          <>
            <span style={{ color: "var(--text-subtle)" }}>/</span>
            <strong>{selected?.provider}</strong>
          </>
        ) : breadcrumbs}
        topbarExtra={topbarExtra}
        totalSavings={totalSavings}
      >
        {content}
      </AppShell>
      {toast && <div className={`toast toast-${toast.type}`}>{toast.message}</div>}
    </>
  );
}
