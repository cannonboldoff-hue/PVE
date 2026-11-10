import { useCallback, useEffect, useRef, useState } from "react";
import { api, Conv, Msg, Project } from "./api";
import Composer from "./components/Composer";
import Sidebar from "./components/Sidebar";
import Thread from "./components/Thread";

export default function App() {
  const [convs, setConvs] = useState<Conv[]>([]);
  const [cid, setCid] = useState<string | null>(null);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [project, setProject] = useState<Project | null>(null);
  const [live, setLive] = useState("");
  const [error, setError] = useState("");
  const conv = convs.find((c) => c.id === cid);
  const timer = useRef<number>();

  const loadConvs = useCallback(async () => {
    const list = await api.conversations();
    setConvs(list);
    return list;
  }, []);

  const create = useCallback(async () => {
    const c = await api.newConversation();
    await loadConvs();
    setCid(c.id);
  }, [loadConvs]);

  useEffect(() => {
    loadConvs().then((list) => (list.length ? setCid(list[0].id) : create()));
  }, [loadConvs, create]);

  const pid = conv?.project_id;
  const refresh = useCallback(() => {
    window.clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      if (pid) api.project(pid).then(setProject).catch(() => {});
    }, 150);
  }, [pid]);

  // load the thread, then follow it over SSE
  useEffect(() => {
    if (!cid || !pid) return;
    setMessages([]);
    setProject(null);
    setLive("");
    api.messages(cid).then(setMessages);
    api.project(pid).then(setProject);
    const es = new EventSource(`/api/conversations/${cid}/events`);
    es.onmessage = (e) => {
      const ev = JSON.parse(e.data);
      if (ev.type === "message") {
        const m: Msg = ev.message;
        setMessages((ms) => (ms.some((x) => x.id === m.id) ? ms : [...ms, m]));
        if (m.role === "assistant") setLive("");
        refresh();
        loadConvs();
      } else if (ev.type === "token") setLive((t) => t + ev.text);
      else if (ev.type === "project") refresh();
    };
    return () => es.close();
  }, [cid, pid, refresh, loadConvs]);

  const guard = async (fn: () => Promise<unknown>) => {
    setError("");
    try {
      await fn();
    } catch (e) {
      setError((e as Error).message);
    }
    refresh();
  };

  return (
    <div className="app">
      <Sidebar
        convs={convs}
        current={cid}
        onSelect={setCid}
        onNew={create}
        onDelete={async (id) => {
          await api.deleteConversation(id);
          const list = await loadConvs();
          if (id === cid) list.length ? setCid(list[0].id) : create();
        }}
      />
      <main className="main">
        <Thread messages={messages} project={project} live={live} act={(a, b) => guard(() => api.act(pid!, a, b))} guard={guard} />
        {error && <div className="error">{error}</div>}
        {pid && <Composer pid={pid} guard={guard} onSend={(t) => guard(() => api.say(cid!, t))} />}
      </main>
    </div>
  );
}
