import { memberGlossary } from "@/api/client";
import { useQuery } from "@/api/use-query";
import { memberCite } from "@/components/quote-card";

/**
 * Plain-language meanings for the plan words on a page, from approved definitions. A disclosure keeps the page short;
 * the words stay one tap away for a member who meets "tier" or "coverage stage" for the first time.
 */
export function Glossary({ keys }: { keys: string[] }) {
  const glossary = useQuery("member-glossary", () => memberGlossary());
  const entries = (glossary.data?.entries ?? []).filter((entry) => keys.includes(entry.key));
  if (!entries.length) return null;
  return (
    <details className="member-glossary">
      <summary>What these words mean</summary>
      <dl>
        {entries.map((entry) => (
          <div key={entry.unit_id}>
            <dt>{capitalize((entry.title || "").replace(/^Definition of /, ""))}</dt>
            <dd>
              {entry.text}
              <span className="quote__cite">{memberCite({ unit_id: entry.unit_id, version: entry.version, title: entry.title || "", text: entry.text, citation: "" } as never)}</span>
            </dd>
          </div>
        ))}
      </dl>
    </details>
  );
}

const capitalize = (text: string) => (text ? text.charAt(0).toUpperCase() + text.slice(1) : text);
