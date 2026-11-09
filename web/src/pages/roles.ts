export const ROLES = [
  {
    id: "author",
    role: "Knowledge Ops author",
    where: "Single Source Studio",
    task: "Open My work and take the first item.",
    views: [{ id: "work", label: "Studio" }],
  },
  {
    id: "legal",
    role: "Legal approver",
    where: "Email, then the review page",
    task: "Start review on the items waiting for a decision.",
    views: [{ id: "inbox", label: "Email" }],
  },
  {
    id: "pharmacy",
    role: "Pharmacy advocate",
    where: "Contact center desktop",
    task: "Read the suggested answer for the call.",
    views: [{ id: "desktop", label: "Agent desktop" }],
  },
  {
    id: "insurance",
    role: "Insurance advocate",
    where: "Contact center desktop",
    task: "Read the suggested answer for the call.",
    views: [{ id: "desktop", label: "Agent desktop" }],
  },
  {
    id: "member",
    role: "Member",
    where: "Phone line, website and app",
    task: "Call or ask online about a drug price.",
    // Phone first: many older members prefer to call (SERVICE_DESIGN 2.6).
    views: [
      { id: "phone", label: "Phone line" },
      { id: "website", label: "Website" },
      { id: "app", label: "App" },
    ],
  },
  {
    id: "owner",
    role: "Knowledge owner",
    where: "Weekly insights",
    task: "See the top gaps and what needs attention.",
    views: [{ id: "insights", label: "Insights" }],
  },
  {
    id: "channel",
    role: "Channel and AI team",
    where: "Developer docs",
    task: "Run the first sample request.",
    views: [{ id: "docs", label: "Docs" }],
  },
] as const;

export type RoleId = (typeof ROLES)[number]["id"];

export function roleById(id: string | undefined) {
  return ROLES.find((role) => role.id === id) ?? null;
}
