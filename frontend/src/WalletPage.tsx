import {useEffect,useState} from "react";
import {Gem, RefreshCw} from "lucide-react";
type WalletData={gems:number;spendable_xp:number;xp_per_gem:number};
type Access={free_remaining:number;extra_remaining:number;gems_per_analysis:number};
export default function WalletPage(){
 const [wallet,setWallet]=useState<WalletData|null>(null);
 const [access,setAccess]=useState<Access|null>(null);
 const [quantity,setQuantity]=useState(2);
 const [busy,setBusy]=useState(false);
 const [message,setMessage]=useState("");
 const [error,setError]=useState("");
 async function refresh(){
  const [w,a]=await Promise.all([fetch("/api/v1/economy"),fetch("/api/v1/analysis/access")]);
  if(!w.ok||!a.ok)throw new Error("Could not load wallet.");
  setWallet(await w.json());setAccess(await a.json());
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
  <button className="secondary-button" onClick={()=>refresh().catch(e=>setError(String(e)))}><RefreshCw size={16}/> Refresh wallet</button>
  </>}
 </div>;
}
