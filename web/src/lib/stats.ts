/**
 * Wilson 95% interval for a pass rate, so a small golden set shows how little it proves.
 * "8 of 8" reads as "95% interval 68% to 100%".
 */
export function wilson(pass: number, total: number) {
  if (!total) return null;
  const z = 1.96;
  const p = pass / total;
  const denom = 1 + (z * z) / total;
  const centre = (p + (z * z) / (2 * total)) / denom;
  const margin = (z * Math.sqrt((p * (1 - p)) / total + (z * z) / (4 * total * total))) / denom;
  return { low: Math.max(0, centre - margin), high: Math.min(1, centre + margin) };
}

/** "95% interval 68% to 100%." from a detail such as "8 of 8", or "" when the detail is not a count. */
export function intervalNote(detail: string) {
  const match = /(\d+) of (\d+)/.exec(detail || "");
  if (!match) return "";
  const range = wilson(Number(match[1]), Number(match[2]));
  if (!range) return "";
  return `95% interval ${Math.round(range.low * 100)}% to ${Math.round(range.high * 100)}%.`;
}
