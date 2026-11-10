import { useRef, useState } from "react";
import { api } from "../api";

type Props = { pid: string; guard: (fn: () => Promise<unknown>) => void; onSend: (text: string) => void };

export default function Composer({ pid, guard, onSend }: Props) {
  const [text, setText] = useState("");
  const file = useRef<HTMLInputElement>(null);

  const send = () => {
    if (!text.trim()) return;
    onSend(text.trim());
    setText("");
  };
  // audio files become the soundtrack, everything else is a clip for the library
  const upload = (files: FileList | null) =>
    files && [...files].forEach((f) => guard(() => api.upload(pid, f, f.type.startsWith("audio/") ? "music" : "clip")));

  return (
    <div
      className="composer"
      onDragOver={(e) => e.preventDefault()}
      onDrop={(e) => {
        e.preventDefault();
        upload(e.dataTransfer.files);
      }}
    >
      <input ref={file} type="file" multiple accept="video/*,image/*,audio/*" hidden onChange={(e) => upload(e.target.files)} />
      <button title="Add clips, photos or music" onClick={() => file.current?.click()}>📎</button>
      <textarea
        rows={1}
        value={text}
        placeholder="Paste a Reel link, drop clips here, or tell me what to change…"
        onChange={(e) => setText(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === "Enter" && !e.shiftKey) {
            e.preventDefault();
            send();
          }
        }}
      />
      <button className="send" onClick={send}>Send</button>
    </div>
  );
}
