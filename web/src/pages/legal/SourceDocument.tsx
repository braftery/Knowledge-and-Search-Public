import { useEffect } from "react";
import { getDocument, type World } from "@/api/guided";
import { useQuery } from "@/api/use-query";
import { Skeleton } from "@/components/skeleton";
import { NumberedSource } from "@/pages/demo/chrome";

/**
 * The whole source document behind a unit, with the unit's passage highlighted, so the approver reads the wording in
 * its original context, not only the extracted sentence.
 */
export function SourceDocument({
  docId,
  quote,
  world = "guided",
  caption = "The highlighted passage is the one this unit was extracted from.",
}: {
  docId: string;
  quote: string;
  world?: World;
  caption?: string;
}) {
  const doc = useQuery(`source-doc:${world}:${docId}`, () => getDocument(docId, world), Boolean(docId));
  useEffect(() => {
    if (!doc.data) return;
    const mark = document.getElementById("src-1");
    const panel = mark?.closest(".source-doc") as HTMLElement | null;
    if (mark && panel) {
      const offset = mark.getBoundingClientRect().top - panel.getBoundingClientRect().top;
      panel.scrollTo({ top: Math.max(0, panel.scrollTop + offset - 48) });
    }
  }, [doc.data, quote]);
  if (!docId) return null;
  if (doc.loading && !doc.data) return <Skeleton width="100%" height="160px" label="Loading the original document" />;
  if (!doc.data) return <p className="hh-meta">The original document could not be loaded.</p>;
  return (
    <section className="legal-source" aria-label="Original document">
      <h3 className="tools-label">
        Original document: {doc.data.name || doc.data.title}
        {doc.data.legal_signed ? <span className="hh-meta"> · {doc.data.legal_signed}</span> : null}
      </h3>
      <NumberedSource body={doc.data.body} quotes={quote ? [{ number: 1, quote }] : []} active={1} />
      <p className="hh-meta">{caption}</p>
    </section>
  );
}
