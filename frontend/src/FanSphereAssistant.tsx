import { FormEvent, useEffect, useRef, useState } from "react";
import { Bot, MessageCircle, Send, Sparkles, X } from "lucide-react";
import "./fansphere-assistant.css";

type ChatMessage = { role: "user" | "assistant"; content: string };
let sharedMessages: ChatMessage[] = [];
const chatListeners = new Set<(messages: ChatMessage[]) => void>();
function appendMessage(message: ChatMessage) { sharedMessages = [...sharedMessages, message]; chatListeners.forEach(listener => listener(sharedMessages)); }
const STARTERS = ["How does Daily Quiz work?", "Explain my XP and Gems", "Help me understand match predictions"];
export default function FanSphereAssistant({ fullPage = false }: { fullPage?: boolean }) {
  const [open, setOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>(sharedMessages);
  useEffect(() => { chatListeners.add(setMessages); return () => { chatListeners.delete(setMessages); }; }, []);
  const [draft, setDraft] = useState("");
  const [busy, setBusy] = useState(false);
  const bottom = useRef<HTMLDivElement>(null);
  useEffect(() => { bottom.current?.scrollIntoView({ behavior: "smooth", block: "nearest" }); }, [messages, busy, open]);
  async function send(event?: FormEvent, suggested?: string) {
    event?.preventDefault();
    const message = (suggested ?? draft).trim();
    if (!message || busy) return;
    const history = messages.slice(-10);
    appendMessage({ role: "user", content: message });
    setDraft(""); setBusy(true);
    try {
      const response = await fetch("/api/v1/chat", {
        method: "POST", credentials: "include", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message, history }),
      });
      const data = await response.json();
      if (!response.ok) throw new Error(typeof data.detail === "string" ? data.detail : "Chat unavailable.");
      appendMessage({ role: "assistant", content: data.reply });
    } catch (error) {
      appendMessage({ role: "assistant", content: error instanceof Error ? error.message : "Chat unavailable. Try again." });
    } finally { setBusy(false); }
  }
  const visible = fullPage || open;
  return <div className={fullPage ? "fs-assistant-page" : "fs-assistant-floating"}>
    {!fullPage && <button className="fs-chat-launcher" type="button" onClick={() => setOpen(!open)} aria-label={open ? "Close FanSphere AI" : "Open FanSphere AI"}>{open ? <X size={23}/> : <MessageCircle size={24}/>}</button>}
    {visible && <section className="fs-chat-panel" aria-label="FanSphere AI Assistant">
      <header className="fs-chat-header"><div className="fs-chat-avatar"><Bot size={22}/></div><div><strong>FanSphere AI</strong><span><Sparkles size={12}/> Your football companion</span></div>{!fullPage && <button type="button" onClick={() => setOpen(false)} aria-label="Close chat"><X size={19}/></button>}</header>
      <div className="fs-chat-messages" aria-live="polite">
        <div className="fs-chat-intro"><div className="fs-chat-intro-icon"><Sparkles size={24}/></div><h3>What can I help you with?</h3><p>Ask about football, your fan journey, quizzes, XP, or how to use FanSphere.</p></div>
        {messages.length === 0 && <div className="fs-chat-starters">{STARTERS.map(q => <button key={q} type="button" onClick={() => void send(undefined, q)}>{q}</button>)}</div>}
        {messages.map((m, i) => <div key={i} className={`fs-chat-bubble ${m.role}`}>{m.content}</div>)}
        {busy && <div className="fs-chat-bubble assistant">Thinking…</div>}
        <div ref={bottom}/>
      </div>
      <form className="fs-chat-compose" onSubmit={e => void send(e)}><input aria-label="Message FanSphere AI" value={draft} onChange={e => setDraft(e.target.value)} maxLength={2000} placeholder="Ask me anything about football…" disabled={busy}/><button type="submit" disabled={busy || !draft.trim()} aria-label="Send message"><Send size={19}/></button></form>
      <div className="fs-chat-disclaimer">AI responses may be inaccurate. Live match data isn't connected to chat.</div>
    </section>}
  </div>;
}
