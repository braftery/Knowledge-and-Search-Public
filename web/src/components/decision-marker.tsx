import { Clock, Sparkles, UserRound } from "lucide-react";
import { Icon } from "@/components/icon";
import { readableDate } from "@/lib/dates";

type DecisionMarkerProps = {
  kind: "ai" | "pending" | "human";
  role?: string;
  name?: string;
  timestamp?: string;
  decision?: string;
  detail?: string;
};

/** Who made the call. Never render this on a member surface. */
export function DecisionMarker({ kind, role, name, timestamp, decision, detail }: DecisionMarkerProps) {
  if (kind === "ai") {
    return (
      <span className="hh-row">
        <span className="hh-mark hh-mark--ai">
          <Icon icon={Sparkles} />
          AI proposed
        </span>
        {detail ? <span className="hh-meta">{detail}</span> : null}
      </span>
    );
  }

  if (kind === "pending") {
    return (
      <span className="hh-mark hh-mark--pending">
        <Icon icon={Clock} />
        Needs a person{role ? `: ${role}` : ""}
      </span>
    );
  }

  const who = [role, name, timestamp ? readableDate(timestamp) : ""].filter(Boolean).join(", ");
  return (
    <span className="hh-row">
      <span className="hh-mark hh-mark--human">
        <Icon icon={UserRound} />
        Human decision{who ? <span className="hh-mark__who">{who}</span> : null}
      </span>
      {decision ? <span className="hh-meta">{decision}</span> : null}
    </span>
  );
}
