// In-memory order-wizard draft. Nothing here is written to the backend
// until Confirm on the final step — mirrors the original kiosk's design
// (no abandoned partial-order rows for a draft that's started but never
// finished).
export function freshDraft() {
  return {
    customer: { id: null, name: "", contact: "", email: "", address: "" },
    event: { date: "", time: "18:00", venue: "", occasion: "", pax: 60, pickupTime: "", dropoffTime: "" },
    // Order Type picked on the wizard's Order-Type screen:
    // 'package' | 'food_tray' | 'food_set'. Drives which branch the Event &
    // Package step shows (package grid / nothing / Sets A-E picker).
    flowType: "",
    package: { id: null, name: "", pricePerPax: 0, baseTotal: 0, minPax: 30 },
    // Food Set selections (flowType === 'food_set'). Supports MULTIPLE
    // different sets AND repeating the same set with a quantity:
    // [{set_id, name, quantity, unit_price, dishes:[{name,category,price,quantity}]}]
    setSelections: [],
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

export function setsTotal(draft) {
  return (draft.setSelections || []).reduce((sum, s) => sum + Number(s.unit_price || 0) * Number(s.quantity || 0), 0);
}

export function grandTotal(draft) {
  const base = draft.flowType === "food_set" ? setsTotal(draft) : Number(draft.package.baseTotal || 0);
  return base + chargesTotal(draft);
}

export function peso(n) {
  const v = Number(n || 0);
  return "₱" + v.toLocaleString("en-PH", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
