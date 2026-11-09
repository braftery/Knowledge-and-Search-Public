import { useEffect, useState } from "react";
import { memberAnswer, memberProfile, memberTopics, sendFeedback } from "@/api/client";
import type { MemberTopic } from "@/api/types";
import { useQuery } from "@/api/use-query";
import type { TranscriptItem } from "@/components/chat";
import { showUndoToast } from "@/components/toast";
import { memberUpdated, plainMemberTitle } from "@/pages/member/plain";
import { priceHeadline, visitHeadline } from "@/lib/plan-labels";
import { readableDate } from "@/lib/dates";

const GREETING =
  "Hi, I can answer questions about your Harbor Health plan. What can I help with?";
const NO_ANSWER = "I don't have an approved answer for that yet. I can connect you with a member advocate.";
const STOP = new Set("a an the is are do does my i me to of for on in at it this that what how can will be with or and".split(" "));

function clarifyLabels(question: string, topics: MemberTopic[]) {
  const words = question
    .toLowerCase()
    .split(/\s+/)
    .map((word) => word.replace(/[^a-z]/g, ""))
    .filter((word) => word && !STOP.has(word));
  const scored = topics
    .map((topic) => {
      const haystack = `${topic.label} ${topic.question}`.toLowerCase();
      const score = words.reduce((total, word) => total + (haystack.includes(word) ? 1 : 0), 0);
      return { label: topic.label, score };
    })
    .filter((item) => item.score > 0)
    .sort((left, right) => right.score - left.score || left.label.localeCompare(right.label));
  return scored.slice(0, 4).map((item) => item.label);
}

const ADD_CALLER = "Add an authorized caller";
const CAREGIVER_UNIT = "U-RX-EDU-001-05";

