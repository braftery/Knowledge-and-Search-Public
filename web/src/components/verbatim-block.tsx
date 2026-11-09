import type { ReactNode } from "react";
import { Lock } from "lucide-react";
import { Icon } from "@/components/icon";

type VerbatimBlockProps = {
  text?: string;
  children?: ReactNode;
};

export function VerbatimBlock({ text, children }: VerbatimBlockProps) {
  return (
    <div className="hh-verbatim">
      <div className="hh-verbatim__head">
        <Icon icon={Lock} />
        Read to member, word for word
      </div>
      <div className="hh-verbatim__text">{children ?? text}</div>
    </div>
  );
}
