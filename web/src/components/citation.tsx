import { FileText } from "lucide-react";
import { Icon } from "@/components/icon";
import { readableDate } from "@/lib/dates";

type CitationProps = {
  audience: "internal" | "member";
  title: string;
  version?: number;
  approver?: string;
  date: string;
  sourceHref?: string;
};

export function Citation({ audience, title, version, approver, date, sourceHref }: CitationProps) {
  if (audience === "member") {
    return (
      <div className="hh-cite">
        <Icon icon={FileText} />
        <span>
          Harbor Health plan rules: {title}
          {date ? `, updated ${readableDate(date)}` : ""}
        </span>
      </div>
    );
  }

  return (
    <div className="hh-cite">
      <Icon icon={FileText} />
      <span>
        {title}
        {version ? `, version ${version}` : ""}
        {approver ? `, approved by ${approver}` : ""} on {readableDate(date)}
        {sourceHref ? (
          <>
            {". "}
            <a href={sourceHref}>Open the source document</a>
          </>
        ) : null}
      </span>
    </div>
  );
}
