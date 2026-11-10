import { ReactNode } from "react";
import { api, Project } from "../api";

type Act = (action: string, body?: unknown) => void;
type Guard = (fn: () => Promise<unknown>) => void;
type CardProps = { p: Project; act: Act; guard: Guard };

const Shell = ({ title, children }: { title: string; children: ReactNode }) => (
  <div className="card">
    <h4>{title}</h4>
    {children}
  </div>
);

const Chip = ({ label }: { label: string }) => <span className={"chip " + label}>{label}</span>;

function ReferenceUpload({ p, guard }: CardProps) {
  if (p.state !== "ANALYZING" || !p.error?.needs_file) return <Shell title="Reference file"><small>Received.</small></Shell>;
  return (
    <Shell title="Upload the reference video">
      <input type="file" accept="video/*,image/*" onChange={(e) => e.target.files?.[0] && guard(() => api.uploadReference(p.id, e.target.files![0]))} />
    </Shell>
  );
}

function BriefCard({ p, act }: CardProps) {
  const b = p.brief;
  if (!b) return null;
  return (
    <Shell title="Creative brief">
      <dl>
        <dt>About</dt><dd>{b.topic}</dd>
        <dt>Keep</dt><dd>{b.keep.join("; ") || "-"}</dd>
        <dt>Change</dt><dd>{b.change.join("; ") || "-"}</dd>
        <dt>Length</dt><dd>{b.target_length}s</dd>
        <dt>Tone</dt><dd>{b.tone}</dd>
        <dt>Captions</dt><dd>{b.captions ? b.caption_language : "off"}</dd>
        <dt>Music</dt><dd>{({ uploaded: "your audio file", reference: "the reference Reel's song", none: "none" } as Record<string, string>)[b.music]}</dd>
      </dl>
      <small>Tell me in chat what to change, e.g. "make it about my bakery, under 20 seconds".</small>
      {p.state === "BRIEF" && <div className="actions"><button className="primary" onClick={() => act("confirm-brief")}>Confirm brief</button></div>}
    </Shell>
  );
}

const ANIM: Record<string, string> = { none: "static", zoom_in: "slow zoom in", zoom_out: "slow zoom out" };
const CAPANIM: Record<string, string> = { none: "appears", fade: "fades in", pop: "pops in", slide_up: "slides up" };

function ShotsCard({ p, act }: CardProps) {
  return (
    <Shell title={`Shot list (${(p.shots ?? []).length})`}>
      <ol className="shots">
        {(p.shots ?? []).map((s: Project) => (
          <li key={s.shot_id} className={s.skipped ? "skipped" : ""}>
            <b>{s.purpose}</b> <small>{s.start}–{s.end}s · {s.asset_type}</small>
            <div>{s.subject}: {s.action}</div>
            <dl className="details">
              <dt>Background</dt>
              <dd>{s.background || "-"} <small>({s.fit === "blur_fit" ? "whole picture over a blurred backdrop" : "fills the frame"})</small></dd>
              <dt>Animation</dt>
              <dd>{ANIM[s.animation] ?? s.animation}</dd>
              <dt>Transition</dt>
              <dd>{s.transition_out === "cut" ? "hard cut" : `${s.transition_out} (0.4 s)`} into the next shot</dd>
              {s.text && (
                <>
                  <dt>Caption</dt>
                  <dd>
                    “{s.text}” <small>({CAPANIM[s.caption_animation] ?? s.caption_animation})</small>
                    <br />
                    <small>
                      <span className="swatch" style={{ background: s.caption_style?.color }} /> {s.caption_style?.font}, {s.caption_style?.size}px,{" "}
                      {s.caption_style?.position}{s.caption_style?.uppercase ? ", caps" : ""}
                      {s.caption_style?.emphasis_words?.length ? `, emphasis: ${s.caption_style.emphasis_words.join(", ")}` : ""}
                      {s.caption_start != null ? ` · on screen ${s.caption_start}–${s.caption_end}s into the shot` : ""}
                    </small>
                  </dd>
                </>
              )}
              {s.grade && !(s.grade.preset === "none" && s.grade.brightness === 0 && s.grade.contrast === 1 && s.grade.saturation === 1) && (
                <>
                  <dt>Colour</dt>
                  <dd>
                    {s.grade.preset !== "none" ? `${s.grade.preset} look` : "custom"} <small>(brightness {s.grade.brightness}, contrast {s.grade.contrast}, saturation {s.grade.saturation})</small>
                  </dd>
                </>
              )}
              {s.layout === "collage" && (
                <>
                  <dt>Layout</dt>
                  <dd>
                    collage of {s.collage?.tiles} pictures on <span className="swatch" style={{ background: s.collage?.background }} /> {s.collage?.background}
                    <small> ({s.collage?.border ? "framed" : "no frames"}, {s.collage?.tilt ? `tilted ${s.collage.tilt}°` : "straight"})</small>
                  </dd>
                </>
              )}
              {s.overlay && s.overlay.toLowerCase() !== "none" && (<><dt>Overlay</dt><dd>{s.overlay} <small>(shown for reference, not rendered yet)</small></dd></>)}
            </dl>
            <button className="link" onClick={() => act("skip-shot", { shot_id: s.shot_id, skip: !s.skipped })}>{s.skipped ? "restore" : "drop"}</button>
          </li>
        ))}
      </ol>
      {p.state === "SHOT_SPECS" && <div className="actions"><button className="primary" onClick={() => act("confirm-shots")}>Looks good, find my clips</button></div>}
    </Shell>
  );
}

