// In-memory order-wizard draft. Nothing here is written to the backend
// until Confirm on the final step — mirrors the original kiosk's design
// (no abandoned partial-order rows for a draft that's started but never
// finished).
export function freshDraft() {
  return {
    customer: { id: null, name: "", contact: "", email: "", address: "" },
    event: { date: "", time: "18:00", venue: "", occasion: "", pax: 60 },
    package: { id: null, name: "", pricePerPax: 0, baseTotal: 0, minPax: 30 },
    menuSelections: [], // [{menu_item_id, item_name, category, price, quantity}]
    additionalCharges: [], // [{description, amount}]
    downPayment: 0,
    paymentMethod: "Cash",
    notes: "",
  };
}

export const wizard = {
  draft: freshDraft(),
  step: 1,
  totalSteps: 6,
  reset() {
    this.draft = freshDraft();
    this.step = 1;
  },
};

export function chargesTotal(draft) {
  return draft.additionalCharges.reduce((sum, c) => sum + Number(c.amount || 0), 0);
}

export function grandTotal(draft) {
  return Number(draft.package.baseTotal || 0) + chargesTotal(draft);
}

export function peso(n) {
  const v = Number(n || 0);
  return "₱" + v.toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
