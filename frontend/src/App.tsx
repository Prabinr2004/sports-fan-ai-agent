import { FormEvent, useEffect, useState } from "react";
import { BarChart3, Bell, Check, Flame, Home, LoaderCircle, Search, Shield, Sparkles, Star, Trophy, Users, X } from "lucide-react";
import type { TeamHubData, TeamSummary } from "./types";

type SavedTeam = TeamSummary & { provider_id: string };
type Profile = { id: number; display_name: string; primary_team: SavedTeam | null; favorites: SavedTeam[]; mode: string };

const navItems = [
  { label: "Home", icon: Home }, { label: "My Team", icon: Shield }, { label: "Favorites", icon: Star },
  { label: "Matches", icon: Trophy }, { label: "Predictions", icon: BarChart3 }, { label: "Daily Quiz", icon: Sparkles }, { label: "Leaderboard", icon: Users },
];

function App() {
  const [apiStatus, setApiStatus] = useState<"checking" | "online" | "offline">("checking");
  const [query, setQuery] = useState(""); const [searching, setSearching] = useState(false);
  const [searchResults, setSearchResults] = useState<TeamSummary[]>([]); const [searchMessage, setSearchMessage] = useState("");
  const [selectedTeam, setSelectedTeam] = useState<TeamHubData | null>(null); const [loadingTeam, setLoadingTeam] = useState(false);
  const [profile, setProfile] = useState<Profile | null>(null); const [savingPreference, setSavingPreference] = useState(false);
  const [activePage, setActivePage] = useState("Home");

  async function loadProfile() {
    const response = await fetch("/api/v1/profile");
    if (response.ok) setProfile(await response.json());
  }

  useEffect(() => {
    fetch("/api/v1/health").then(r => { if (!r.ok) throw new Error(); return r.json(); }).then(() => setApiStatus("online")).catch(() => setApiStatus("offline"));
    loadProfile().catch(() => undefined);
  }, []);

  async function searchTeams(event: FormEvent) {
    event.preventDefault(); const trimmed = query.trim(); if (trimmed.length < 2) return;
    setSearching(true); setSearchMessage(""); setSearchResults([]);
    try { const response = await fetch(`/api/v1/teams/search?q=${encodeURIComponent(trimmed)}`); const payload = await response.json(); if (!response.ok) throw new Error(payload.detail || "Team search failed."); setSearchResults(payload.results || []); if (!payload.results?.length) setSearchMessage("No matching clubs found."); }
    catch (error) { setSearchMessage(error instanceof Error ? error.message : "Team search failed."); } finally { setSearching(false); }
  }

  async function openTeam(team: TeamSummary | SavedTeam) {
    const id = "provider_id" in team ? team.provider_id : team.id; setLoadingTeam(true); setSearchMessage("");
    try { const response = await fetch(`/api/v1/teams/${id}`); const payload = await response.json(); if (!response.ok) throw new Error(payload.detail || "Could not load the team hub."); setSelectedTeam(payload); setSearchResults([]); setQuery(""); }
    catch (error) { setSearchMessage(error instanceof Error ? error.message : "Could not load the team hub."); } finally { setLoadingTeam(false); }
  }

  async function savePreference(kind: "primary" | "favorite", providerId: string) {
    setSavingPreference(true);
    try {
      const response = await fetch(kind === "primary" ? "/api/v1/profile/primary-team" : "/api/v1/profile/favorites", { method: kind === "primary" ? "PUT" : "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ provider_team_id: providerId }) });
      if (!response.ok) throw new Error("Could not save team preference."); await loadProfile();
    } finally { setSavingPreference(false); }
  }

  async function removeFavorite(providerId: string) {
    setSavingPreference(true); try { await fetch(`/api/v1/profile/favorites/${providerId}`, { method: "DELETE" }); await loadProfile(); } finally { setSavingPreference(false); }
  }

  const primaryId = profile?.primary_team?.provider_id;
  const favoriteIds = new Set(profile?.favorites.map(team => team.provider_id) || []);

  return <div className="app-shell">
    <aside className="sidebar"><div className="brand"><div className="brand-mark">F</div><div><strong>FanSphere</strong><span>V2 Preview</span></div></div>
      <nav>{navItems.map(({label,icon:Icon}) => <button className={activePage===label?"nav-item active":"nav-item"} key={label} onClick={() => {setActivePage(label);setSelectedTeam(null)}}><Icon size={19}/><span>{label}</span></button>)}</nav>
      <div className="sidebar-card"><Flame size={21}/><div><span>Daily streak</span><strong>Coming next</strong></div></div>
    </aside>
    <main><header className="topbar"><form className="search search-form" onSubmit={searchTeams}>{searching?<LoaderCircle className="spin" size={18}/>:<Search size={18}/>}<input aria-label="Search teams" placeholder="Search any football club..." value={query} onChange={e=>setQuery(e.target.value)}/><button type="submit" className="search-submit" disabled={searching||query.trim().length<2}>Search</button>
      {(searchResults.length>0||searchMessage)&&<div className="search-popover">{searchMessage&&<p className="search-message">{searchMessage}</p>}{searchResults.map(team=><button type="button" className="search-result" key={team.id} onClick={()=>openTeam(team)}><span className="search-crest">{team.crest_url?<img src={team.crest_url} alt=""/>:(team.tla||team.name.slice(0,2))}</span><span><strong>{team.name}</strong><small>{[team.league_name,team.country].filter(Boolean).join(" · ")||"Football club"}</small></span><span className="result-arrow">→</span></button>)}</div>}</form>
      <div className={`api-status ${apiStatus}`}><span/>{apiStatus==="checking"?"Connecting":apiStatus==="online"?"API online":"API offline"}</div><button className="icon-button" aria-label="Notifications"><Bell size={19}/></button><div className="avatar">PR</div></header>
      <section className="content">{selectedTeam?<TeamHub data={selectedTeam} onClose={()=>setSelectedTeam(null)} primaryId={primaryId} favoriteIds={favoriteIds} saving={savingPreference} onPrimary={id=>savePreference("primary",id)} onFavorite={id=>savePreference("favorite",id)} onUnfavorite={removeFavorite}/>:activePage==="Favorites"?<FavoritesPage profile={profile} onOpen={openTeam}/>:activePage==="My Team"?<MyTeamPage profile={profile} onOpen={openTeam}/>:<HomeDashboard profile={profile} onOpen={openTeam}/>} {loadingTeam&&<div className="loading-overlay"><LoaderCircle className="spin" size={28}/><span>Loading club...</span></div>}</section>
    </main></div>;
}

function HomeDashboard({profile,onOpen}:{profile:Profile|null;onOpen:(team:SavedTeam)=>void}) {
  const team=profile?.primary_team;
  return <><div className="welcome-row"><div><span className="eyebrow">YOUR FOOTBALL WORLD</span><h1>Good afternoon, {profile?.display_name||"fan"}.</h1><p>{team?`Your home feed now starts with ${team.name}.`:"Search for your club and make it your primary team."}</p></div><div className="xp-pill"><span>V2</span><strong>PROFILE LIVE</strong></div></div>
    {team?<section className="hero-card"><div className="team-identity"><div className="crest-placeholder">{team.crest_url?<img className="saved-crest" src={team.crest_url} alt=""/>:team.name.slice(0,2)}</div><div><span className="eyebrow">PRIMARY TEAM</span><h2>{team.name}</h2><p>{[team.league_name,team.country].filter(Boolean).join(" · ")}</p></div></div><button className="primary-button" onClick={()=>onOpen(team)}>Open Team Hub</button></section>:<section className="empty-state"><Shield size={34}/><h2>Choose your club</h2><p>Use search above, open a team, then select “Make My Team.”</p></section>}
    <div className="dashboard-grid"><section className="panel"><span className="eyebrow">FOLLOWING</span><h3>{profile?.favorites.length||0} favorite clubs</h3><p>Your followed teams are stored locally and survive page refreshes.</p></section><section className="panel"><span className="eyebrow">NEXT MILESTONE</span><h3>XP + daily quiz</h3><p>Preferences are now the base for personalized quizzes and rewards.</p></section></div></>;
}

function MyTeamPage({profile,onOpen}:{profile:Profile|null;onOpen:(team:SavedTeam)=>void}) { const team=profile?.primary_team; return <><span className="eyebrow">MY TEAM</span><h1>{team?team.name:"No primary team yet"}</h1>{team?<button className="primary-button" onClick={()=>onOpen(team)}>Open {team.name} hub</button>:<p>Search for a club and choose Make My Team.</p>}</>; }
function FavoritesPage({profile,onOpen}:{profile:Profile|null;onOpen:(team:SavedTeam)=>void}) { return <><span className="eyebrow">FAVORITES</span><h1>Following</h1><div className="favorites-grid">{profile?.favorites.length?profile.favorites.map(team=><button key={team.provider_id} className="favorite-card" onClick={()=>onOpen(team)}>{team.crest_url&&<img src={team.crest_url} alt=""/>}<span><strong>{team.name}</strong><small>{team.league_name||team.country}</small></span><span>→</span></button>):<p>You are not following any extra clubs yet.</p>}</div></>; }

function TeamHub({data,onClose,primaryId,favoriteIds,saving,onPrimary,onFavorite,onUnfavorite}:{data:TeamHubData;onClose:()=>void;primaryId?:string;favoriteIds:Set<string>;saving:boolean;onPrimary:(id:string)=>void;onFavorite:(id:string)=>void;onUnfavorite:(id:string)=>void}) {
  const {team,squad,fixtures}=data; const isPrimary=primaryId===team.id; const isFavorite=favoriteIds.has(team.id);
  return <div className="team-hub"><button className="back-button" onClick={onClose}><X size={16}/> Close team hub</button><section className="team-hub-hero"><div className="hub-crest">{team.crest_url?<img src={team.crest_url} alt={`${team.name} crest`}/>:team.tla||team.name.slice(0,2)}</div><div className="hub-title"><span className="eyebrow">TEAM HUB</span><h1>{team.name}</h1><p>{[team.league_name,team.country].filter(Boolean).join(" · ")}</p><div className="team-meta">{team.founded&&<span>Founded {team.founded}</span>}{team.venue&&<span>{team.venue}</span>}{team.club_colors&&<span>{team.club_colors}</span>}</div></div><div className="team-actions"><button disabled={saving||isPrimary} className="primary-button" onClick={()=>onPrimary(team.id)}>{isPrimary?<><Check size={16}/> My Team</>:"Make My Team"}</button><button disabled={saving} className={isFavorite?"secondary-button followed":"secondary-button"} onClick={()=>isFavorite?onUnfavorite(team.id):onFavorite(team.id)}><Star size={16}/>{isFavorite?" Following":" Follow"}</button></div></section>
    <div className="hub-grid"><section className="panel"><div className="panel-heading"><div><span className="eyebrow">SQUAD</span><h3>Current players</h3></div><span className="count-chip">{squad.length}</span></div><div className="player-list">{squad.map(player=><article key={player.id}><div className="player-avatar">{player.name.split(" ").map(p=>p[0]).slice(0,2).join("")}</div><div><strong>{player.name}</strong><span>{[player.position,player.nationality].filter(Boolean).join(" · ")||"Player"}</span></div></article>)}</div></section><section className="panel"><div className="panel-heading"><div><span className="eyebrow">UPCOMING</span><h3>Fixtures</h3></div><span className="count-chip">{fixtures.length}</span></div><div className="hub-fixtures">{fixtures.map(f=><article key={f.id}><small>{f.competition||"Match"}</small><strong>{f.home_team.name} <span>vs</span> {f.away_team.name}</strong><p>{f.utc_date?new Date(f.utc_date).toLocaleString([], {dateStyle:"medium",timeStyle:"short"}):"Date TBA"}</p></article>)}</div></section></div></div>;
}
export default App;
