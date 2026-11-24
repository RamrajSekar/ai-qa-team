"use client";
import {useEffect,useState} from "react";
import {useAuth} from "@/components/providers/AuthProvider";
import {knowledgeRequest} from "@/components/knowledge/knowledgeApi";
import {WorkspaceDialog} from "@/components/ui/workspace-dialog";

type Field="title"|"description"|"acceptance_criteria";
const fields:Field[]=["title","description","acceptance_criteria"];
const labels:Record<Field,string>={title:"Title",description:"Description",acceptance_criteria:"Acceptance criteria"};
interface Connection{connected:boolean;revision:number;site?:string;cloud_id?:string;project_key?:string;acceptance_field?:string|null}
interface Item{issue_id:string;issue_key:string;story_id:string|null;incoming:Record<Field,string>;current:Record<Field,string>|null;conflicts:Field[];warnings:string[]}
interface Preview{preview_id:string;items:Item[]}

export default function JiraImport({projectId,onClose,onImported}:{projectId:string;onClose:()=>void;onImported:()=>Promise<void>}){
 const {user}=useAuth();const admin=user?.account_role==="OWNER"||user?.account_role==="ADMIN";
 const base=`/projects/${encodeURIComponent(projectId)}/jira`;
 const [connection,setConnection]=useState<Connection|null>(null);
 const [keys,setKeys]=useState("");
 const [preview,setPreview]=useState<Preview|null>(null);const [selected,setSelected]=useState<Record<string,Field[]>>({});
 const [reviewed,setReviewed]=useState(false);const [busy,setBusy]=useState(false);const [error,setError]=useState("");const [done,setDone]=useState("");
 useEffect(()=>{let active=true;void knowledgeRequest<Connection>(base+"/connection").then(row=>{if(active){setConnection(row);}}).catch(failure=>{if(active)setError(failure instanceof Error?failure.message:"Connection unavailable.");});return()=>{active=false;};},[base]);
 async function act(work:()=>Promise<void>){setBusy(true);setError("");setDone("");try{await work();}catch(failure){setError(failure instanceof Error?failure.message:"Request failed. Refresh before retrying.");}finally{setBusy(false);}}
 const selections=Object.entries(selected).filter(([,values])=>values.length).map(([issue_id,values])=>({issue_id,fields:values}));
 return <WorkspaceDialog open onClose={onClose} title="Import stories from Jira" busy={busy}>
  <h2>Import stories from Jira</h2><p>Read-only Jira Cloud import. Review the preview before creating or updating stories. No AI request or Jira write is made.</p>
  <p role="status">{connection?connection.connected?`Connected to ${connection.site} · ${connection.project_key}`:"Jira is not connected.":"Loading connection…"}</p>
  {admin?<section className="space-y-3"><button className="workspace-button" disabled={busy||!connection} onClick={()=>void act(async()=>{
    const result=await knowledgeRequest<{state:string;authorization_url:string}>(base+"/oauth/start",{expected_revision:connection!.revision});
    sessionStorage.setItem("jira-oauth-pending",JSON.stringify({state:result.state,projectId}));
    window.location.assign(result.authorization_url);
  })}>{connection?.connected?"Reconnect Jira":"Connect Jira"}</button>
  <p>Sign in securely with Atlassian, then choose your Jira site and project. No API token is needed. This project connection can be used by authorized project members for reviewed imports.</p>
  {connection?.connected&&<button className="workspace-button" disabled={busy} onClick={()=>{if(!window.confirm("Disconnect Jira? Existing imported stories will remain."))return;void act(async()=>{setConnection(await knowledgeRequest(base+"/disconnect",{expected_revision:connection.revision}));setPreview(null);});}}>Disconnect</button>}
  </section>:<p>An account Owner or Admin who belongs to this project must configure Jira.</p>}
  <fieldset disabled={busy||!connection?.connected} className="space-y-3 border-0 p-0">
   <label className="block">Issue keys (up to 10)<textarea className="border rounded w-full" placeholder="APP-1, APP-2" value={keys} onChange={event=>{setKeys(event.target.value);setPreview(null);setReviewed(false);}} /></label>
   <button className="workspace-button" disabled={!keys.trim()} onClick={()=>void act(async()=>{const row=await knowledgeRequest<Preview>(base+"/preview",{issue_keys:keys.split(/[\s,]+/).filter(Boolean).map(value=>value.toUpperCase())});setPreview(row);setReviewed(false);setSelected(Object.fromEntries(row.items.map(item=>[item.issue_id,fields.filter(field=>!item.current||(!item.conflicts.includes(field)&&item.current[field]!==item.incoming[field]))])));})}>Preview import</button>
  </fieldset>
  {preview&&<section aria-label="Jira import preview" className="space-y-4"><h3>Review proposed changes</h3><p>Unselected fields keep local edits. Selecting a conflicting field explicitly replaces it. Content changes require fresh story/design review; previous executions remain unchanged.</p>
   {preview.items.map(item=><article className="border rounded p-3 space-y-3" key={item.issue_id}><h4>{item.issue_key} · {item.story_id?"Update existing story":"New story"}</h4>{item.warnings.map(warning=><p key={warning}>{warning}</p>)}
    {fields.map(field=><div key={field} className="border-t pt-2"><label><input type="checkbox" aria-label={`${item.issue_key} ${labels[field]}`} disabled={busy} checked={(selected[item.issue_id]||[]).includes(field)} onChange={event=>{setSelected(current=>({...current,[item.issue_id]:event.target.checked?[...(current[item.issue_id]||[]),field]:(current[item.issue_id]||[]).filter(value=>value!==field)}));setReviewed(false);}} /> {labels[field]} {item.conflicts.includes(field)&&<strong>— replaces local edits</strong>}</label>{item.current&&<p className="whitespace-pre-wrap">Current: {item.current[field]||"Not provided"}</p>}<p className="whitespace-pre-wrap">Jira: {item.incoming[field]||"Not provided"}</p></div>)}
   </article>)}
   <label className="block"><input type="checkbox" checked={reviewed} disabled={busy} onChange={event=>setReviewed(event.target.checked)} /> I reviewed the selected changes.</label>
   <button className="workspace-button workspace-primary" disabled={busy||!reviewed||!selections.length||preview.items.some(item=>!item.current&&(selected[item.issue_id]||[]).length>0&&(selected[item.issue_id]||[]).length!==fields.length)} onClick={()=>void act(async()=>{const result=await knowledgeRequest<{stories:{story_id:string;action:string}[]}>(base+"/apply",{preview_id:preview.preview_id,selections,reviewed:true});setDone(`${result.stories.length} stories imported. Existing duplicates were not recreated.`);setPreview(null);await onImported();})}>Import selected changes</button>
   <p>Apply errors may have an uncertain outcome. Retry the same preview to reconcile; do not recreate it blindly.</p>
  </section>}
  {error&&<p role="alert">{error}</p>}{done&&<p role="status">{done}</p>}
  <button className="workspace-button" disabled={busy} onClick={onClose}>Close</button>
 </WorkspaceDialog>;
}
