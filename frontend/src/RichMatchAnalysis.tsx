import { useEffect, useState } from "react";
import { Sparkles } from "lucide-react";

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

  useEffect(() => {
    let active = true;
    setAccess(null);
    setAnalysis("");
    setError("");
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
    ? "Show analysis" : free ? "Analyze match · Free"
    : "Analyze match · " + (access?.gems_per_analysis ?? 2) + " Gems";

  async function analyze() {
    if (disabled) return;
    setRunning(true);
    setError("");
    try {
      const response = await fetch("/api/v1/analysis/" + encodeURIComponent(matchId) + "/rich", { method: "POST" });
      const payload = await response.json();
      if (!response.ok) throw new Error(typeof payload.detail === "string" ? payload.detail : "Could not analyze this match.");
      setAnalysis(payload.analysis || "");
      const latest = await fetch("/api/v1/analysis/access?match_id=" + encodeURIComponent(matchId));
      if (latest.ok) setAccess(await latest.json());
    } catch (err) {
      setError(err instanceof Error ? err.message : "Analysis temporarily unavailable.");
    } finally {
      setRunning(false);
    }
  }

  const available = Boolean(access?.rich_analysis_available);
  const note = loadingAccess ? "Checking availability…" :
    !access ? "" : !available ? "AI insights are temporarily unavailable." :
    analysis ? "" : access.match_unlocked ? "Your analysis is ready to view." :
    free ? "One free analysis available today." :
    access.extra_remaining <= 0 ? "Daily analysis limit reached." :
    !canAfford ? "Not enough Gems. Visit Wallet." : "Unlock for " + access.gems_per_analysis + " Gems.";

  return <section className="match-center-panel" aria-label="AI match analysis"
    style={{ padding: "16px 20px", display: "flex", flexDirection: "column", gap: 10 }}>
    <div style={{ display: "flex", alignItems: "center", justifyContent: "space-between", gap: 12, flexWrap: "wrap" }}>
      <h2 style={{ margin: 0, display: "flex", alignItems: "center", gap: 8, fontSize: 17 }}>
        <Sparkles size={17} /> AI Match Analysis
      </h2>
      {available && !analysis && <button type="button" className="secondary-button"
        disabled={disabled} onClick={() => void analyze()}
        style={{ display: "inline-flex", alignItems: "center", gap: 7, padding: "8px 12px" }}>
        <Sparkles size={14} />{label}
      </button>}
    </div>
    {note && <small role="status" style={{ color: "#9bb5c8" }}>{note}</small>}
    {error && <small role="alert" style={{ color: "#ffb4b4" }}>{error}</small>}
    {analysis && <div style={{ whiteSpace: "pre-wrap", lineHeight: 1.65, fontSize: 14 }}>
      {analysis}
    </div>}
  </section>;
}
