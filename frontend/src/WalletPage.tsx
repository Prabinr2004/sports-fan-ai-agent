import {useEffect,useState} from "react";
import {Gem, RefreshCw, ArrowUpRight, ArrowDownLeft, History} from "lucide-react";
type WalletData={gems:number;spendable_xp:number;xp_per_gem:number};
type WalletEvent={id:string;currency:"XP"|"GEM";amount:number;source:string;created_at:string|null};
type Access={free_remaining:number;extra_remaining:number;gems_per_analysis:number};
export default function WalletPage(){
 const [wallet,setWallet]=useState<WalletData|null>(null);
 const [access,setAccess]=useState<Access|null>(null);
 const [quantity,setQuantity]=useState(2);
 const [history,setHistory]=useState<WalletEvent[]>([]);
 const [historyFilter,setHistoryFilter]=useState<"ALL"|"XP"|"GEM">("ALL");
 const [historyError,setHistoryError]=useState("");
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 const [error,setError]=useState("");
 async function refresh(){
  const [w,a]=await Promise.all([fetch("/api/v1/economy"),fetch("/api/v1/analysis/access")]);
  if(!w.ok||!a.ok)throw new Error("Could not load wallet.");
  setWallet(await w.json());setAccess(await a.json());
  try{const h=await fetch("/api/v1/economy/history");if(!h.ok)throw new Error("History unavailable.");const payload=await h.json();setHistory(payload.events||[]);setHistoryError("");}catch{setHistoryError("Could not load recent activity.");}
 }
 useEffect(()=>{refresh().catch(e=>setError(String(e)))},[]);
 async function exchange(){
  if(!wallet)return;
  setBusy(true);setMessage("");setError("");
  try{
   const r=await fetch("/api/v1/economy/exchange",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({gems:quantity})});
   const data=await r.json();
   if(!r.ok)throw new Error(data.detail||"Exchange failed.");
   await refresh();
   setMessage(`Exchanged ${quantity*wallet.xp_per_gem} spendable XP for ${quantity} Gems.`);
  }catch(e){setError(e instanceof Error?e.message:"Exchange failed.");}
  finally{setBusy(false)}
 }
 const cost=quantity*(wallet?.xp_per_gem||200);
 return <div className="profile-page" style={{maxWidth:1000}}>
  <style>{`.wallet-history{margin:24px 0;padding:20px;border:1px solid #29475c;border-radius:16px;background:#0b1d2e}.wallet-history-heading{display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:16px;margin-bottom:15px}.wallet-history-heading h2{display:flex;align-items:center;gap:9px;margin:7px 0}.wallet-history-heading p{font-size:13px;color:#9db5c8}.wallet-history-filters{display:flex;gap:7px}.wallet-history-filters button{background:#10283a;color:#b6cad9;border:1px solid #35536b;border-radius:9px;padding:9px 14px;cursor:pointer}.wallet-history-filters button[aria-pressed="true"]{border-color:#72ecc7;color:#72ecc7;background:#143e3e}.wallet-history-list{display:flex;flex-direction:column;gap:8px;max-height:420px;overflow-y:auto;overscroll-behavior:contain;padding-right:6px;scrollbar-width:thin;scrollbar-color:#456b7d #0b1d2e}.wallet-history-list::-webkit-scrollbar{width:7px}.wallet-history-list::-webkit-scrollbar-thumb{background:#456b7d;border-radius:8px}.wallet-history-list::-webkit-scrollbar-track{background:#0b1d2e}.wallet-history-item{display:flex;align-items:center;gap:12px;padding:12px;background:#0e2639;border:1px solid #233e54;border-radius:12px}.wallet-history-icon{width:36px;height:36px;display:grid;place-items:center;border-radius:10px;flex-shrink:0}.wallet-history-icon.earned{color:#7cf3c7;background:#153c3d}.wallet-history-icon.spent{color:#ffbc8c;background:#3a2b2d}.wallet-history-details{display:flex;flex:1;min-width:0;flex-direction:column;gap:5px}.wallet-history-details strong{font-size:13px;text-transform:capitalize}.wallet-history-details small{color:#9db5c8;font-size:11px}.wallet-history-amount{font-size:13px;white-space:nowrap}.wallet-history-amount.earned{color:#7cf3c7}.wallet-history-amount.spent{color:#ffbc8c}.wallet-history-empty{padding:16px;color:#9db5c8}`}</style>
  <span className="eyebrow">FANSPHERE ECONOMY</span><h1>Gem Wallet</h1>
  <p>One place to view Gems, exchange earned XP, and track match unlocks.</p>
  {error&&<p role="alert" style={{color:"#ff9da5"}}>{error}</p>}
  {wallet&&<><div className="profile-stat-grid" style={{marginTop:24}}>
   <div><Gem/><span>Available Gems</span><strong>{wallet.gems}</strong></div>
   <div><Gem/><span>Spendable XP</span><strong>{wallet.spendable_xp}</strong></div>
   <div><Gem/><span>Free match today</span><strong>{access?.free_remaining??"—"}</strong></div>
   <div><Gem/><span>Paid unlock slots left</span><strong>{access?.extra_remaining??"—"}</strong></div>
  </div>
  <section className="profile-analysis-access" style={{marginTop:22,display:"block"}}>
   <span className="eyebrow">XP → GEMS</span><h2 style={{margin:"8px 0"}}>Exchange XP for Gems</h2>
   <p style={{marginBottom:12}}>1 Gem costs {wallet.xp_per_gem} spendable XP. An additional match costs {access?.gems_per_analysis??2} Gems. Lifetime XP and your level do not decrease.</p>
   <label htmlFor="gem-quantity" style={{display:"block",marginBottom:6}}>Number of Gems</label>
   <select id="gem-quantity" value={quantity} onChange={e=>setQuantity(Number(e.target.value))} style={{background:"#10273b",color:"#e6f8ff",border:"1px solid #34536b",borderRadius:9,padding:"10px 14px"}}>
    {Array.from({length:20},(_,i)=>i+1).map(n=><option key={n} value={n}>{n} {n===1?"Gem":"Gems"}</option>)}
   </select>
   <p style={{marginTop:10}}>Exchange cost: <strong>{cost} XP</strong></p>
   <button className="primary-button" disabled={busy||wallet.spendable_xp<cost} onClick={exchange}>{busy?"Exchanging...":`Exchange ${cost} XP for ${quantity} Gems`}</button>
   {wallet.spendable_xp<cost&&<p style={{color:"#a9bfd3",marginTop:10}}>You need {cost-wallet.spendable_xp} more spendable XP for this exchange.</p>}
   {message&&<p role="status" style={{color:"#7cf3c7",marginTop:10}}>{message}</p>}
  </section>
  <p style={{marginTop:16}}>Today's allowance: {access?.free_remaining??0} free match remaining and {access?.extra_remaining??0} additional paid unlock slots. Slots are not free matches: each requires {access?.gems_per_analysis??2} Gems.</p>
  <section className="wallet-history">
   <div className="wallet-history-heading"><div><span className="eyebrow">REWARDS LEDGER</span><h2><History size={22}/> Activity history</h2><p>Recent earned and spent XP and Gems, newest first.</p></div><div className="wallet-history-filters">{(["ALL","XP","GEM"] as const).map(filter=><button type="button" key={filter} aria-pressed={historyFilter===filter} onClick={()=>setHistoryFilter(filter)}>{filter==="ALL"?"All":filter==="XP"?"XP":"Gems"}</button>)}</div></div>
   {historyError&&<p role="alert">{historyError}</p>}
   {!historyError&&history.filter(event=>historyFilter==="ALL"||event.currency===historyFilter).length===0&&<p className="wallet-history-empty">No transactions in this category yet.</p>}
   <div className="wallet-history-list">{history.filter(event=>historyFilter==="ALL"||event.currency===historyFilter).map(event=><div className="wallet-history-item" key={event.id}><span className={event.amount>=0?"wallet-history-icon earned":"wallet-history-icon spent"}>{event.amount>=0?<ArrowDownLeft size={19}/>:<ArrowUpRight size={19}/>}</span><div className="wallet-history-details"><strong>{event.source==="daily_quiz"?"Daily Quiz reward":event.source==="gem_exchange"?"XP exchanged for Gems":event.source==="xp_exchange"?"Gems received from XP exchange":event.source==="match_analysis"?"Match analysis unlock":event.source.replaceAll("_"," ")}</strong><small>{event.created_at?new Date(event.created_at).toLocaleString():"Date unavailable"}</small></div><strong className={event.amount>=0?"wallet-history-amount earned":"wallet-history-amount spent"}>{event.amount>0?"+":""}{event.amount} {event.currency==="GEM"?"Gems":"XP"}</strong></div>)}</div>
  </section>
  <button className="secondary-button" onClick={()=>refresh().catch(e=>setError(String(e)))}><RefreshCw size={16}/> Refresh wallet</button>
  </>}
 </div>;
}

