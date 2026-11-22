"use client";
import {useRef,useState} from "react";
import {knowledgeRequest} from "./knowledgeApi";

interface Answer {
  status:"supported"|"not_covered"|"conflicting";answer:string;knowledge_version_id:string|null;
  citations:{claim_id:string;quote:string;source_id:string;source_quote:string;information_type:string;segment_index:number|null}[];
}

export default function AskKnowledge({base,onInspect,onCorrect}:{base:string;onInspect:(id:string)=>void;onCorrect:(id:string)=>void}) {
  const [question,setQuestion]=useState("");const [answer,setAnswer]=useState<Answer|null>(null);
  const [busy,setBusy]=useState(false);const [error,setError]=useState("");
  const request=useRef<string|null>(null);
  async function submit(retry=false){
    if(retry&&!window.confirm("Submit a new AI request? The previous attempt may have used your allowance."))return;
    if(retry)request.current=null;
    request.current ||=crypto.randomUUID().replaceAll("-","");
    setBusy(true);setError("");setAnswer(null);
    try{setAnswer(await knowledgeRequest<Answer>(base+"/ask",{question,request_id:request.current}));request.current=null;}
    catch(failure){setError(failure instanceof Error?failure.message:"Could not answer. The request may have used your allowance.");}
    finally{setBusy(false);}
  }
  return <section className="workspace-card p-5 space-y-4" aria-label="Ask your QA Agent">
    <h2>Ask your QA Agent</h2><p>Ask about approved knowledge. Uses your AI allowance. Exclude credentials and personal data.</p>
    <label className="block">Your question<textarea className="border rounded w-full" rows={3} maxLength={2000} disabled={busy} value={question} onChange={event=>{setQuestion(event.target.value);request.current=null;setError("");}} /></label>
    <button className="workspace-button workspace-primary" disabled={busy||question.trim().length<3||!!error} onClick={()=>void submit()}>{busy?"Checking approved knowledge…":"Ask"}</button>
    {error&&<div role="alert"><p>{error}</p><p>Not retried automatically. Questions and answers are unsaved; resubmitting may use another request.</p><button className="workspace-button" disabled={busy} onClick={()=>void submit(true)}>Submit new request explicitly</button></div>}
    {answer&&<section aria-label="Knowledge answer" className="space-y-3"><strong>{answer.status==="supported"?"Answer from approved knowledge":answer.status==="conflicting"?"Conflicting knowledge — review needed":"Not covered"}</strong><p className="whitespace-pre-wrap">{answer.answer}</p>
      {answer.citations.map((item,index)=><article className="border rounded p-3 space-y-2" key={`${item.claim_id}-${index}`}><p>{item.quote}</p><p>Information type: {item.information_type}</p><details><summary>Source excerpt</summary><blockquote>{item.source_quote}</blockquote>{item.segment_index!==null&&<p>Transcript segment {item.segment_index+1}</p>}</details><div className="workspace-actions"><button className="workspace-button" onClick={()=>onInspect(item.source_id)}>Review source</button><button className="workspace-button" onClick={()=>onCorrect(item.claim_id)}>Propose correction</button></div></article>)}
      <p>Verify cited rules. Answers do not update knowledge; refresh clears this conversation.</p>
    </section>}
  </section>;
}
