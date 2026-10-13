import { useEffect, useRef, useState } from "react";
import { Bell, Check, Gem, Sparkles, Trophy, Award, CalendarClock } from "lucide-react";

type Notice = { id: string; title: string; detail: string; page: string; icon: "quiz" | "level" | "gems" | "badge" | "match" };
type QuizStatus = { completed: boolean };
type LevelsStatus = { unlocked_level: number; selected_level?: number; levels: Array<{ level: number; rounds_completed: number; rounds_to_unlock_next: number }> };
type WalletStatus = { gems: number; spendable_xp: number; xp_per_gem: number };
type BadgeStatus = { achievements: { id: string; name: string; unlocked: boolean }[] };
type RewardHistory = { events: { id: string; currency: string; amount: number }[] };
type TeamProfile = { primary_team: { provider_id: string; name: string } | null; favorites: { provider_id: string; name: string }[] };

export default function NotificationBell({ userId, onNavigate }: { userId: number; onNavigate: (page: string) => void }) {
  const [open, setOpen] = useState(false);
  const [items, setItems] = useState<Notice[]>([]);
  const [read, setRead] = useState<string[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const root = useRef<HTMLDivElement>(null);
  const day = new Date().toLocaleDateString("en-CA");
  const storageKey = `fansphere-notifications-read:${userId}:${day}`;
  const snapshotKey = `fansphere-notification-snapshot:${userId}`;

  useEffect(() => {
    try { setRead(JSON.parse(localStorage.getItem(storageKey) || "[]")); }
    catch { setRead([]); }
  }, [storageKey]);

  async function refresh() {
    setLoading(true);
    setError("");
    try {
      const [quizResponse, levelResponse, walletResponse, badgeResponse, rewardResponse, profileResponse] = await Promise.all([
        fetch("/api/v1/quiz/daily"),
        fetch("/api/v1/quiz/levels"),
        fetch("/api/v1/economy"),
        fetch("/api/v1/profile/achievements"),
        fetch("/api/v1/economy/history"),
        fetch("/api/v1/profile"),
      ]);
      if (![quizResponse, levelResponse, walletResponse, badgeResponse, rewardResponse, profileResponse].every(r => r.ok)) throw new Error("Notifications could not be refreshed.");
      const quiz: QuizStatus = await quizResponse.json();
      const levels: LevelsStatus = await levelResponse.json();
      const wallet: WalletStatus = await walletResponse.json();
      const badges: BadgeStatus = await badgeResponse.json();
      const rewards: RewardHistory = await rewardResponse.json();
      const profile: TeamProfile = await profileResponse.json();
      const next: Notice[] = [];
      if (!quiz.completed) next.push({
        id: "daily-quiz", title: "Your daily quiz is ready",
        detail: "Five new questions are waiting.", page: "Daily Quiz", icon: "quiz",
      });
      const current = levels.levels.find(l => l.level === (levels.selected_level || levels.unlocked_level));
      if (current && current.level < levels.levels.length && current.rounds_to_unlock_next > 0 && current.rounds_to_unlock_next <= 2) {
        next.push({ id: `level-${current.level}-${current.rounds_completed}`,
          title: "You're close to the next level",
          detail: `${current.rounds_to_unlock_next} more rewarded round${current.rounds_to_unlock_next === 1 ? "" : "s"} to unlock Level ${current.level + 1}.`,
          page: "Daily Quiz", icon: "level" });
      }
      if (wallet.gems < 2 && wallet.spendable_xp >= wallet.xp_per_gem) {
        next.push({ id: "low-gems", title: "You can exchange XP for Gems",
          detail: `You have ${wallet.gems} Gems. Visit Wallet to exchange earned XP.`, page: "Wallet", icon: "gems" });
      }
      // Only notify on observed changes; the first check establishes a baseline.
      try {
        const unlocked = badges.achievements.filter(b => b.unlocked).map(b => b.id);
        const gemRewards = rewards.events.filter(e => e.currency === "GEM" && e.amount > 0);
        const previousText = localStorage.getItem(snapshotKey);
        const previous = previousText ? JSON.parse(previousText) : null;
        const events: Notice[] = (previous?.events || []).filter((n: Notice) => !read.includes(n.id));
        if (previous) {
          for (const badge of badges.achievements.filter(b => b.unlocked && !previous.badges.includes(b.id))) {
            events.push({ id: "badge-" + badge.id, title: "New badge unlocked", detail: badge.name, page: "Profile", icon: "badge" });
          }
          if (levels.unlocked_level > previous.level) {
            events.push({ id: "unlock-" + levels.unlocked_level, title: "Level unlocked!",
              detail: "Level " + levels.unlocked_level + " is now available.", page: "Daily Quiz", icon: "level" });
          }
          for (const reward of gemRewards.filter(e => !previous.rewards.includes(e.id))) {
            events.push({ id: "reward-" + reward.id, title: "Gems received",
              detail: "+" + reward.amount + " Gems added to your wallet.", page: "Wallet", icon: "gems" });
          }
        }
        next.push(...events.slice(-20));
        localStorage.setItem(snapshotKey, JSON.stringify({ badges: unlocked, level: levels.unlocked_level,
          rewards: gemRewards.map(e => e.id), events: events.slice(-20) }));
      } catch { /* Storage may be unavailable. */ }
      // Use existing fresh team-hub cache only; no extra football provider requests.
      const seen = new Set<string>();
      for (const team of [profile.primary_team, ...profile.favorites]) {
        if (!team) continue;
        try {
          const cached = JSON.parse(localStorage.getItem("fansphere-team-hub-v2:" + userId + ":" + team.provider_id) || "null");
          if (!cached || Date.now() - cached.savedAt > 30 * 60 * 1000) continue;
          for (const match of cached.data?.fixtures || []) {
            if (!match.utc_date || seen.has(String(match.id))) continue;
            const hours = (new Date(match.utc_date).getTime() - Date.now()) / 3600000;
            if (!(hours > 0 && hours <= 24)) continue;
            seen.add(String(match.id));
            const period = hours <= 2 ? "2h" : "24h";
            next.push({ id: "match-" + match.id + "-" + period,
              title: match.home_team.name + " vs " + match.away_team.name,
              detail: team.name + " plays " + (period === "2h" ? "within 2 hours" : "within 24 hours") + ". Kickoff " +
                new Date(match.utc_date).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }),
              page: "Matches", icon: "match" });
          }
        } catch { /* Ignore invalid cached fixtures. */ }
      }
      setItems(Array.from(new Map(next.map(n => [n.id, n])).values()));
    } catch (e) { setError(e instanceof Error ? e.message : "Notifications unavailable."); }
    finally { setLoading(false); }
  }

  useEffect(() => {
    if (!open) return;
    void refresh();
    const close = (event: MouseEvent) => { if (root.current && !root.current.contains(event.target as Node)) setOpen(false); };
    const escape = (event: KeyboardEvent) => { if (event.key === "Escape") setOpen(false); };
    document.addEventListener("mousedown", close);
    document.addEventListener("keydown", escape);
    return () => { document.removeEventListener("mousedown", close); document.removeEventListener("keydown", escape); };
  }, [open, userId]);

  function markRead(ids: string[]) {
    const updated = Array.from(new Set([...read, ...ids]));
    setRead(updated);
    try {
      localStorage.setItem(storageKey, JSON.stringify(updated));
      const snapshot = JSON.parse(localStorage.getItem(snapshotKey) || "null");
      if (snapshot) localStorage.setItem(snapshotKey, JSON.stringify({ ...snapshot,
        events: (snapshot.events || []).filter((n: Notice) => !updated.includes(n.id)) }));
    } catch {}
  }

  const unread = items.filter(item => !read.includes(item.id)).length;
  return <div ref={root} style={{ position: "relative", flexShrink: 0 }}>
    <button type="button" className="icon-button" aria-label={`Notifications${unread ? `, ${unread} unread` : ""}`}
      aria-expanded={open} aria-haspopup="dialog" onClick={() => setOpen(value => !value)}
      style={{ position: "relative" }}>
      <Bell size={19}/>
      {unread > 0 && <span style={{ position: "absolute", top: 2, right: 2, width: 7, height: 7, borderRadius: "50%", background: "#7cf3c7" }}/>}
    </button>
    {open && <section role="dialog" aria-label="Notifications" style={{
      position: "absolute", right: 0, top: "calc(100% + 12px)", zIndex: 100,
      width: "min(340px, 85vw)", maxHeight: "70vh", overflowY: "auto",
      padding: 14, background: "#0d2234", border: "1px solid #315269",
      borderRadius: 14, boxShadow: "0 16px 45px rgba(0,0,0,.4)", color: "#e2edf7",
    }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 10, marginBottom: 12 }}>
        <strong>Notifications</strong>
        {unread > 0 && <button type="button" onClick={() => markRead(items.map(item => item.id))}
          style={{ background: "none", border: 0, color: "#7cf3c7", cursor: "pointer", fontSize: 12 }}>Mark all read</button>}
      </div>
      {loading && <p style={{ fontSize: 12, color: "#9bb5c8" }}>Checking updates…</p>}
      {error && <p role="alert" style={{ fontSize: 12, color: "#ffb4b4" }}>{error}</p>}
      {!loading && !error && items.length === 0 && <p style={{ fontSize: 12, color: "#9bb5c8" }}>You're all caught up!</p>}
      {!loading && items.map(item => <button type="button" key={item.id} onClick={() => {
        markRead([item.id]); setOpen(false); onNavigate(item.page);
      }} style={{ display: "flex", gap: 10, width: "100%", textAlign: "left", padding: "12px 8px",
        background: read.includes(item.id) ? "transparent" : "#143449",
        border: 0, borderBottom: "1px solid #29445f", borderRadius: 7, cursor: "pointer", color: "#e2edf7" }}>
        <span style={{ color: "#7cf3c7", marginTop: 2 }}>{item.icon === "gems" ? <Gem size={17}/> : item.icon === "level" ? <Trophy size={17}/> : item.icon === "badge" ? <Award size={17}/> : item.icon === "match" ? <CalendarClock size={17}/> : <Sparkles size={17}/>}</span>
        <span style={{ flex: 1 }}><strong style={{ display: "block", fontSize: 12 }}>{item.title}</strong>
          <small style={{ display: "block", marginTop: 4, color: "#9bb5c8", lineHeight: 1.4 }}>{item.detail}</small></span>
        {read.includes(item.id) && <Check size={14} color="#7cf3c7"/>}
      </button>)}
    </section>}
  </div>;
}
