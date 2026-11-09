import type { ApiDiff } from "@/api/guided";
import type { DiffPart } from "@/lib/word-diff";

export function apiDiff(parts: ApiDiff[] | undefined): DiffPart[] {
  return (parts || []).map((part) => {
    if (part.kind === "remove") return { kind: "del", text: part.text };
    if (part.kind === "add") return { kind: "add", text: part.text };
    return { kind: "text", text: part.text };
  });
}

export function addedOnly(parts: ApiDiff[] | undefined): DiffPart[] {
  return apiDiff(parts).filter((part) => part.kind !== "del");
}

const CHANNELS: Record<string, string> = {
  advocate_guidance: "Advocate guidance",
  member_chat: "Member chat",
  website: "Website",
  voice_bot: "Phone line",
};

const BASES: Record<string, string> = {
  pharmacy: "Pharmacy",
  benefits: "Benefits",
  "shared-legal": "Shared legal",
};

const STATUSES: Record<string, string> = {
  proposed: "Proposed",
  approved: "Approved",
  returned: "Sent back",
  superseded: "Superseded",
  blocked_conflict: "Blocked",
  merged: "Merged",
  retired: "Retired",
};

const RELATIONS: Record<string, string> = {
  exact: "Exact copy",
  near_duplicate: "Near-duplicate",
  conflict: "Conflict",
};

export function channelLabel(value: string) {
  return CHANNELS[value] || value.replaceAll("_", " ");
}

export function baseLabel(value: string) {
  return BASES[value] || value;
}

export function statusLabel(value: string | undefined) {
  if (!value) return "";
  return STATUSES[value] || value;
}

export function relationLabel(value: string) {
  return RELATIONS[value] || value.replaceAll("_", " ");
}

export function joinLabels(values: string[] | undefined, label: (value: string) => string) {
  return (values || []).map(label).join(", ");
}

export function listPhrase(values: string[]) {
  if (values.length === 0) return "";
  if (values.length === 1) return values[0];
  if (values.length === 2) return `${values[0]} and ${values[1]}`;
  return `${values.slice(0, -1).join(", ")}, and ${values[values.length - 1]}`;
}

/** "Routed to Legal: mentions cost." becomes { queue: "Legal", why: "Mentions cost." } */
export function routingWhy(reason: string | undefined) {
  const text = (reason || "").trim();
  if (!text) return null;
  const match = text.match(/^Routed to ([^:]+):\s*(.+)$/);
  if (!match) return { queue: "", why: text };
  const why = match[2].trim();
  return { queue: match[1].trim(), why: why.charAt(0).toUpperCase() + why.slice(1) };
}

/** Unit titles carry a "(Legal)" queue suffix for staff; advocates and members see the plain title. */
export function plainTitle(title: string) {
  return (title || "").replace(/\s*\((Legal|Legal verbatim)\)\s*$/, "");
}
