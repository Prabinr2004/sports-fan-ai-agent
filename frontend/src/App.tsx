import { useEffect, useState } from "react";
import {
  BarChart3,
  Bell,
  Flame,
  Home,
  Search,
  Shield,
  Sparkles,
  Star,
  Trophy,
  Users,
} from "lucide-react";

const navItems = [
  { label: "Home", icon: Home, active: true },
  { label: "My Team", icon: Shield },
  { label: "Favorites", icon: Star },
  { label: "Matches", icon: Trophy },
  { label: "Predictions", icon: BarChart3 },
  { label: "Daily Quiz", icon: Sparkles },
  { label: "Leaderboard", icon: Users },
];

const fixtures = [
  { opponent: "Atlético Madrid", date: "Sun · 1:00 PM", location: "Home" },
  { opponent: "Villarreal", date: "Wed · 2:00 PM", location: "Away" },
];

function App() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");

  useEffect(() => {
    fetch("/api/v1/health")
      .then((response) => {
        if (!response.ok) throw new Error("API unavailable");
        return response.json();
      })
      .then(() => setApiStatus("online"))
      .catch(() => setApiStatus("offline"));
  }, []);

  return (
    <div className="app-shell">
      <aside className="sidebar">
        <div className="brand">
          <div className="brand-mark">F</div>
          <div>
            <strong>FanSphere</strong>
            <span>V2 Preview</span>
          </div>
        </div>

        <nav>
          {navItems.map(({ label, icon: Icon, active }) => (
            <button className={active ? "nav-item active" : "nav-item"} key={label}>
              <Icon size={19} />
              <span>{label}</span>
            </button>
          ))}
        </nav>

        <div className="sidebar-card">
          <Flame size={21} />
          <div>
            <span>Daily streak</span>
            <strong>4 days</strong>
          </div>
        </div>
      </aside>

      <main>
        <header className="topbar">
          <div className="search">
            <Search size={18} />
            <input aria-label="Search teams" placeholder="Search any football club..." />
            <kbd>⌘ K</kbd>
          </div>
          <div className={`api-status ${apiStatus}`}>
            <span />
            {apiStatus === "checking" ? "Connecting" : apiStatus === "online" ? "API online" : "API offline"}
          </div>
          <button className="icon-button" aria-label="Notifications">
            <Bell size={19} />
          </button>
          <div className="avatar">PR</div>
        </header>

        <section className="content">
          <div className="welcome-row">
            <div>
              <span className="eyebrow">YOUR FOOTBALL WORLD</span>
              <h1>Good afternoon, Prabin.</h1>
              <p>Everything that matters to you, starting with your club.</p>
            </div>
            <div className="xp-pill">
              <span>LEVEL 4</span>
              <strong>720 XP</strong>
            </div>
          </div>

          <section className="hero-card">
            <div className="team-identity">
              <div className="crest-placeholder">RM</div>
              <div>
                <span className="eyebrow">PRIMARY TEAM</span>
                <h2>Real Madrid</h2>
                <p>LaLiga · Spain</p>
              </div>
            </div>
            <div className="form-block">
              <span>RECENT FORM</span>
              <div className="form-dots">
                <b>W</b><b>W</b><b className="draw">D</b><b>W</b><b className="loss">L</b>
              </div>
            </div>
            <button className="primary-button">Open Team Hub</button>
          </section>

          <div className="dashboard-grid">
            <section className="panel next-match">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">NEXT MATCH</span>
                  <h3>Madrid Derby</h3>
                </div>
                <span className="live-chip">In 3 days</span>
              </div>
              <div className="matchup">
                <div>
                  <div className="mini-crest">RM</div>
                  <strong>Real Madrid</strong>
                </div>
                <div className="versus">
                  <strong>VS</strong>
                  <span>Sun · 1:00 PM</span>
                </div>
                <div>
                  <div className="mini-crest alt">ATM</div>
                  <strong>Atlético</strong>
                </div>
              </div>
              <button className="secondary-button">Make your prediction</button>
            </section>

            <section className="panel challenge">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">DAILY CHALLENGE</span>
                  <h3>Keep your streak alive</h3>
                </div>
                <Flame size={25} />
              </div>
              <div className="streak-number">4</div>
              <p>days in a row</p>
              <div className="progress-track"><span /></div>
              <small>One more day toward your next streak reward.</small>
              <button className="primary-button">Play today's quiz</button>
            </section>

            <section className="panel full">
              <div className="panel-heading">
                <div>
                  <span className="eyebrow">UPCOMING</span>
                  <h3>Your club's next fixtures</h3>
                </div>
                <button className="text-button">View all matches</button>
              </div>
              <div className="fixture-list">
                {fixtures.map((fixture) => (
                  <article key={fixture.opponent}>
                    <div className="mini-crest">RM</div>
                    <div className="fixture-copy">
                      <strong>Real Madrid vs {fixture.opponent}</strong>
                      <span>{fixture.date} · {fixture.location}</span>
                    </div>
                    <span className="fixture-arrow">→</span>
                  </article>
                ))}
              </div>
            </section>
          </div>

          <p className="preview-note">
            Preview data is intentionally static. Live teams, squads, fixtures and model probabilities will come from the provider/API and ML layers.
          </p>
        </section>
      </main>
    </div>
  );
}

export default App;
