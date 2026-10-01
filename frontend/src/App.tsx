import { FormEvent, useEffect, useState } from "react";
import {
  BarChart3,
  Bell,
  Flame,
  Home,
  LoaderCircle,
  Search,
  Shield,
  Sparkles,
  Star,
  Trophy,
  Users,
  X,
} from "lucide-react";
import type { TeamHubData, TeamSummary } from "./types";

const navItems = [
  { label: "Home", icon: Home, active: true },
  { label: "My Team", icon: Shield },
  { label: "Favorites", icon: Star },
  { label: "Matches", icon: Trophy },
  { label: "Predictions", icon: BarChart3 },
  { label: "Daily Quiz", icon: Sparkles },
  { label: "Leaderboard", icon: Users },
];

const previewFixtures = [
  { opponent: "Atlético Madrid", date: "Sun · 1:00 PM", location: "Home" },
  { opponent: "Villarreal", date: "Wed · 2:00 PM", location: "Away" },
];

function App() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [query, setQuery] = useState("");
  const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<TeamSummary[]>([]);
  const [searchMessage, setSearchMessage] = useState("");
  const [selectedTeam, setSelectedTeam] = useState<TeamHubData | null>(null);
  const [loadingTeam, setLoadingTeam] = useState(false);

  useEffect(() => {
    fetch("/api/v1/health")
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json();
      })
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  async function searchTeams(event: FormEvent) {
    event.preventDefault();
    const trimmed = query.trim();
    if (trimmed.length < 2) return;

    setSearching(true);
    setSearchMessage("");
    setSearchResults([]);
    try {
      const response = await fetch(`/api/v1/teams/search?q=${encodeURIComponent(trimmed)}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Team search failed.");
      setSearchResults(payload.results || []);
      if (!payload.results?.length) setSearchMessage("No matching clubs found.");
    } catch (error) {
      setSearchMessage(error instanceof Error ? error.message : "Team search failed.");
    } finally {
      setSearching(false);
    }
  }

  async function openTeam(team: TeamSummary) {
    setLoadingTeam(true);
    setSearchMessage("");
    try {
      const response = await fetch(`/api/v1/teams/${team.id}`);
      const payload = await response.json();
      if (!response.ok) throw new Error(payload.detail || "Could not load the team hub.");
      setSelectedTeam(payload);
      setSearchResults([]);
      setQuery("");
    } catch (error) {
      setSearchMessage(error instanceof Error ? error.message : "Could not load the team hub.");
    } finally {
      setLoadingTeam(false);
    }
  }

  function closeTeamHub() {
    setSelectedTeam(null);
  }

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div><strong>FanSphere</strong><span>V2 Preview</span></div>
        </div>
        <nav>
          {navItems.map(({ label, icon: Icon, active }) => (
            <button className={active ? "nav-item active" : "nav-item"} key={label}>
              <Icon size={19} /><span>{label}</span>
            </button>
          ))}
        </nav>
        <div className="sidebar-card"><Flame size={21} /><div><span>Daily streak</span><strong>4 days</strong></div></div>
      </aside>

      <main>
        <header className="topbar">
          <form className="search search-form" onSubmit={searchTeams}>
            {searching ? <LoaderCircle className="spin" size={18} /> : <Search size={18} />}
            <input
              aria-label="Search teams"
              placeholder="Search any football club..."
              value={query}
              onChange={(event) => setQuery(event.target.value)}
            />
            <button type="submit" className="search-submit" disabled={searching || query.trim().length < 2}>Search</button>
            {(searchResults.length > 0 || searchMessage) && (
              <div className="search-popover">
                {searchMessage && <p className="search-message">{searchMessage}</p>}
                {searchResults.map((team) => (
                  <button type="button" className="search-result" key={team.id} onClick={() => openTeam(team)}>
                    <span className="search-crest">
                      {team.crest_url ? <img src={team.crest_url} alt="" /> : (team.tla || team.name.slice(0, 2))}
                    </span>
                    <span><strong>{team.name}</strong><small>{[team.league_name, team.country].filter(Boolean).join(" · ") || "Football club"}</small></span>
                    <span className="result-arrow">→</span>
                  </button>
                ))}
              </div>
            )}
          </form>
          <div className={`api-status ${apiStatus}`}><span />{apiStatus === "checking" ? "Connecting" : apiStatus === "online" ? "API online" : "API offline"}</div>
          <button className="icon-button" aria-label="Notifications"><Bell size={19} /></button>
          <div className="avatar">PR</div>
        </header>

        <section className="content">
          {selectedTeam ? (
            <TeamHub data={selectedTeam} onClose={closeTeamHub} />
          ) : (
            <HomeDashboard />
          )}
          {loadingTeam && <div className="loading-overlay"><LoaderCircle className="spin" size={28} /><span>Loading club...</span></div>}
        </section>
      </main>
    </div>
  );
}

function HomeDashboard() {
  return (
    <>
      <div className="welcome-row">
        <div><span className="eyebrow">YOUR FOOTBALL WORLD</span><h1>Good afternoon, Prabin.</h1><p>Everything that matters to you, starting with your club.</p></div>
        <div className="xp-pill"><span>LEVEL 4</span><strong>720 XP</strong></div>
      </div>
      <section className="hero-card">
        <div className="team-identity"><div className="crest-placeholder">RM</div><div><span className="eyebrow">PRIMARY TEAM · PREVIEW</span><h2>Real Madrid</h2><p>LaLiga · Spain</p></div></div>
        <div className="form-block"><span>RECENT FORM</span><div className="form-dots"><b>W</b><b>W</b><b className="draw">D</b><b>W</b><b className="loss">L</b></div></div>
        <button className="primary-button">Open Team Hub</button>
      </section>
      <div className="dashboard-grid">
        <section className="panel next-match">
          <div className="panel-heading"><div><span className="eyebrow">NEXT MATCH · PREVIEW</span><h3>Madrid Derby</h3></div><span className="live-chip">Demo</span></div>
          <div className="matchup"><div><div className="mini-crest">RM</div><strong>Real Madrid</strong></div><div className="versus"><strong>VS</strong><span>Preview</span></div><div><div className="mini-crest alt">ATM</div><strong>Atlético</strong></div></div>
          <button className="secondary-button">Prediction feature coming next</button>
        </section>
        <section className="panel challenge">
          <div className="panel-heading"><div><span className="eyebrow">DAILY CHALLENGE · PREVIEW</span><h3>Keep your streak alive</h3></div><Flame size={25} /></div>
          <div className="streak-number">4</div><p>days in a row</p><div className="progress-track"><span /></div><small>Quiz and persistent XP arrive after accounts.</small><button className="primary-button">Daily quiz coming soon</button>
        </section>
        <section className="panel full">
          <div className="panel-heading"><div><span className="eyebrow">UPCOMING · PREVIEW</span><h3>Your club's next fixtures</h3></div></div>
          <div className="fixture-list">{previewFixtures.map((fixture) => <article key={fixture.opponent}><div className="mini-crest">RM</div><div className="fixture-copy"><strong>Real Madrid vs {fixture.opponent}</strong><span>{fixture.date} · {fixture.location}</span></div><span className="fixture-arrow">→</span></article>)}</div>
        </section>
      </div>
      <p className="preview-note">Search becomes live as soon as the football provider key is configured. The home cards remain clearly marked preview until accounts and preferences are connected.</p>
    </>
  );
}

function TeamHub({ data, onClose }: { data: TeamHubData; onClose: () => void }) {
  const { team, squad, fixtures } = data;
  return (
    <div className="team-hub">
      <button className="back-button" onClick={onClose}><X size={16} /> Close team hub</button>
      <section className="team-hub-hero">
        <div className="hub-crest">{team.crest_url ? <img src={team.crest_url} alt={`${team.name} crest`} /> : team.tla || team.name.slice(0, 2)}</div>
        <div className="hub-title"><span className="eyebrow">TEAM HUB</span><h1>{team.name}</h1><p>{[team.league_name, team.country].filter(Boolean).join(" · ")}</p><div className="team-meta">{team.founded && <span>Founded {team.founded}</span>}{team.venue && <span>{team.venue}</span>}{team.club_colors && <span>{team.club_colors}</span>}</div></div>
      </section>
      <div className="hub-grid">
        <section className="panel"><div className="panel-heading"><div><span className="eyebrow">SQUAD</span><h3>Current players</h3></div><span className="count-chip">{squad.length}</span></div><div className="player-list">{squad.length ? squad.map((player) => <article key={player.id}><div className="player-avatar">{player.name.split(" ").map((part) => part[0]).slice(0, 2).join("")}</div><div><strong>{player.name}</strong><span>{[player.position, player.nationality].filter(Boolean).join(" · ") || "Player"}</span></div></article>) : <p>No squad data is available on the current provider plan.</p>}</div></section>
        <section className="panel"><div className="panel-heading"><div><span className="eyebrow">UPCOMING</span><h3>Fixtures</h3></div><span className="count-chip">{fixtures.length}</span></div><div className="hub-fixtures">{fixtures.length ? fixtures.map((fixture) => <article key={fixture.id}><small>{fixture.competition || "Match"}</small><strong>{fixture.home_team.name} <span>vs</span> {fixture.away_team.name}</strong><p>{fixture.utc_date ? new Date(fixture.utc_date).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "Date TBA"}</p></article>) : <p>No scheduled fixtures returned.</p>}</div></section>
      </div>
    </div>
  );
}

export default App;
