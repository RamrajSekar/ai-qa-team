"use client";
/* eslint-disable @next/next/no-img-element -- Authorized private blob previews must not use the public image optimizer. */
import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/utils/api";
import { useFeatures } from "@/components/providers/FeatureFlagsProvider";

type Job = {upload_id:string; title:string; format:string; state:string; error_code?:string; expires_at:string; source_ids:string[];images:{image_id:string;page?:number;timestamp_seconds?:number}[]};
export default function KnowledgeUploads({ projectId, canDelete, onReady }: {projectId:string;canDelete:boolean;onReady:()=>Promise<void>}) {
  const {enabled}=useFeatures();const available=enabled("knowledge_uploads");
  const [jobs,setJobs]=useState<Job[]>([]);const [qualified,setQualified]=useState(false);const [limit,setLimit]=useState(0);
  const [file,setFile]=useState<File|null>(null);const [consent,setConsent]=useState(false);const [images,setImages]=useState(false);
  const [busy,setBusy]=useState(false);const [error,setError]=useState("");const [preview,setPreview]=useState<string|null>(null);
  const base=`/projects/${encodeURIComponent(projectId)}/knowledge/uploads`;
  const load=useCallback(async()=>{const response=await apiFetch(base,{cache:"no-store"});if(!response.ok)throw new Error("Could not load upload status.");setJobs(response.data.records);setQualified(response.data.enabled);setLimit(response.data.max_upload_bytes);},[base]);
  useEffect(()=>{if(available)void load().catch(()=>setError("Could not load upload status."));},[available,load]);
  useEffect(()=>()=>{if(preview)URL.revokeObjectURL(preview);},[preview]);
  async function upload(){
    if(!file||!qualified||file.size>limit)return;setBusy(true);setError("");
    try{
      const content=await file.arrayBuffer();const sha256=Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256",content))).map(value=>value.toString(16).padStart(2,"0")).join("");
      const format=file.name.split(".").at(-1)?.toLowerCase();
      const admitted=await apiFetch(base,{method:"POST",body:JSON.stringify({title:file.name.slice(0,200),format,size_bytes:file.size,sha256,consent_ai:consent,interpret_images:images})});
      if(!admitted.ok)throw new Error(typeof admitted.data?.detail==="string"?admitted.data.detail:"Upload was rejected. Check format, limits and AI consent.");
      const response=await apiFetch(`${base}/${admitted.data.upload_id}/content`,{method:"PUT",headers:{"Content-Type":"application/octet-stream"},body:content});
      if(!response.ok)throw new Error("Upload was not confirmed. Refresh status; do not automatically resubmit.");
      setFile(null);await load();
    }catch(failure){setError(failure instanceof Error?failure.message:"Upload was not confirmed. Refresh status before retrying.");}
    finally{setBusy(false);}
  }
  async function refresh(){setError("");try{await load();await onReady();}catch{setError("Could not refresh upload status.");}}
  return <section className="border rounded p-4 space-y-3" aria-label="Private document uploads"><h3>Private document uploads</h3>
    {!available?<p>Uploads are disabled until private storage and restricted document processing are qualified.</p>:<>
      {!qualified&&<p>Storage/worker qualification is incomplete. Uploads remain unavailable.</p>}
      <p>Use nonsensitive English product material only. Original files and selected images expire after the displayed retention date; derived text and reviewed knowledge remain. No source is approved automatically.</p>
      <input aria-label="Private knowledge file" type="file" disabled={busy||!qualified} accept=".txt,.pdf,.docx" onChange={event=>{setFile(event.target.files?.[0]||null);setConsent(false);}} />
      <label className="block"><input type="checkbox" disabled={busy||!qualified} checked={consent} onChange={event=>setConsent(event.target.checked)} />I authorize metered AI image interpretation for this nonsensitive material when requested.</label>
      {enabled("knowledge_image_interpretation")&&<label className="block"><input type="checkbox" disabled={busy||!qualified} checked={images} onChange={event=>setImages(event.target.checked)} />Interpret selected document images (up to four) with AI (additional requests).</label>}
      <button className="workspace-button" disabled={busy||!qualified||!file||file.size>limit} onClick={()=>void upload()}>Upload private source</button>
      <button className="workspace-button" disabled={busy} onClick={()=>void refresh()}>Refresh upload status</button>
      {jobs.map(job=><article className="border rounded p-3" key={job.upload_id}><h4>{job.title} · {job.state}</h4>{job.error_code&&<p>{job.error_code} · No automatic replay.</p>}<p>Originals expire: {new Date(job.expires_at).toLocaleString()}</p>
        {job.source_ids.map(id=><a className="block underline" key={id} href={`#source-${id}`}>Inspect derived source</a>)}
        {job.images.map(image=><button key={image.image_id} className="workspace-button" onClick={()=>void(async()=>{try{const response=await fetch(`${process.env.NEXT_PUBLIC_API_URL}${base}/${job.upload_id}/images/${image.image_id}`,{credentials:"include",cache:"no-store"});if(!response.ok)throw new Error();setPreview(URL.createObjectURL(await response.blob()));}catch{setError("Image is unavailable or expired.");}})()}>Inspect image {image.page?`on page ${image.page}`:`near ${image.timestamp_seconds?.toFixed(1)} seconds`}</button>)}
        {canDelete&&job.state!=="deleted"&&<button className="workspace-button" onClick={()=>{if(window.confirm("Delete originals and image artifacts? Derived source text and reviewed knowledge will remain."))void apiFetch(`${base}/${job.upload_id}`,{method:"DELETE"}).then(response=>{if(!response.ok)throw new Error();return load();}).catch(()=>setError("Deletion was not confirmed. Refresh status."));}}>Delete originals</button>}
      </article>)}
    </>}{error&&<p role="alert">{error}</p>}{preview&&<div>{/* Private authorized preview; URL is revoked when replaced or unmounted. */}
      <img src={preview} alt="Selected source image requiring human review" className="max-w-full" /><button className="workspace-button" onClick={()=>setPreview(null)}>Close image</button></div>}
  </section>;
}
