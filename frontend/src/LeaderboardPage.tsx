import { useEffect, useState } from "react";
import { Crown, LoaderCircle, Medal, RefreshCw, Trophy } from "lucide-react";

type Entry = { rank:number; user_id:number; display_name:string; total_xp:number; level:number; is_current_user:boolean };
type Leaderboard = { entries:Entry[]; notice?:string };

export default function LeaderboardPage(){
 const [data,setData]=useState<Leaderboard|null>(null); const [error,setError]=useState(""); const [refreshing,setRefreshing]=useState(false);
 async function load(refresh=false){if(refresh)setRefreshing(true);setError("");try{const r=await fetch("/api/v1/leaderboard");const p=await r.json();if(!r.ok)throw new Error(p.detail||"Could not load leaderboard.");setData(p)}catch(e){setError(e instanceof Error?e.message:"Could not load leaderboard.")}finally{if(refresh)setRefreshing(false)}} useEffect(()=>{load()},[]);
 if(error&&!data)return <section className="empty-state"><Trophy size={34}/><h2>Leaderboard unavailable</h2><p>{error}</p></section>;
 if(!data)return <div className="matches-loading"><LoaderCircle className="spin"/> Loading leaderboard...</div>;
 const leader=data.entries[0];
 return <div className="leaderboard-page"><span className="eyebrow">FAN RANKINGS</span><h1>Leaderboard</h1><p>Ranked by XP earned from FanSphere activities.</p><button className="secondary-button" disabled={refreshing} onClick={()=>load(true)}>{refreshing?<LoaderCircle className="spin" size={16}/>:<RefreshCw size={16}/>} {refreshing?"Refreshing...":"Refresh Rankings"}</button>{error&&<p role="alert">{error}</p>}{leader&&<section className="leader-hero"><Crown size={30}/><div><span>TOP FAN</span><h2>{leader.display_name}</h2><p>Level {leader.level} · {leader.total_xp} XP</p></div><strong>#{leader.rank}</strong></section>}<section className="leaderboard-table"><div className="leaderboard-head"><span>Rank</span><span>Fan</span><span>Level</span><span>XP</span></div>{data.entries.map(entry=><div className={entry.is_current_user?"leaderboard-row current":"leaderboard-row"} key={entry.user_id}><span className="rank-cell">{entry.rank<=3?<Medal size={18}/>:null}#{entry.rank}</span><span className="fan-cell"><span className="fan-avatar">{entry.display_name.split(" ").map(x=>x[0]).slice(0,2).join("")}</span><span><strong>{entry.display_name}</strong>{entry.is_current_user&&<small>You</small>}</span></span><span>Level {entry.level}</span><strong>{entry.total_xp} XP</strong></div>)}</section>{data.notice&&<p className="leaderboard-note">{data.notice}</p>}</div>;
}
