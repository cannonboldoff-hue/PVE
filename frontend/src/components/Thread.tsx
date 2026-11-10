import { useEffect, useRef } from "react";
import { Msg, Project } from "../api";
import Card from "./cards";

type Props = {
  messages: Msg[];
  project: Project | null;
  live: string;
  act: (action: string, body?: unknown) => void;
  guard: (fn: () => Promise<unknown>) => void;
};

export default function Thread({ messages, project, live, act, guard }: Props) {
  const end = useRef<HTMLDivElement>(null);
  useEffect(() => {
    end.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages.length, live, project?.state]);

  // only the newest card of each type is interactive; older ones point to it
  const lastOfType = new Map<string, number>();
  messages.forEach((m) => m.card && lastOfType.set(m.card.type, m.id));

  return (
    <div className="thread">
      {messages.map((m) =>
        m.kind === "card" && m.card ? (
          <div key={m.id} className="row assistant">
            {project ? (
              <Card type={m.card.type} p={project} latest={lastOfType.get(m.card.type) === m.id} act={act} guard={guard} />
            ) : null}
          </div>
        ) : (
          <div key={m.id} className={"row " + m.role}>
            <div className="bubble">{m.content}</div>
          </div>
        ),
      )}
      {live && (
        <div className="row assistant">
          <div className="bubble">{live}</div>
        </div>
      )}
      <div ref={end} />
    </div>
  );
}
