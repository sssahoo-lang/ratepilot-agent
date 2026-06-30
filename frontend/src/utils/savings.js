/** Monthly savings — backend is the single source of truth. */
export function getMonthlySavings(n) {
  return Number(n?.monthly_savings) || 0;
}

/** Best offer savings — same field; backend computes from best_offer_received or savings_achieved. */
export function getBestOfferSavings(n) {
  return Number(n?.monthly_savings) || 0;
}