function MatchesCard({ p, act }: CardProps) {
  const rows = p.summary?.rows ?? [];
  const clips = (p.assets ?? []).filter((a: Project) => a.kind === "clip" && ["ready", "too_short"].includes(a.status));
  const editable = ["AWAITING_UPLOADS", "AWAITING_APPROVAL"].includes(p.state);
  return (
    <Shell title="Matches">
      <table>
        <tbody>
          {rows.filter((r: Project) => !r.skipped).map((r: Project) => (
            <tr key={r.shot_id}>
              <td>{r.shot_id}. {r.purpose}</td>
              <td><Chip label={r.label} /></td>
              <td>{r.clip ?? "-"}{r.tiles > 0 && ` +${r.tiles} more`}<br /><small>{r.reason}</small></td>
              <td>
                {editable && clips.length > 0 && (
                  <select value="" onChange={(e) => e.target.value && act("swap-clip", { shot_id: r.shot_id, asset_id: e.target.value })}>
                    <option value="">swap…</option>
                    {clips.map((c: Project) => <option key={c.id} value={c.id}>{c.filename}</option>)}
                  </select>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </Shell>
  );
}

function FilmCard({ p, act, guard }: CardProps) {
  const missing = (p.matches ?? []).filter((m: Project) => m.label === "missing" && !p.shots.find((s: Project) => s.shot_id === m.shot_id)?.skipped);
  if (!missing.length) return <Shell title="Film these"><small>Nothing left to film.</small></Shell>;
  return (
    <Shell title={`Film these ${missing.length}`}>
      {missing.map((m: Project) => (
        <div key={m.shot_id} className="film">
          <div><b>Shot {m.shot_id}</b>: {m.instruction || m.reason}</div>
          <input type="file" accept="video/*,image/*" onChange={(e) => e.target.files?.[0] && guard(() => api.upload(p.id, e.target.files![0], "clip", m.shot_id))} />
          <button className="link" onClick={() => act("skip-shot", { shot_id: m.shot_id })}>skip this shot</button>
        </div>
      ))}
      <div className="actions"><button onClick={() => act("skip-missing")}>Skip all remaining</button></div>
    </Shell>
  );
}

function ApprovalCard({ p, act }: CardProps) {
  const s = p.summary;
  if (!s) return null;
  const ready = p.state === "AWAITING_APPROVAL";
  return (
    <Shell title="Approve your Reel">
      <p>{p.brief.topic}: about {s.duration}s, {s.captions ? "with captions" : "no captions"}, music: {({ uploaded: "your file", reference: "reference song, cuts on the beat", none: "none" } as Record<string, string>)[s.music]}.</p>
      <table>
        <tbody>
          {s.rows.map((r: Project) => (
            <tr key={r.shot_id} className={r.skipped ? "skipped" : ""}>
              <td>{r.shot_id}. {r.purpose}</td>
              <td>{r.skipped ? "skipped" : <Chip label={r.label} />}</td>
              <td>{r.clip ?? "-"}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {p.approved ? <small>Approved.</small> : (
        <div className="actions"><button className="primary" disabled={!ready} onClick={() => act("approve")}>Approve and build</button></div>
      )}
    </Shell>
  );
}

function ProgressCard({ p }: CardProps) {
  return (
    <Shell title="Building">
      <ul className="progress">
        {(p.progress ?? []).map((n: Project) => (
          <li key={n.node}><Chip label={n.status} /> {n.node}{n.cached ? " (cached)" : ""}</li>
        ))}
      </ul>
    </Shell>
  );
}

function VideoCard({ p }: CardProps) {
  if (!p.final_path) return null;
  return (
    <Shell title={`Draft v${p.draft_n}`}>
      <video src={api.videoUrl(p.id, p.draft_n)} controls playsInline />
    </Shell>
  );
}

function FinalCard({ p }: CardProps) {
  if (p.state !== "FINAL") return null;
  return (
    <Shell title="Final Reel">
      <video src={api.videoUrl(p.id, p.draft_n)} controls playsInline />
      <div className="actions"><a className="button primary" href={api.videoUrl(p.id, p.draft_n, true)} download>Download MP4</a></div>
    </Shell>
  );
}

function VerifierCard({ p }: CardProps) {
  const v = p.verifier;
  if (!v) return null;
  return (
    <details className="card">
      <summary>Verifier report: <b>{v.verdict}</b> (draft {v.draft}, {v.round} repair round{v.round === 1 ? "" : "s"})</summary>
      <p>{v.summary}</p>
      <ul>{Object.entries(v.tech ?? {}).map(([k, c]) => <li key={k}><Chip label={(c as Project).ok ? "done" : "failed"} /> {k}: {(c as Project).detail}</li>)}</ul>
      {v.content && <p><small>Content check: {JSON.stringify(v.content)}</small></p>}
      {v.issues?.map((i: Project, n: number) => <p key={n}>• {i.problem}</p>)}
    </details>
  );
}

const CARDS: Record<string, (p: CardProps) => ReactNode> = {
  reference_upload: ReferenceUpload, brief: BriefCard, shots: ShotsCard, matches: MatchesCard, film: FilmCard,
  approval: ApprovalCard, progress: ProgressCard, video: VideoCard, final: FinalCard, verifier: VerifierCard,
};

export default function Card({ type, p, latest, act, guard }: { type: string; p: Project; latest: boolean; act: Act; guard: Guard }) {
  if (!latest) return <div className="card old"><small>{type.replace("_", " ")} card (updated below)</small></div>;
  const C = CARDS[type];
  return C ? <>{C({ p, act, guard })}</> : null;
}
