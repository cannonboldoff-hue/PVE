export type Msg = { id: number; role: "user" | "assistant"; kind: "text" | "card"; content: string; card: { type: string; project_id: string } | null };
// eslint-disable-next-line @typescript-eslint/no-explicit-any
export type Project = Record<string, any>;
export type Conv = { id: string; title: string; project_id: string; state: string };

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  const r = await fetch("/api" + path, init);
  const body = await r.json().catch(() => ({}));
  if (!r.ok) throw new Error(body.error || body.detail || r.statusText);
  return body;
}

const post = (path: string, body?: unknown) =>
  call<{ message?: string }>(path, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body ?? {}),
  });

export const api = {
  conversations: () => call<Conv[]>("/conversations"),
  newConversation: () => call<{ id: string; project_id: string }>("/conversations", { method: "POST" }),
  deleteConversation: (id: string) => call("/conversations/" + id, { method: "DELETE" }),
  templates: () => call<{ key: string; title: string; shots: number; seconds: number }[]>("/templates"),
  messages: (id: string) => call<Msg[]>(`/conversations/${id}/messages`),
  say: (id: string, text: string) => post(`/conversations/${id}/messages`, { text }),
  project: (pid: string) => call<Project>("/projects/" + pid),
  act: (pid: string, action: string, body?: unknown) => post(`/projects/${pid}/${action}`, body),
  upload: (pid: string, file: File, kind: "clip" | "music", shotId?: number) => {
    const f = new FormData();
    f.append("file", file);
    f.append("project_id", pid);
    f.append("kind", kind);
    if (shotId !== undefined) f.append("shot_id", String(shotId));
    return call("/assets", { method: "POST", body: f });
  },
  uploadReference: (pid: string, file: File) => {
    const f = new FormData();
    f.append("file", file);
    return call(`/projects/${pid}/reference-file`, { method: "POST", body: f });
  },
  deleteAsset: (id: string) => call("/assets/" + id, { method: "DELETE" }),
  videoUrl: (pid: string, v: number, download = false) => `/api/projects/${pid}/video?v=${v}${download ? "&download=1" : ""}`,
};
