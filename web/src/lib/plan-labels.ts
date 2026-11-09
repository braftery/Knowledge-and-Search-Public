import type { DrugPrice, VisitCost } from "@/api/types";

export const PHARMACY_LABELS: Record<string, string> = {
  preferred_retail: "preferred retail pharmacy",
  standard_retail: "standard retail pharmacy",
  mail_order: "mail order",
  specialty: "Harbor Specialty Pharmacy",
};

export const VISIT_LABELS: Record<string, string> = {
  primary_care: "Primary care visit",
  specialist: "Specialist visit",
  urgent_care: "Urgent care visit",
  emergency: "Emergency room visit",
};

export function priceHeadline(price: DrugPrice) {
  const where = PHARMACY_LABELS[price.pharmacy] || price.pharmacy;
  return `${price.drug.name} ${price.drug.strength}, ${price.days}-day supply, ${where}`;
}

export function visitHeadline(cost: VisitCost) {
  return `${VISIT_LABELS[cost.visit] || cost.visit}, ${cost.network === "out" ? "out of network" : "in network"}`;
}
