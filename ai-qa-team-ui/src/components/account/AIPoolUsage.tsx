"use client";
import {useEffect,useState} from "react";
import {useProjects} from "@/hooks/useProjects";
import {apiFetch} from "@/utils/api";
import styles from "./SubscriptionUsage.module.css";

type Mode="MANAGED"|"BYOK";
const pools={MANAGED:{label:"Managed AI Requests",used:"managed_ai_credits_used",limit:"managed_ai_credits_limit"},BYOK:{label:"BYOK AI Requests",used:"byok_ai_requests_used",limit:"byok_ai_requests_limit"}} as const;
export default function AIPoolUsage({usage,limits}:{usage:Partial<Record<"managed_ai_credits_used"|"byok_ai_requests_used",number>>;limits:Partial<Record<"managed_ai_credits_limit"|"byok_ai_requests_limit",number|null>>}){
 const {projects,loading,failed}=useProjects();const [selection,setSelection]=useState("");
 const projectId=projects.find(project=>project.project_id===selection)?.project_id||projects[0]?.project_id||"";
 const [resolved,setResolved]=useState<{project:string;mode:Mode|null}>();
 useEffect(()=>{
  if(!projectId)return;
  const controller=new AbortController();
  void apiFetch(`/projects/${encodeURIComponent(projectId)}/ai/configuration`,{signal:controller.signal}).then(response=>{
   if(!response.ok)throw new Error();
   const mode=response.data===null?"MANAGED":response.data?.mode;
   if(mode!=="MANAGED"&&mode!=="BYOK")throw new Error();
   if(!controller.signal.aborted)setResolved({project:projectId,mode});
  }).catch(()=>{if(!controller.signal.aborted)setResolved({project:projectId,mode:null});});
  return()=>controller.abort();
 },[projectId]);
 const mode=resolved?.project===projectId?resolved.mode:null;
 function meter(poolMode:Mode){const pool=pools[poolMode];const current=mode===poolMode;const used=usage[pool.used]??0,limit=limits[pool.limit];return <section aria-label={pool.label} className={`${styles.aiUsageTile} ${current?styles.currentAiTile:""}`}>
  <div className={styles.aiTileHeader}><h4>{pool.label}</h4>{current&&<span className={styles.currentBadge}>CURRENT</span>}</div>
  <dl className={styles.meterLine}><dt>Requests used</dt><dd>{limit===undefined?"Unavailable":limit===null?`${used} / Unlimited`:`${used} / ${limit}`}</dd></dl>
  {typeof limit==="number"&&limit>0&&<progress className={styles.progress} aria-label={`${pool.label} usage`} value={Math.min(Math.max(used,0),limit)} max={limit} />}
  <p className={styles.note}>{limit===undefined?"Allowance not configured":limit===null?"Unlimited allowance":`${Math.max(0,limit-used)} remaining`}</p>
  <p className={styles.note}>{poolMode==="MANAGED"?"Uses platform credentials. One request may generate multiple items.":"Uses your key and provider billing. One request may generate multiple items."}</p>
 </section>;}
 return <div className={styles.group}>
  {projects.length>1&&<label>AI mode for project<select aria-label="AI mode for project" value={projectId} onChange={event=>setSelection(event.target.value)}>{projects.map(project=><option key={project.project_id} value={project.project_id}>{project.name}</option>)}</select></label>}
  {!mode&&<p role="status" className={styles.note}>{loading||(!failed&&projectId&&resolved?.project!==projectId)?"Loading saved AI mode…":projectId?"Saved AI mode unavailable. Both balances are shown.":"No accessible project selected. Both balances are shown."}</p>}
  <div className={styles.grid}>{meter("MANAGED")}{meter("BYOK")}</div>
 </div>;
}
