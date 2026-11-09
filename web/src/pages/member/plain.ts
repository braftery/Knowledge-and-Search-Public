export function plainMemberTitle(title: string) {
  // The title as approved, without the internal approver suffix. It reads as a name in "Source: Harbor Health, {title}".
  return title.replace(" (Legal verbatim)", "").replace(" (Legal)", "");
}

export function memberUpdated(answer: { updated?: string; effective_date?: string }) {
  return (answer.updated || answer.effective_date || "").slice(0, 10);
}
