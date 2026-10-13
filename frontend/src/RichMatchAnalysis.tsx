import { useEffect, useState } from "react";
import { Gem, Sparkles } from "lucide-react";

type Access = {
  free_remaining: number;
  extra_remaining: number;
  gems: number;
  gems_per_analysis: number;
  match_unlocked: boolean;
  rich_analysis_available: boolean;
};

export default function RichMatchAnalysis({ matchId }: { matchId: string }) {
  const [access, setAccess] = useState<Access | null>(null);
  const [analysis, setAnalysis] = useState("");
  const [loadingAccess, setLoadingAccess] = useState(true);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState("");
  const [cached, setCached] = useState(false);

  useEffect(() => {
    let active = true;
    setAccess(null);
    setAnalysis("");
    setError("");
    setCached(false);
    setLoadingAccess(true);
    fetch("/api/v1/analysis/access?match_id=" + encodeURIComponent(matchId))
      .then(async response => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Analysis availability could not be loaded.");
        return payload as Access;
      })
      .then(payload => { if (active) setAccess(payload); })
      .catch(err => { if (active) setError(err instanceof Error ? err.message : "Analysis unavailable."); })
      .finally(() => { if (active) setLoadingAccess(false); });
    return () => { active = false; };
  }, [matchId]);

  const free = Boolean(access && access.free_remaining > 0 && !access.match_unlocked);
  const paid = Boolean(access && !access.match_unlocked && !free);
  const canAfford = Boolean(access && access.gems >= access.gems_per_analysis && access.extra_remaining > 0);
  const disabled = running || loadingAccess || !access?.rich_analysis_available || (paid && !canAfford);
  const label = running ? "Analyzing…" : access?.match_unlocked
    ? "View saved analysis" : free ? "Analyze Match · Free today"
    : "Analyze Match · " + (access?.gems_per_analysis ?? 2) + " Gems";

  async function analyze() {
    if (disabled) return;
    setRunning(true);
    setError("");
    try {
      const response = await fetch("/api/v1/analysis/" + encodeURIComponent(matchId) + "/rich", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Could not analyze this match.");
      setAnalysis(payload.analysis || "");
      setCached(Boolean(payload.cached));
      const latest = await fetch("/api/v1/analysis/access?match_id=" + encodeURIComponent(matchId));
      if (latest.ok) setAccess(await latest.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis temporarily unavailable.");
    } finally {
      setRunning(false);
    }
  }

  return <section className="match-center-panel" aria-label="AI match analysis">
    <span className="eyebrow">FANSPHERE AI</span>
    <h2>Match analysis</h2>
    <p>Explore this matchup with an AI explanation based on available team form and model data.</p>
    {loadingAccess ? <p role="status">Checking analysis access…</p> : access && <>
      <p style={{ fontSize: 13, opacity: .85 }}>
        {access.match_unlocked ? "Previously unlocked · no additional charge" :
          free ? "Your first match analysis today is free." :
          access.extra_remaining <= 0 ? "Today's additional analysis limit has been reached." :
          "Additional analysis costs " + access.gems_per_analysis + " Gems."}
        {" "}Gem balance: {access.gems}.
      </p>
      {!access.rich_analysis_available && <p role="status">AI analysis is not configured on this server.</p>}
      <button type="button" className="secondary-button" disabled={disabled} onClick={() => void analyze()}
        style={{ display: "inline-flex", alignItems: "center", gap: 8 }}>
        {paid ? <Gem size={15} /> : <Sparkles size={15} />}{label}
      </button>
      {paid && !canAfford && <p role="status">Not enough Gems or no additional analyses remaining. Check Wallet.</p>}
    </>}
    {error && <p role="alert">{error}</p>}
    {analysis && <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.65, marginTop: 16 }}>
      <strong>{cached ? "Saved analysis" : "Match insight"}</strong>
      <p>{analysis}</p>
    </div>}
  </section>;
}