/** onAddCaller opens the add-an-authorized-caller task where the channel has one (the website). */
export function useMemberChat(sessionId: string | null, onAddCaller?: () => void) {
  const topics = useQuery(`topics:${sessionId ?? "none"}`, () => memberTopics(sessionId as string), Boolean(sessionId));
  const [items, setItems] = useState<TranscriptItem[]>([{ kind: "message", id: "hi", from: "bot", text: GREETING }]);
  const [chipsOn, setChipsOn] = useState(true);
  const [pending, setPending] = useState(false);

  useEffect(() => {
    const loaded = topics.data;
    if (!loaded || !chipsOn) return;
    setItems((current) => {
      if (current.some((item) => item.kind === "chips")) return current;
      return [...current, { kind: "chips", id: "topics", labels: loaded.slice(0, 4).map((topic) => topic.label) }];
    });
  }, [topics.data, chipsOn]);

  async function ask(question: string) {
    const clean = question.trim();
    if (!clean || pending) return;
    setChipsOn(false);
    setItems((current) => [
      ...current.filter((item) => item.kind !== "chips" && item.kind !== "help" && item.kind !== "handoff"),
      { kind: "message", id: `q-${Date.now()}`, from: "member", text: clean },
    ]);
    if (!sessionId) {
      setItems((current) => [
        ...current,
        { kind: "message", id: `e-${Date.now()}`, from: "bot", text: "I cannot look that up right now. Try again in a moment, or I can connect you with a member advocate." },
        { kind: "handoff", id: `h-${Date.now()}` },
      ]);
      return;
    }
    setPending(true);
    try {
      const answer = await memberAnswer(sessionId, clean);
      setItems((current) => {
        const next = [...current];
        const stamp = Date.now();
        if (answer.kind === "price" && answer.price) {
          const price = answer.price;
          next.push({
            kind: "quote",
            id: `p-${stamp}`,
            amount: price.available ? price.price_display : undefined,
            headline: priceHeadline(price),
            details: [price.available ? "Covered on your plan" : "", price.tier_label, price.coverage_stage],
            note: price.note,
            withheld: price.withheld_reason || (!price.available && !price.note ? "That option is not available on your plan." : ""),
            units: answer.units?.length ? answer.units : price.units,
          });
          if (answer.chips?.length) next.push({ kind: "chips", id: `chips-${stamp}`, labels: answer.chips.slice(0, 3) });
          next.push({ kind: "help", id: `help-${stamp}`, question: clean, unitId: (price.units[0] || { unit_id: "" }).unit_id });
          return next;
        }
        if (answer.kind === "visit_cost" && answer.visit_cost) {
          const cost = answer.visit_cost;
          next.push({
            kind: "quote",
            id: `v-${stamp}`,
            amount: cost.available ? cost.cost_display : undefined,
            headline: visitHeadline(cost),
            note: cost.note,
            withheld: cost.withheld_reason || (!cost.available && !cost.note ? "That visit is not covered on your plan." : ""),
            units: answer.units?.length ? answer.units : cost.units,
          });
          if (answer.chips?.length) next.push({ kind: "chips", id: `chips-${stamp}`, labels: answer.chips.slice(0, 3) });
          next.push({ kind: "help", id: `help-${stamp}`, question: clean, unitId: (cost.units[0] || { unit_id: "" }).unit_id });
          return next;
        }
        if ((answer.kind === "clarify" || answer.kind === "handoff_offer") && answer.chips?.length) {
          next.push({ kind: "message", id: `c-${stamp}`, from: "bot", text: answer.reply || "Which of these do you mean?" });
          next.push({ kind: "chips", id: `chips-${stamp}`, labels: answer.chips.slice(0, 4) });
          return next;
        }
        if (answer.kind === "out_of_scope") {
          next.push({ kind: "message", id: `o-${stamp}`, from: "bot", text: answer.reply || NO_ANSWER });
          next.push({ kind: "handoff", id: `h-${stamp}` });
          return next;
        }
        if (answer.kind === "safety") {
          // Emergency and crisis language: the approved safety wording, with no "did this help" and no topic chips.
          const unit = answer.units?.[0];
          next.push({
            kind: "message",
            id: `s-${stamp}`,
            from: "bot",
            tone: "urgent",
            text: answer.member_text || answer.reply || "",
            citation: unit ? { title: plainMemberTitle(unit.title), date: "" } : undefined,
          });
          return next;
        }
        if (answer.kind === "plan_figure" && answer.reply) {
          // A plan figure travels with its approved disclaimer, the same way a price does.
          next.push({
            kind: "quote",
            id: `pf-${stamp}`,
            amount: /\$[\d,]+(?:\.\d{2})?/.exec(answer.reply)?.[0],
            headline: answer.reply,
            units: answer.units ?? [],
          });
          next.push({ kind: "help", id: `help-${stamp}`, question: clean, unitId: (answer.units?.[0] || { unit_id: "" }).unit_id });
          return next;
        }
        if (answer.abstained || !answer.member_text) {
          const labels = answer.suggestions?.length
            ? answer.suggestions.slice(0, 4)
            : clarifyLabels(clean, topics.data ?? []);
          if (labels.length >= 2) {
            const names = labels.map((label) => label.toLowerCase()).join(" or ");
            next.push({
              kind: "message",
              id: `c-${Date.now()}`,
              from: "bot",
              text: `I want to give you the right answer. Is this about ${names}?`,
            });
            next.push({ kind: "chips", id: `chips-${Date.now()}`, labels });
          } else {
            next.push({ kind: "message", id: `a-${Date.now()}`, from: "bot", text: NO_ANSWER });
            next.push({ kind: "handoff", id: `h-${Date.now()}` });
          }
        } else {
          next.push({
            kind: "message",
            id: `a-${Date.now()}`,
            from: "bot",
            text: answer.member_text,
            citation: { title: plainMemberTitle(answer.title), date: memberUpdated(answer) },
          });
          // The caregiver rule states a requirement; give the next step to meet it.
          if (answer.unit_id === CAREGIVER_UNIT && onAddCaller) {
            next.push({ kind: "chips", id: `caller-${Date.now()}`, labels: [ADD_CALLER] });
          }
          next.push({
            kind: "help",
            id: `help-${Date.now()}`,
            question: clean,
            unitId: answer.unit_id,
          });
        }
        return next;
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Try again.";
      setItems((current) => [...current, { kind: "message", id: `err-${Date.now()}`, from: "bot", text: message }]);
    } finally {
      setPending(false);
    }
  }

  function onChip(label: string) {
    if (label === "Talk to a member advocate") {
      onHandoff();
      return;
    }
    if (label === ADD_CALLER && onAddCaller) {
      onAddCaller();
      return;
    }
    if (label === "See my recent claims") {
      void showClaims();
      return;
    }
    const topic = topics.data?.find((item) => item.label === label);
    void ask(topic?.question || label);
  }

  async function showClaims() {
    setItems((current) => [
      ...current.filter((item) => item.kind !== "chips"),
      { kind: "message", id: `q-${Date.now()}`, from: "member", text: "See my recent claims" },
    ]);
    try {
      const profile = await memberProfile();
      const lines = (profile.claims ?? [])
        .map((claim) => `${readableDate(claim.date)}: ${claim.provider_type}, you paid ${claim.member_paid_display} (${claim.status.toLowerCase()})`)
        .join("; ");
      setItems((current) => [
        ...current,
        { kind: "message", id: `cl-${Date.now()}`, from: "bot", text: lines ? `Your recent claims: ${lines}. Illustrative.` : "You have no recent claims." },
        { kind: "handoff", id: `h-${Date.now()}` },
      ]);
    } catch (error) {
      const message = error instanceof Error ? error.message : "Try again.";
      setItems((current) => [...current, { kind: "message", id: `err-${Date.now()}`, from: "bot", text: message }]);
    }
  }

  async function onHelp(yes: boolean) {
    const help = [...items].reverse().find((item) => item.kind === "help");
    if (!yes && sessionId && help && help.kind === "help") {
      try {
        await sendFeedback(sessionId, {
          source: "channel",
          role: "Member",
          kind: "not_helpful",
          question: help.question,
          unit_id: help.unitId,
          note: "Member tapped No on Did that answer help?",
        });
      } catch (error) {
        const message = error instanceof Error ? error.message : "Try again.";
        setItems((current) => [...current, { kind: "message", id: `fb-${Date.now()}`, from: "bot", text: message }]);
        return;
      }
    }
    setItems((current) => {
      const next = current.filter((item) => item.kind !== "help");
      if (!yes) {
        next.push({ kind: "message", id: `sorry-${Date.now()}`, from: "bot", text: "Thanks for telling us. Would you like to talk to a member advocate?" });
        next.push({ kind: "handoff", id: `h-${Date.now()}` });
      }
      return next;
    });
    showUndoToast({
      message: yes ? "Thanks. That helps the knowledge team." : "Thanks. Your feedback goes to the knowledge team.",
    });
  }

  function onHandoff() {
    setItems((current) => [
      ...current.filter((item) => item.kind !== "handoff"),
      { kind: "message", id: `advocate-${Date.now()}`, from: "bot", text: "A member advocate can take this from here. Call 1-800-555-0148, 8 AM to 8 PM, seven days a week. Hours are illustrative." },
    ]);
  }

  return { items, pending, ask, onChip, onHelp, onHandoff, topics };
}
