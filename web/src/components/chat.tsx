import { MessageCircle, X } from "lucide-react";
import { useEffect, useId, useRef, useState, type FormEvent, type ReactNode } from "react";
import { createPortal } from "react-dom";
import { Button } from "@/components/button";
import { Citation } from "@/components/citation";
import { QuoteCard } from "@/components/quote-card";
import type { UnitRef } from "@/api/types";
import { Icon } from "@/components/icon";
import { SlowNote } from "@/components/slow-note";

type ChatLauncherProps = {
  open: boolean;
  onToggle: () => void;
};

export function ChatLauncher({ open, onToggle }: ChatLauncherProps) {
  return (
    <button
      className="hh-launcher"
      type="button"
      aria-expanded={open}
      aria-controls="ask-harbor-panel"
      onClick={onToggle}
    >
      <Icon icon={MessageCircle} />
      Ask Harbor
    </button>
  );
}

export type ChatMessage = {
  kind: "message";
  id: string;
  from: "bot" | "member";
  text: string;
  citation?: { title: string; date: string };
  /** Safety replies (emergency and crisis) are shown with more weight than ordinary answers. */
  tone?: "urgent";
};

export type TranscriptItem =
  | ChatMessage
  | { kind: "chips"; id: string; labels: string[] }
  | { kind: "help"; id: string; question: string; unitId: string }
  | { kind: "handoff"; id: string }
  | {
      kind: "quote";
      id: string;
      amount?: string;
      headline: string;
      details?: string[];
      note?: string;
      withheld?: string;
      units: UnitRef[];
    };

type ChatPanelProps = {
  items: TranscriptItem[];
  onChip?: (label: string) => void;
  onSend: (text: string) => void;
  onClose: () => void;
  onHelp?: (yes: boolean) => void;
  onHandoff?: () => void;
  inputLabel?: string;
  autoFocus?: boolean;
  capped?: boolean;
  fill?: boolean;
  pending?: boolean;
};

export function ChatPanel({
  items,
  onChip,
  onSend,
  onClose,
  onHelp,
  onHandoff,
  inputLabel = "Your question",
  autoFocus = true,
  capped = false,
  fill = false,
  pending = false,
}: ChatPanelProps) {
  const inputId = useId();
  const inputRef = useRef<HTMLInputElement>(null);
  const closeRef = useRef<HTMLButtonElement>(null);
  const bodyRef = useRef<HTMLDivElement>(null);
  const sheet = useNarrow() && !fill;

  useEffect(() => {
    const body = bodyRef.current;
    const conversationStarted = items.some((item) => item.kind === "message" && item.from === "member");
    if (body && (conversationStarted || pending)) body.scrollTop = body.scrollHeight;
  }, [items, pending]);

  useEffect(() => {
    const fine = window.matchMedia("(pointer: fine)").matches;
    if (autoFocus && fine) inputRef.current?.focus();
  }, [autoFocus]);

  useEffect(() => {
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        event.preventDefault();
        onClose();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [onClose]);

  function submit(event: FormEvent) {
    event.preventDefault();
    const value = inputRef.current?.value.trim() ?? "";
    if (!value) return;
    onSend(value);
    if (inputRef.current) inputRef.current.value = "";
  }

  const closeButton = (
    <button ref={closeRef} className="hh-btn hh-btn--tertiary" type="button" aria-label="Close chat" onClick={onClose}>
      <Icon icon={X} />
    </button>
  );

  const panel = (
    <section
      className={["hh-chat", fill ? "" : "hh-chat-pop", capped ? "hh-chat--capped" : "", sheet ? "hh-chat--sheet" : ""].filter(Boolean).join(" ")}
      id="ask-harbor-panel"
      aria-label="Ask Harbor"
      role={sheet ? "dialog" : undefined}
      aria-modal={sheet ? true : undefined}
      style={fill ? { width: "100%", height: "100%", maxHeight: "none", borderRadius: 0, boxShadow: "none" } : undefined}
    >
      <header className="hh-chat__head">
        {sheet ? closeButton : null}
        <h2 className="hh-chat__title">Ask Harbor</h2>
        {sheet ? null : closeButton}
      </header>
      <div className="hh-chat__body" ref={bodyRef} role="log" aria-live="polite" aria-relevant="additions" aria-label="Conversation">
        {items.map((item) => {
          if (item.kind === "chips") {
            return (
              <div key={item.id} className="hh-chips" role="group" aria-label="Suggestions">
                {item.labels.map((chip) => (
                  <button key={chip} className="hh-chip" type="button" onClick={() => onChip?.(chip)}>
                    {chip}
                  </button>
                ))}
              </div>
            );
          }
          if (item.kind === "help") {
            return (
              <div key={item.id} className="hh-row" style={{ gap: 8 }}>
                <span>Did that answer help?</span>
                <Button variant="secondary" compact onClick={() => onHelp?.(true)} style={{ minHeight: 44 }}>
                  Yes
                </Button>
                <Button variant="secondary" compact onClick={() => onHelp?.(false)} style={{ minHeight: 44 }}>
                  No
                </Button>
              </div>
            );
          }
          if (item.kind === "quote") {
            return (
              <div key={item.id} className="hh-bubble hh-bubble--bot hh-bubble--quote">
                <QuoteCard
                  compact
                  amount={item.amount}
                  headline={item.headline}
                  details={item.details}
                  note={item.note}
                  withheld={item.withheld}
                  units={item.units}
                />
              </div>
            );
          }
          if (item.kind === "handoff") {
            return (
              <Button key={item.id} variant="primary" onClick={onHandoff}>
                Talk to a member advocate
              </Button>
            );
          }
          return (
            <div
              key={item.id}
              className={item.from === "bot" ? `hh-bubble hh-bubble--bot${item.tone === "urgent" ? " hh-bubble--urgent" : ""}` : "hh-bubble hh-bubble--me"}
              role={item.tone === "urgent" ? "alert" : undefined}
            >
              {item.text}
              {item.citation ? <Citation audience="member" title={item.citation.title} date={item.citation.date} /> : null}
            </div>
          );
        })}
        {pending ? (
          <div className="hh-bubble hh-bubble--bot" aria-busy="true">
            Looking that up…
            <SlowNote active={pending} className="hh-chat__slow" />
          </div>
        ) : null}
      </div>
      <form className="hh-chat__foot" onSubmit={submit}>
        <input
          ref={inputRef}
          id={inputId}
          className="hh-input"
          aria-label={inputLabel}
          placeholder="Ask about your plan…"
          autoComplete="off"
        />
        <Button variant="primary" type="submit">
          Send
        </Button>
      </form>
      <p className="hh-chat__note">
        Please don't type personal details like your member ID or date of birth here.
      </p>
    </section>
  );

  if (sheet) {
    return createPortal(
      <div data-theme="member" className="hh-m">
        {panel}
      </div>,
      document.body,
    );
  }
  return panel;
}

function useNarrow() {
  const [narrow, setNarrow] = useState(() => window.matchMedia("(max-width: 639px)").matches);
  useEffect(() => {
    const query = window.matchMedia("(max-width: 639px)");
    const apply = () => setNarrow(query.matches);
    apply();
    query.addEventListener("change", apply);
    return () => query.removeEventListener("change", apply);
  }, []);
  return narrow;
}

export function ChatFrame({ children }: { children: ReactNode }) {
  return (
    <div data-theme="member" className="hh-m">
      {children}
    </div>
  );
}
