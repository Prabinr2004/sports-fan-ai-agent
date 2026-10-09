import { ArrowLeft, CalendarDays, LockKeyhole, RefreshCw } from "lucide-react";
import { useEffect, useState } from "react";
import ModelOutlook from "./ModelOutlook";

export type MatchCenterTeam={id:string;name:string;short_name?:string|null;tla?:string|null;crest_url?:string|null};
export type MatchCenterMatch={id:string;source_team_id:string;utc_date?:string|null;status?:string|null;competition?:string|null;home_team:MatchCenterTeam;away_team:MatchCenterTeam;user_prediction?:"HOME"|"DRAW"|"AWAY"|null;prediction_locked?:boolean};
type Props={match:MatchCenterMatch;onBack:()=>void;onPick:(match:MatchCenterMatch,outcome:"HOME"|"DRAW"|"AWAY")=>Promise<void>;saving:boolean;message?:string;userId?:number};
function Team({team}:{team:MatchCenterTeam}){return <div className="match-center-team">{team.crest_url?<img src={team.crest_url} alt=""/>:<div className="match-center-fallback">{team.tla||team.name.slice(0,2)}</div>}<strong>{team.name}</strong></div>}
type FormStats={form:string[];goals_for:number|null;goals_against:number|null;matches:number};
type Standing={competition?:string|null;position:number};
const HUB_TTL=30*60*1000;
function cachedHub(userId:number|undefined,teamId:string){
 if(!userId)return null;
 try{
  const entry=JSON.parse(window.localStorage.getItem(`fansphere-team-hub-v2:${userId}:${teamId}`)||"null");
  return entry&&Date.now()-entry.savedAt<HUB_TTL&&String(entry.data?.team?.id)===teamId?entry.data:null;
 }catch{return null}
}
function comparisonFromCache(userId:number|undefined,match:MatchCenterMatch){
 const sides=[match.home_team,match.away_team].map(team=>{
  const hub=cachedHub(userId,String(team.id));
  if(!hub)return null;
  const recent=(hub.recent_results||[]).filter((m:any)=>m.score?.home!=null&&m.score?.away!=null).sort((a:any,b:any)=>(a.utc_date||"").localeCompare(b.utc_date||"")).slice(-5);
  let goalsFor=0,goalsAgainst=0;
  const form=recent.map((m:any)=>{
   const home=String(m.home_team?.id)===String(team.id);
   const gf=home?m.score.home:m.score.away,ga=home?m.score.away:m.score.home;
   goalsFor+=gf;goalsAgainst+=ga;
   return gf>ga?"W":gf===ga?"D":"L";
  });
  return {stats:{form,goals_for:form.length?goalsFor:null,goals_against:form.length?goalsAgainst:null,matches:form.length} as FormStats,standings:(hub.standings||[]).filter((s:any)=>s.position!=null).map((s:any)=>({competition:s.competition,position:s.position})) as Standing[]};
 });
 if(!sides.some(Boolean))return null;
 return {home:sides[0]?.stats||{form:[],goals_for:null,goals_against:null,matches:0},away:sides[1]?.stats||{form:[],goals_for:null,goals_against:null,matches:0},standings:{home:sides[0]?.standings||[],away:sides[1]?.standings||[]}};
}
function mergeComparison(incoming:Comparison|null,cached:Comparison|null):Comparison|null{
 if(!cached)return incoming;
 if(!incoming)return cached;
 const stats=(a:FormStats,b:FormStats):FormStats=>a?.form?.length?a:b;
 return {home:stats(incoming.home,cached.home),away:stats(incoming.away,cached.away),standings:{home:incoming.standings?.home?.length?incoming.standings.home:cached.standings?.home||[],away:incoming.standings?.away?.length?incoming.standings.away:cached.standings?.away||[]}};
}
type Comparison={home:FormStats;away:FormStats;standings?:{home:Standing[];away:Standing[]}};
function readComparisonCache(userId:number|undefined,matchId:string):Comparison|null{
 if(!userId)return null;
 try{const raw=window.localStorage.getItem(`fansphere-match-comparison-v1:${userId}:${matchId}`);if(!raw)return null;const entry=JSON.parse(raw);return Date.now()-entry.savedAt<6*60*60*1000?entry.data:null}catch{return null}
}
function saveComparisonCache(userId:number|undefined,matchId:string,data:Comparison){
 if(!userId)return;
 try{window.localStorage.setItem(`fansphere-match-comparison-v1:${userId}:${matchId}`,JSON.stringify({savedAt:Date.now(),data}))}catch{}
}
function FormRow({stats}:{stats?:FormStats}){return <div className="form-row">{stats?.form?.length?stats.form.map((r,i)=><span key={i} className={"form-dot "+r.toLowerCase()}>{r}</span>):<small>Form unavailable</small>}</div>}
export default function MatchCenter({match,onBack,onPick,saving,message,userId}:Props){const kickoffDate=match.utc_date?new Date(match.utc_date):null;const kickoff=kickoffDate&&Number.isFinite(kickoffDate.getTime())?kickoffDate:null;const [now,setNow]=useState(Date.now());const [lastChecked,setLastChecked]=useState<number|null>(null);const [refreshing,setRefreshing]=useState(false);const [liveStatus,setLiveStatus]=useState(match.status||"SCHEDULED");const [liveScore,setLiveScore]=useState<{home:number|null;away:number|null}|null>(null);const [comparison,setComparison]=useState<Comparison|null>(null);const [result,setResult]=useState<{status:"CORRECT"|"INCORRECT";actual_outcome:"HOME"|"DRAW"|"AWAY";score:{home:number|null;away:number|null}}|null>(null);useEffect(()=>{let active=true;const cached=mergeComparison(comparisonFromCache(userId,match),readComparisonCache(userId,match.id));setComparison(cached);setResult(null);fetch("/api/v1/matches/"+encodeURIComponent(match.id)+"/center").then(r=>r.ok?r.json():null).then(p=>{if(!active)return;const merged=mergeComparison(p?.comparison||null,cached);setComparison(merged);if(merged)saveComparisonCache(userId,match.id,merged);setResult(p?.result||null)}).catch(()=>undefined);return()=>{active=false}},[match.id,userId]);useEffect(()=>{setLiveStatus(match.status||"SCHEDULED");setLiveScore(null)},[match.id,match.status]);
useEffect(()=>{const timer=window.setInterval(()=>setNow(Date.now()),30000);return()=>window.clearInterval(timer)},[]);
const statusUpper=liveStatus.toUpperCase();
const isLive=["IN_PLAY","PAUSED","LIVE","HALFTIME","HALF_TIME"].includes(statusUpper);
const isFinal=["FINISHED","AWARDED"].includes(statusUpper);
const timeUntil=kickoff?kickoff.getTime()-now:null;
const countdown=timeUntil!=null&&timeUntil>0?(()=>{const minutes=Math.ceil(timeUntil/60000);const days=Math.floor(minutes/1440);const hours=Math.floor((minutes%1440)/60);return days>0?`${days}d ${hours}h to kickoff`:hours>0?`${hours}h ${minutes%60}m to kickoff`:`${minutes}m to kickoff`})():null;
const [liveError,setLiveError]=useState("");
async function refreshLive(){
 if(refreshing)return;
 setRefreshing(true);
 try{
  const response=await fetch("/api/v1/matches/"+encodeURIComponent(match.id)+"/live");
  if(!response.ok)throw Error(response.status===503?"Provider temporarily rate limited":"Live score unavailable");
  const payload=await response.json();
  if(payload.status)setLiveStatus(payload.status);
  if(payload.score?.home!=null&&payload.score?.away!=null)setLiveScore(payload.score);
  setLastChecked(Date.now());
  setLiveError("");
 }catch(e){setLiveError(e instanceof Error?e.message:"Unable to refresh");}
 finally{setRefreshing(false)}
}
useEffect(()=>{let active=true;fetch("/api/v1/matches/"+encodeURIComponent(match.id)+"/live").then(r=>r.ok?r.json():null).then(p=>{if(!active||!p)return;if(p.status)setLiveStatus(p.status);if(p.score?.home!=null&&p.score?.away!=null)setLiveScore(p.score);setLastChecked(Date.now())}).catch(()=>{});return()=>{active=false}},[match.id]);
useEffect(()=>{if(isFinal)return;const nearKickoff=kickoff&&kickoff.getTime()-now<2*60*60*1000;const interval=isLive||nearKickoff?60000:300000;const timer=window.setInterval(()=>{void refreshLive()},interval);return()=>window.clearInterval(timer)},[match.id,isLive,isFinal,refreshing,Boolean(kickoff&&kickoff.getTime()-now<2*60*60*1000)]);
const actualLabel=result?.actual_outcome==="HOME"?match.home_team.name:result?.actual_outcome==="AWAY"?match.away_team.name:result?.actual_outcome==="DRAW"?"Draw":"";return <div className="match-center-page"><style>{`.match-center-live-tools{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-top:13px;color:#86f2ce;font-size:12px}.match-center-live-tools button{display:inline-flex;align-items:center;gap:6px;padding:7px 10px;border:1px solid #397d77;border-radius:8px;background:#123a3c;color:#a7ffe1;cursor:pointer}.match-center-live-tools button:disabled{opacity:.6;cursor:wait}.match-center-live-tools small{color:#9bb5c8}`}</style><button className="secondary-button match-center-back" onClick={onBack}><ArrowLeft size={15}/> Back to matches</button><section className="match-center-hero"><div className="match-center-meta"><span className="eyebrow">MATCH CENTER · {isLive?"LIVE":isFinal?"FULL TIME":statusUpper==="PAUSED"?"HALF TIME":countdown?"UPCOMING":"MATCH STATUS"}</span><h1>{match.competition||"Football"}</h1><p><CalendarDays size={12}/> {kickoff?kickoff.toLocaleString([],{dateStyle:"full",timeStyle:"short"}):"Kickoff TBA"}</p><div className="match-center-live-tools"><span>{isLive?"Match in progress":isFinal?"Match finished":countdown||"Awaiting match update"}</span><button type="button" onClick={()=>void refreshLive()} disabled={refreshing}><RefreshCw size={13}/>{refreshing?"Checking…":"Refresh match"}</button>{lastChecked&&<small>Checked {new Date(lastChecked).toLocaleTimeString([],{hour:"numeric",minute:"2-digit"})}</small>}{liveError&&<small role="status">{liveError} · Showing last known data</small>}</div></div><div className="match-center-versus"><Team team={match.home_team}/><div className="match-center-vs">{liveScore&&(isLive||isFinal)?`${liveScore.home} – ${liveScore.away}`:"VS"}</div><Team team={match.away_team}/></div></section>{message&&<div className="prediction-toast match-center-note">{message}</div>}{result&&<section className={"match-center-result "+result.status.toLowerCase()}><span>FINAL RESULT</span><strong>{match.home_team.short_name||match.home_team.name} {result.score.home??"—"}–{result.score.away??"—"} {match.away_team.short_name||match.away_team.name}</strong><p>Your pick was <b>{result.status==="CORRECT"?"correct ✓":"incorrect"}</b> · Result: {actualLabel}</p></section>}<div className="match-center-grid"><section className="match-center-panel"><span className="eyebrow">YOUR FAN PICK</span><h2>Who do you think wins?</h2><p>Your first pre-match pick earns 10 XP. You can change it before kickoff without earning more XP.</p><div className="match-center-picks"><button disabled={saving||match.prediction_locked} className={match.user_prediction==="HOME"?"picked":""} onClick={()=>onPick(match,"HOME")}>{match.home_team.short_name||match.home_team.name}</button><button disabled={saving||match.prediction_locked} className={match.user_prediction==="DRAW"?"picked":""} onClick={()=>onPick(match,"DRAW")}>Draw</button><button disabled={saving||match.prediction_locked} className={match.user_prediction==="AWAY"?"picked":""} onClick={()=>onPick(match,"AWAY")}>{match.away_team.short_name||match.away_team.name}</button></div><div className="match-center-lock"><LockKeyhole size={13}/>{match.prediction_locked?"Prediction locked after kickoff":"Pick locks when the match kicks off"}</div></section><section className="match-center-panel match-center-model"><span className="eyebrow">FANSPHERE MODEL</span><h2>Match outlook</h2><p>Compare your fan pick with our football model.</p><ModelOutlook key={match.id} matchId={match.id} homeTeam={match.home_team} awayTeam={match.away_team} competition={match.competition}/></section></div><section className="match-center-panel match-center-comparison"><span className="eyebrow">TEAM COMPARISON</span><h2>Matchup snapshot</h2>{(comparison?.home?.form?.length||comparison?.away?.form?.length)?<><div className="comparison-subheading">Recent form · last five finished matches</div><div className="comparison-form"><div><strong>{match.home_team.short_name||match.home_team.name}</strong><FormRow stats={comparison?.home}/></div><div><strong>{match.away_team.short_name||match.away_team.name}</strong><FormRow stats={comparison?.away}/></div></div><div className="comparison-table"><div><strong>{comparison?.home.goals_for??"—"}</strong><span>Goals scored</span><strong>{comparison?.away.goals_for??"—"}</strong></div><div><strong>{comparison?.home.goals_against??"—"}</strong><span>Goals conceded</span><strong>{comparison?.away.goals_against??"—"}</strong></div></div></>:null}{(comparison?.standings?.home?.length||comparison?.standings?.away?.length)?<><div className="comparison-subheading">Competition standings</div><div className="comparison-standings"><div><strong>{match.home_team.short_name||match.home_team.name}</strong>{comparison?.standings?.home?.length?comparison.standings.home.map((s,i)=><span key={i}>{s.competition||"Competition"} <b>#{s.position}</b></span>):<span>Standing unavailable</span>}</div><div><strong>{match.away_team.short_name||match.away_team.name}</strong>{comparison?.standings?.away?.length?comparison.standings.away.map((s,i)=><span key={i}>{s.competition||"Competition"} <b>#{s.position}</b></span>):<span>Standing unavailable</span>}</div></div></>:null}{!comparison?.home?.form?.length&&!comparison?.away?.form?.length&&!comparison?.standings?.home?.length&&!comparison?.standings?.away?.length?<p className="comparison-empty">Team comparison data is not available for this matchup from the current football data provider.</p>:null}</section></div>}
