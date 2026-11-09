import type { ReactNode } from "react";

export type Column<Row> = {
  id: string;
  header: string;
  numeric?: boolean;
  render: (row: Row) => ReactNode;
};

type DataTableProps<Row> = {
  columns: Column<Row>[];
  rows: Row[];
  getId: (row: Row) => string;
  selectedId?: string;
  onSelect?: (id: string) => void;
  caption: string;
};

export function DataTable<Row>({ columns, rows, getId, selectedId, onSelect, caption }: DataTableProps<Row>) {
  return (
    <table className="hh-table">
      <caption className="sr-only">{caption}</caption>
      <thead>
        <tr>
          {columns.map((column) => (
            <th key={column.id} className={column.numeric ? "num" : undefined} scope="col">
              {column.header}
            </th>
          ))}
        </tr>
      </thead>
      <tbody>
        {rows.map((row) => {
          const id = getId(row);
          const selected = id === selectedId;
          return (
            <tr
              key={id}
              aria-selected={selected}
              tabIndex={0}
              onClick={() => onSelect?.(id)}
              onKeyDown={(event) => {
                if (event.key === "Enter" || event.key === " ") {
                  event.preventDefault();
                  onSelect?.(id);
                }
              }}
              style={{ cursor: onSelect ? "pointer" : undefined }}
            >
              {columns.map((column) => (
                <td key={column.id} className={column.numeric ? "num" : undefined}>
                  {column.render(row)}
                </td>
              ))}
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
