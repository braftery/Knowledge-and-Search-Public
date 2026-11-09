const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];

/**
 * "2026-09-23" reads as "Sep 23, 2026", and "2026-09-23 10:15 ET" as "Sep 23, 2026, 10:15 ET".
 * Anything that does not start with a date is returned as given.
 */
export function readableDate(value: string | undefined | null) {
  const text = (value || "").trim();
  const match = /^(\d{4})-(\d{2})-(\d{2})(?:[ T](\d{2}):(\d{2})(?::\d{2})?(?:\s*([A-Z]{2,4}))?)?/.exec(text);
  if (!match) return text;
  const [, year, month, day, hour, minute, zone] = match;
  const date = `${MONTHS[Number(month) - 1] ?? month} ${Number(day)}, ${year}`;
  return hour ? `${date}, ${hour}:${minute}${zone ? ` ${zone}` : ""}` : date;
}
