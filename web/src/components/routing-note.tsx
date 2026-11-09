import { Route } from "lucide-react";
import { routingWhy } from "@/lib/labels";

/** Shows why the routing rule sent a unit to Legal or to Knowledge Ops approvals. Renders nothing for units with no recorded reason. */
export function RoutingNote({ reason, heading }: { reason?: string; heading?: string }) {
  const parsed = routingWhy(reason);
  if (!parsed) return null;
  const title = heading ?? (parsed.queue ? `Why this went to ${parsed.queue}` : "Why this came here");
  return (
    <aside className="routing-note" aria-label={title}>
      <Route aria-hidden="true" className="routing-note__icon" />
      <div>
        <p className="routing-note__title">{title}</p>
        <p className="routing-note__why">{parsed.why}</p>
        <p className="routing-note__rule">Set by the routing rule, which can send a unit up to Legal but never lowers a Legal gate.</p>
      </div>
    </aside>
  );
}
