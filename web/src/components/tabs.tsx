import { useRef, type KeyboardEvent, type ReactNode } from "react";

export type TabItem = {
  id: string;
  label: string;
  count?: number;
};

type TabsProps = {
  tabs: TabItem[];
  value: string;
  onChange: (id: string) => void;
  label: string;
  children?: ReactNode;
};

export function Tabs({ tabs, value, onChange, label, children }: TabsProps) {
  const listRef = useRef<HTMLDivElement>(null);

  function onKeyDown(event: KeyboardEvent<HTMLButtonElement>, index: number) {
    const horizontal = event.key === "ArrowRight" || event.key === "ArrowLeft";
    const edge = event.key === "Home" || event.key === "End";
    if (!horizontal && !edge) return;
    event.preventDefault();
    const last = tabs.length - 1;
    let next = index;
    if (event.key === "ArrowRight") next = index === last ? 0 : index + 1;
    if (event.key === "ArrowLeft") next = index === 0 ? last : index - 1;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = last;
    onChange(tabs[next].id);
    const buttons = listRef.current?.querySelectorAll<HTMLButtonElement>('[role="tab"]');
    buttons?.[next]?.focus();
  }

  return (
    <div>
      <div className="hh-tabs" role="tablist" aria-label={label} ref={listRef}>
        {tabs.map((tab, index) => {
          const selected = tab.id === value;
          return (
            <button
              key={tab.id}
              className="hh-tab"
              role="tab"
              type="button"
              id={`tab-${tab.id}`}
              aria-selected={selected}
              aria-controls={selected && children ? `panel-${tab.id}` : undefined}
              tabIndex={selected ? 0 : -1}
              onClick={() => onChange(tab.id)}
              onKeyDown={(event) => onKeyDown(event, index)}
            >
              {tab.label}
              {typeof tab.count === "number" ? <span className="hh-count">{tab.count}</span> : null}
            </button>
          );
        })}
      </div>
      {children ? (
        <div role="tabpanel" id={`panel-${value}`} aria-labelledby={`tab-${value}`}>
          {children}
        </div>
      ) : null}
    </div>
  );
}
