"use client";
import {useCallback,useEffect,useState} from "react";
import {IconAction} from "@/components/ui/icon-action";
import {apiFetch} from "@/utils/api";
import {DesignBadge} from "./DesignWorkspace";

interface Queue {items:{type:string;id:string;title:string;status:string;href:string;detail:string;pending_with:string[]}[];has_more:boolean;unavailable_types:string[]}

export default function PendingReviews({projectId}:{projectId:string}){
 const [data,setData]=useState<Queue|null>(null);const [page,setPage]=useState(0);
 const [loading,setLoading]=useState(true);const [error,setError]=useState("");
 const load=useCallback(async(signal?:AbortSignal)=>{
  setLoading(true);setError("");setData(null);
  try{
   const response=await apiFetch(`/projects/${encodeURIComponent(projectId)}/pending-reviews?page=${page}&limit=20`,{signal:signal?AbortSignal.any([signal,AbortSignal.timeout(15000)]):AbortSignal.timeout(15000)});
   if(!response.ok||!Array.isArray(response.data?.items)||!Array.isArray(response.data?.unavailable_types))throw new Error("Pending reviews are unavailable.");
   if(!signal?.aborted)setData(response.data);
  }catch(e){if(!signal?.aborted)setError(e instanceof Error?e.message:"Pending reviews are unavailable.");}
  finally{if(!signal?.aborted)setLoading(false);}
 },[projectId,page]);
 useEffect(()=>{const controller=new AbortController();void load(controller.signal);return()=>controller.abort();},[load]);
 return <section className="workspace-panel" aria-labelledby="pending-reviews-title">
  <div className="workspace-panel-header"><h2 id="pending-reviews-title">Pending reviews</h2><button className="workspace-button" disabled={loading} onClick={()=>void load()}>Refresh reviews</button></div>
  <div className="workspace-panel-body space-y-3">
   <p className="text-sm">Review and approve items in their original workspace.</p>
   {loading?<p role="status">Loading pending reviews…</p>:error?<p role="alert">{error}</p>:data&&<>
    {!!data.unavailable_types.length&&<p role="alert">Some reviews could not be loaded: {data.unavailable_types.join(", ")}. Refresh to try again.</p>}
    {data.items.length?<div className="overflow-x-auto"><table className="w-full text-sm" aria-label="Pending reviews"><thead><tr><th className="p-3 text-left">Type</th><th className="p-3 text-left">Item</th><th className="p-3 text-left">Status</th><th className="p-3 text-left">Pending with</th><th className="p-3 text-left">Action</th></tr></thead><tbody>
     {data.items.map(item=><tr className="border-t" key={`${item.type}:${item.id}`}><td className="p-3">{item.type}</td><td className="p-3"><strong>{item.title}</strong>{item.detail&&<p>{item.detail}</p>}</td><td className="p-3"><DesignBadge tone={item.status==="Blocked"||item.status==="Needs attention"?"warning":undefined}>{item.status}</DesignBadge></td><td className="p-3">{item.pending_with?.length?item.pending_with.join(", "):"No eligible reviewer"}</td><td className="p-3"><IconAction action="review" label="Review" href={item.href} /></td></tr>)}
    </tbody></table></div>:<p>{data.unavailable_types.length?"Review results are incomplete. Refresh to try again.":"No pending reviews on this page."}</p>}
    <nav className="flex flex-wrap items-center gap-3" aria-label="Review pages"><button className="workspace-button" disabled={!page} onClick={()=>setPage(p=>p-1)}>Previous reviews</button><span>Page {page+1}</span><button className="workspace-button" disabled={!data.has_more} onClick={()=>setPage(p=>p+1)}>Next reviews</button></nav>
    <p className="text-xs">Pending with shows eligible reviewers. Up to 20 items per type, per page.</p>
   </>}
  </div>
 </section>;
}
