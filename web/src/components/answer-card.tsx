import { Copy, Flag } from "lucide-react";
import { useId, useState } from "react";
import * as Popover from "@radix-ui/react-popover";
import { Button } from "@/components/button";
import { Citation } from "@/components/citation";
import { DecisionMarker } from "@/components/decision-marker";
import { Icon } from "@/components/icon";
import { VerbatimBlock } from "@/components/verbatim-block";
import { showUndoToast } from "@/components/toast";

export const FLAG_REASONS = [
  { id: "couldnt_find", label: "Could not find it" },
  { id: "hard_to_find", label: "Hard to find" },
  { id: "confusing_wording", label: "Wording confused the member" },
  { id: "wrong_or_outdated", label: "Looks wrong or out of date" },
] as const;

export type FlagPayload = {
  kind: (typeof FLAG_REASONS)[number]["id"];
  note: string;
};

type AnswerCardProps = {
  question: string;
  wording: string;
  verbatim?: boolean;
  citation: {
    title: string;
    version?: number;
    approver?: string;
    date: string;
    sourceHref?: string;
  };
  onFlag?: (payload: FlagPayload) => void;
  fit?: boolean;
  approval?: { role: string; timestamp?: string; version?: number };
  readerRole?: string;
};

export function AnswerCard({ question, wording, verbatim = false, citation, onFlag, fit = false, approval, readerRole }: AnswerCardProps) {
  const noteId = useId();
  const [kind, setKind] = useState<FlagPayload["kind"]>("couldnt_find");
  const [note, setNote] = useState("");
  const [open, setOpen] = useState(false);

  async function copyWording() {
    try {
      await navigator.clipboard.writeText(wording);
    } catch {
      const area = document.createElement("textarea");
      area.value = wording;
      document.body.appendChild(area);
      area.select();
      document.execCommand("copy");
      area.remove();
    }
    showUndoToast({ message: "Copied the approved wording." });
  }

  function sendFlag() {
    onFlag?.({ kind, note: note.trim() });
    setOpen(false);
    setNote("");
    showUndoToast({ message: "Flag sent. Member details are removed before it is stored." });
  }

  return (
    <article className="hh-answer" style={fit ? undefined : { maxWidth: 400 }}>
      <div className="hh-answer__q">{question}</div>
      {approval ? (
        <DecisionMarker
          kind="human"
          role={approval.role}
          timestamp={approval.timestamp}
          decision={approval.version ? `Approved version ${approval.version}.` : "Approved."}
        />
      ) : null}
      {verbatim ? <VerbatimBlock text={wording} /> : <p className="tools-body" style={{ margin: 0 }}>{wording}</p>}
      {verbatim && readerRole ? <p className="hh-meta" style={{ margin: 0 }}>Read word for word. Paraphrasing is not allowed.</p> : null}
      <Citation audience="internal" {...citation} />
      <div className="hh-answer__actions">
        <Button variant="secondary" compact onClick={copyWording}>
          <Icon icon={Copy} />
          Copy wording
        </Button>
        <Popover.Root open={open} onOpenChange={setOpen}>
          <Popover.Trigger asChild>
            <Button variant="tertiary" compact>
              <Icon icon={Flag} />
              Flag this answer
            </Button>
          </Popover.Trigger>
          <Popover.Portal>
            <Popover.Content className="hh-card" sideOffset={8} align="start" style={{ width: 320 }}>
              <fieldset style={{ border: 0, margin: 0, padding: 0, display: "flex", flexDirection: "column", gap: 8 }}>
                <legend className="hh-label">What went wrong?</legend>
                {FLAG_REASONS.map((reason) => (
                  <label key={reason.id} className="tools-body" style={{ display: "flex", gap: 8, alignItems: "center" }}>
                    <input
                      type="radio"
                      name={noteId}
                      value={reason.id}
                      checked={kind === reason.id}
                      onChange={() => setKind(reason.id)}
                    />
                    {reason.label}
                  </label>
                ))}
              </fieldset>
              <label className="hh-label" htmlFor={`${noteId}-note`} style={{ display: "block", marginTop: 12 }}>
                Note <span className="hh-opt">(optional)</span>
              </label>
              <input
                id={`${noteId}-note`}
                className="hh-input"
                value={note}
                onChange={(event) => setNote(event.target.value)}
                placeholder="For example, took three searches…"
                autoComplete="off"
              />
              <div style={{ marginTop: 12 }}>
                <Button variant="primary" compact onClick={sendFlag}>
                  Send to the knowledge team
                </Button>
              </div>
            </Popover.Content>
          </Popover.Portal>
        </Popover.Root>
      </div>
    </article>
  );
}
