import { FormEvent, useEffect, useRef, useState } from "react";
import { ChevronDown, LogOut, UserRound } from "lucide-react";

export default function AccountMenu({ name, email, onSignOut }: { name: string; email: string; onSignOut: () => void }) {
  const [open, setOpen] = useState(false);
  const [section, setSection] = useState(false);
  const [changing, setChanging] = useState(false);
  const [current, setCurrent] = useState("");
  const [next, setNext] = useState("");
  const [confirm, setConfirm] = useState("");
  const [message, setMessage] = useState("");
  const [busy, setBusy] = useState(false);
  const root = useRef<HTMLDivElement>(null);
  useEffect(() => {
    if (!open) return;
    const outside = (event: MouseEvent) => { if (root.current && !root.current.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", outside);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", outside); document.removeEventListener("keydown", escape); };
  }, [open]);
  async function submit(event: FormEvent) {
    event.preventDefault();
    setMessage("");
    if (next !== confirm) { setMessage("New passwords do not match."); return; }
    if (next.length < 12) { setMessage("Use at least 12 characters."); return; }
    setBusy(true);
    try {
      const response = await fetch("/api/v1/auth/change-password", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ current_password: current, new_password: next }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Password change failed.");
      setMessage("Password changed successfully.");
      setCurrent(""); setNext(""); setConfirm(""); setChanging(false);
    } catch (error) { setMessage(error instanceof Error ? error.message : "Unable to update password."); }
    finally { setBusy(false); }
  }
  const actionStyle = { display: "flex", alignItems: "center", gap: 9, width: "100%", padding: "12px", border: 0,
    background: "transparent", color: "#e2edf7", textAlign: "left" as const, cursor: "pointer" };
  return <div ref={root} style={{ position: "relative", flexShrink: 0 }}>
    <button type="button" aria-label="Account menu" aria-expanded={open} onClick={() => setOpen(v => !v)}
      style={{ display: "flex", alignItems: "center", gap: 5, border: 0, padding: 0, background: "transparent", cursor: "pointer", color: "#a9c2d2" }}>
      <span className="avatar">{name.slice(0, 2).toUpperCase()}</span><ChevronDown size={14}/>
    </button>
    {open && <section className="premium-account-popover" role="dialog" aria-label="Account" style={{ position: "absolute", right: 0, top: "calc(100% + 14px)",
      width: "min(320px, 85vw)", maxHeight: "75vh", overflowY: "auto", zIndex: 120,
      border: "1px solid #315269", borderRadius: 14, padding: 10, background: "#0d2234",
      boxShadow: "0 16px 45px rgba(0,0,0,.4)", color: "#e2edf7" }}>
      <button className="premium-account-action" type="button" style={actionStyle} onClick={() => setSection(v => !v)}><UserRound size={17}/> User Info <ChevronDown size={14}/></button>
      {section && <div style={{ padding: "6px 12px 12px", fontSize: 13 }}>
        <div><strong>{name}</strong></div>
        <div style={{ color: "#a9c2d2", overflowWrap: "anywhere", marginTop: 5 }}>{email}</div>
        <div style={{ marginTop: 9, color: "#a9c2d2" }}>Password: ••••••••••••</div>
        <button type="button" onClick={() => { setChanging(v => !v); setMessage(""); }}
          style={{ color: "#7cf3c7", background: "transparent", border: 0, padding: "10px 0", cursor: "pointer" }}>Change password</button>
        {changing && <form onSubmit={submit} style={{ display: "grid", gap: 9 }}>
          <input type="password" autoComplete="current-password" placeholder="Current password" required value={current} onChange={e => setCurrent(e.target.value)} style={{ padding: 10, borderRadius: 7, width: "100%" }}/>
          <input type="password" autoComplete="new-password" placeholder="New password (12+ characters)" required minLength={12} value={next} onChange={e => setNext(e.target.value)} style={{ padding: 10, borderRadius: 7, width: "100%" }}/>
          <input type="password" autoComplete="new-password" placeholder="Confirm new password" required value={confirm} onChange={e => setConfirm(e.target.value)} style={{ padding: 10, borderRadius: 7, width: "100%" }}/>
          <button className="premium-account-save" type="submit" disabled={busy} style={{ padding: 10, borderRadius: 7, background: "#7cf3c7", color: "#0b2132", border: 0, fontWeight: 700, cursor: "pointer" }}>{busy ? "Saving…" : "Update password"}</button>
        </form>}
        {message && <p role="status" style={{ fontSize: 12, color: "#7cf3c7" }}>{message}</p>}
      </div>}
      <div style={{ borderTop: "1px solid #315269" }}/>
      <button className="premium-account-action" type="button" style={actionStyle} onClick={() => { setOpen(false); onSignOut(); }}><LogOut size={17}/> Sign Out</button>
    </section>}
  </div>;
}
