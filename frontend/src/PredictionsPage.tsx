import { BarChart3, CheckCircle2, Clock3, LoaderCircle, Target } from "lucide-react";
import { useEffect, useState } from "react";

type Prediction = {
  id: number;
  match_id: string;
  home_team_name: string;
  away_team_name: string;
  predicted_outcome: "HOME" | "DRAW" | "AWAY";
  kickoff_utc?: string | null;
  created_at?: string | null;
};

type PredictionResponse = { predictions: Prediction[]; total: number; notice?: string | null };

function pickLabel(item: Prediction) {
  if (item.predicted_outcome === "HOME") return item.home_team_name;
  if (item.predicted_outcome === "AWAY") return item.away_team_name;
  return "Draw";
}

export default function PredictionsPage() {
  const [data, setData] = useState<PredictionResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetch("/api/v1/matches/predictions")
      .then(async (response) => {
        const payload = await response.json();
        if (!response.ok) throw new Error(payload.detail || "Could not load predictions.");
        return payload;
      })
      .then(setData)
      .catch((err) => setError(err instanceof Error ? err.message : "Could not load predictions."));
  }, []);

  if (!data && !error) return <div className="matches-loading"><LoaderCircle className="spin" /> Loading prediction dashboard...</div>;
  if (error) return <section className="empty-state"><BarChart3 size={34}/><h2>Prediction dashboard unavailable</h2><p>{error}</p></section>;

  const predictions = data?.predictions || [];
  return <div className="predictions-dashboard">
    <span className="eyebrow">PREDICTION CENTER</span>
    <h1>Your predictions</h1>
    <p>A separate history of your fan picks. Match results, accuracy, and ML comparison will appear here as those systems come online.</p>

    <div className="prediction-stats">
      <section><Target size={19}/><div><span>TOTAL PICKS</span><strong>{predictions.length}</strong></div></section>
      <section><Clock3 size={19}/><div><span>AWAITING RESULTS</span><strong>{predictions.length}</strong></div></section>
      <section><CheckCircle2 size={19}/><div><span>ACCURACY</span><strong>—</strong></div></section>
    </div>

    {data?.notice && <div className="quiz-complete-note">{data.notice}</div>}

    {!predictions.length ? <section className="empty-state"><Target size={34}/><h2>No predictions yet</h2><p>Go to Matches and make your first fan prediction.</p></section> :
      <div className="prediction-history">
        {predictions.map((item) => <article className="prediction-history-row" key={item.id}>
          <div className="prediction-match-name">
            <span className="prediction-match-icon"><BarChart3 size={17}/></span>
            <div><strong>{item.home_team_name} <span>vs</span> {item.away_team_name}</strong><small>{item.kickoff_utc ? new Date(item.kickoff_utc).toLocaleString([], {dateStyle:"medium",timeStyle:"short"}) : "Upcoming match"}</small></div>
          </div>
          <div className="prediction-pick"><span>YOUR PICK</span><strong>{pickLabel(item)}</strong></div>
          <div className="prediction-result pending"><span>STATUS</span><strong>Pending</strong></div>
        </article>)}
      </div>}
  </div>;
}
