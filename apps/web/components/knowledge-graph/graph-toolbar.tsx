"use client";

type Props = {
  search: string;
  onSearch: (value: string) => void;
  onFit: () => void;
  onReset: () => void;
  onRelayout: () => void;
  labels: { search: string; fit: string; reset: string; relayout: string };
};

export function GraphToolbar({ search, onSearch, onFit, onReset, onRelayout, labels }: Props) {
  return (
    <div className="graph-toolbar">
      <input
        value={search}
        onChange={(event) => onSearch(event.target.value)}
        placeholder={labels.search}
        aria-label={labels.search}
      />
      <button className="secondary" onClick={onFit}>{labels.fit}</button>
      <button className="secondary" onClick={onReset}>{labels.reset}</button>
      <button className="secondary" onClick={onRelayout}>{labels.relayout}</button>
    </div>
  );
}
