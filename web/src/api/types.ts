export type SessionMode = "start" | "short" | "jump" | "explore";

export type Session = {
  session_id: string;
  mode: SessionMode;
};

export type MemberCitation = {
  title: string;
  date: string;
};

export type MemberAnswer = {
  abstained: boolean;
  member_text: string;
  title: string;
  version: number | null;
  unit_id: string;
  citation: string;
  ai_source: string;
  query: string;
  updated?: string;
  effective_date?: string;
  suggestions?: string[];
  kind?: string;
  reply?: string;
  chips?: string[];
  units?: UnitRef[];
  price?: DrugPrice;
  visit_cost?: VisitCost;
};

/** An approved unit attached by reference to a number from plan data. */
export type UnitRef = { unit_id: string; version: number; title: string; text: string; citation: string; type?: string };

export type PlanDrug = { drug_id: string; name: string; strength: string; tier?: number; specialty: boolean };

export type DrugPrice = {
  drug: PlanDrug;
  pharmacy: string;
  days: number;
  available: boolean;
  price: number | null;
  price_display: string;
  tier_label: string;
  coverage_stage: string;
  note: string;
  withheld_reason: string;
  units: UnitRef[];
};

export type VisitCost = {
  visit: string;
  network: string;
  available: boolean;
  cost: number | null;
  cost_display: string;
  note: string;
  withheld_reason: string;
  units: UnitRef[];
};

type Money = { amount: number; display: string };

export type MemberProfile = {
  member: { member_id: string; name: string; plan: string };
  plan: Record<string, Money | string | unknown> & { name?: string };
  coverage_stage: string;
  oop?: { limit: number; spent: number; limit_display: string; spent_display: string };
  drug_deductible?: { amount: number; met: boolean };
  drugs: PlanDrug[];
  claims?: Array<{
    date: string;
    provider_type: string;
    amount_billed_display: string;
    plan_paid_display: string;
    member_paid_display: string;
    status: string;
  }>;
  recent_contacts: Array<{ date: string; channel: string; summary: string }>;
};

export type MemberRecord = MemberProfile & {
  verified?: boolean;
  prices?: Array<{ drug_id: string; available: boolean; price_display: string; tier_label: string; note: string }>;
  units?: UnitRef[];
  withheld_reason?: string;
};

export type MemberTopic = {
  label: string;
  question: string;
};

export type UnitView = {
  unit_id: string;
  version: number;
  title: string;
  type: string;
  text: string;
  member_text: string;
  status: string;
  kb_scope: string;
  audience: string;
  applicability: string;
  source_doc: string;
  source_quote: string;
  approved_by: string;
  approved_on: string;
  effective_date: string;
  channels: string;
  verbatim: boolean;
};

export type SearchResult = {
  /** The caller is not verified: the result is the advocate's rule, not an answer to read to the member. */
  verify_first?: boolean;
  kind?: string;
  price?: DrugPrice;
  visit_cost?: VisitCost;
  price_options?: Array<{ pharmacy: string; days: number; available: boolean; price_display: string }>;
  units?: UnitRef[];
  status?: string;
  blocked_note?: string;
  fallback_unit?: UnitView | null;
  abstained: boolean;
  query: string;
  role: string;
  ai_source: string;
  note: string;
  searched: string[];
  unit: UnitView | null;
  /** The queue that owns this question, when this role cannot read its knowledge base. */
  transfer?: { queue: string; reason: string } | null;
};

export class ApiError extends Error {
  status: number;
  constructor(status: number, message: string) {
    super(message);
    this.status = status;
  }
}
