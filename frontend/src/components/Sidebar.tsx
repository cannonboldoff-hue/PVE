import { Conv } from "../api";

type Props = { convs: Conv[]; current: string | null; onSelect: (id: string) => void; onNew: () => void; onDelete: (id: string) => void };

export default function Sidebar({ convs, current, onSelect, onNew, onDelete }: Props) {
  return (
    <aside className="sidebar">
      <button className="new" onClick={onNew}>+ New Reel</button>
      {convs.map((c) => (
        <div key={c.id} className={"conv" + (c.id === current ? " active" : "")} onClick={() => onSelect(c.id)}>
          <span>{c.title}</span>
          <small>{c.state.toLowerCase().replace("_", " ")}</small>
          <button
            className="del"
            title="Delete project"
            onClick={(e) => {
              e.stopPropagation();
              if (confirm("Delete this project and its renders? Your uploaded clips stay in the library.")) onDelete(c.id);
            }}
          >
            ×
          </button>
        </div>
      ))}
    </aside>
  );
}
