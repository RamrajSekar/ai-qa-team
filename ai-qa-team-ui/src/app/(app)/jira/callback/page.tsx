"use client";
import {useEffect,useState} from "react";
import Link from "next/link";
import {knowledgeRequest} from "@/components/knowledge/knowledgeApi";

interface Pending{state:string;projectId:string;code:string}
interface Grant{grant_id:string;sites:{cloud_id:string;site:string}[]}
export default function JiraCallback(){
 const [pending,setPending]=useState<Pending|null>(null);const [projectId,setProjectId]=useState("");
 const [grant,setGrant]=useState<Grant|null>(null);const [cloud,setCloud]=useState("");
 const [projects,setProjects]=useState<{key:string;name:string}[]>([]);const [project,setProject]=useState("");
 const [mapping,setMapping]=useState("");const [busy,setBusy]=useState(false);const [error,setError]=useState("");const [done,setDone]=useState(false);
 useEffect(()=>{
  // Remove authorization parameters before any further navigation. Never persist the code.
  const query=new URLSearchParams(window.location.search);window.history.replaceState(null,"","/jira/callback");
  const raw=sessionStorage.getItem("jira-oauth-pending");
  if(!query.size)return;
  try{
   const saved=JSON.parse(raw||"null");
   if(!saved?.projectId||typeof saved.state!=="string"||saved.state!==query.get("state"))throw new Error();
   setProjectId(saved.projectId);sessionStorage.removeItem("jira-oauth-pending");
   if(query.has("error")){setError("Jira access was not granted. Return to Stories to connect again.");return;}
   const code=query.get("code");if(!code)throw new Error();
   setPending({state:saved.state,projectId:saved.projectId,code});
  }catch{setError("This Jira sign-in could not be verified. Return to Stories and connect again.");}
 },[]);
 async function act(work:()=>Promise<void>){setBusy(true);setError("");try{await work();}catch(failure){setError(failure instanceof Error?failure.message:"Jira connection failed. Connect again.");}finally{setBusy(false);}}
 const base=`/projects/${encodeURIComponent(projectId)}/jira/oauth`;
 return <main className="design-page space-y-4"><h1>Connect Jira</h1>
  {pending&&<><p>Continue to retrieve the Jira sites you authorized. This step runs once; if interrupted, start a new connection.</p><button className="workspace-button workspace-primary" disabled={busy} onClick={()=>void act(async()=>{
   const value=pending;setPending(null);
   const result=await knowledgeRequest<Grant>(`/projects/${encodeURIComponent(value.projectId)}/jira/oauth/complete`,{state:value.state,code:value.code});setGrant(result);
  })}>Continue Jira connection</button></>}
  {grant&&!done&&<fieldset disabled={busy} className="space-y-4"><legend>Choose your Jira site and project</legend>
   <label className="block">Jira site<select aria-label="Jira site" value={cloud} onChange={event=>{setCloud(event.target.value);setProjects([]);setProject("");}}><option value="">Select a site</option>{grant.sites.map(site=><option key={site.cloud_id} value={site.cloud_id}>{site.site}</option>)}</select></label>
   <button className="workspace-button" disabled={!cloud} onClick={()=>void act(async()=>{const result=await knowledgeRequest<{projects:{key:string;name:string}[];limited:boolean}>(base+"/projects",{grant_id:grant.grant_id,cloud_id:cloud});setProjects(result.projects);setProject("");if(result.limited)setError("Showing the first 50 accessible projects. Further project browsing is not available yet.");})}>Load Jira projects</button>
   <label className="block">Jira project<select aria-label="Jira project" value={project} onChange={event=>setProject(event.target.value)}><option value="">Select a project</option>{projects.map(item=><option key={item.key} value={item.key}>{item.name} ({item.key})</option>)}</select></label>
   <details><summary>Optional acceptance criteria mapping</summary><label>Acceptance criteria field<input value={mapping} placeholder="customfield_10001" onChange={event=>setMapping(event.target.value)} /></label><p>Leave blank if there is no separate field. Missing criteria remain empty.</p></details>
   <button className="workspace-button workspace-primary" disabled={!project} onClick={()=>void act(async()=>{await knowledgeRequest(base+"/select",{grant_id:grant.grant_id,cloud_id:cloud,project_key:project,acceptance_field:mapping.trim()||null});setDone(true);setGrant(null);})}>Save Jira connection</button>
  </fieldset>}
  {busy&&<p role="status">Connecting…</p>}{error&&<p role="alert">{error}</p>}{done&&<p role="status">Jira connected. Return to Stories to preview an import.</p>}
  {!pending&&!grant&&!done&&!error&&<p>Return to Stories to begin a new Jira connection.</p>}
  <Link className="workspace-button" href={projectId?`/projects/${encodeURIComponent(projectId)}/stories`:"/projects"}>Back to Stories</Link>
 </main>;
}
