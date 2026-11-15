import { apiFetch } from "@/utils/api";

export async function knowledgeRequest<T>(path: string, body?: unknown): Promise<T> {
  const response = await apiFetch(path, body === undefined ? {} : { method: "POST", body: JSON.stringify(body) });
  if (!response.ok) {
    const detail = response.data?.detail;
    throw new Error(typeof detail === "string" ? detail : detail?.message || `Request rejected (HTTP ${response.status}).`);
  }
  return response.data as T;
}

export interface Claim {
  claim_id: string; category: "terminology" | "role" | "business_rule" | "workflow" | "exception" | "unknown";
  statement: string; epistemic_status: "expected" | "observed" | "inferred" | "unknown";
  source_id: string; segment_index: number | null; quote: string;
}
export interface Source {
  origin?: {kind:string;story_id?:string;story_digest?:string;upload_id?:string;page_number?:number;block_number?:number;timestamp_seconds?:number};
  source_id: string; title: string; kind: "document" | "recording_transcript"; text: string;
  segments: { start_seconds: number; end_seconds: number; text: string }[];
}
export interface KnowledgeVersion {
  version_id: string; title: string; claims: Claim[]; status: "draft" | "approved";
  clarification_answers: Record<string, string>; content_digest: string;
  parent_version_id?: string | null;
  changes?: { action: "add" | "replace" | "remove"; claim_id: string; before: Claim | null; after: Claim | null }[];
  approved_by?: string;
  approved_by_name?: string;
  approved_at?: string;
}

export interface TrainingProposal { claim: Claim; decision: "pending" | "confirmed" | "rejected" | "clarify"; clarification_question?: string; clarification_answer?: string }
export interface TrainingSession {
  review_id: string; title: string; mode: "training" | "correction" | "removal";
  source_id: string | null; base_version_id: string | null; draft_version_id: string;
  state: "reviewing" | "saving" | "saved" | "rejected"; extraction_state: "not_started" | "running" | "completed" | "uncertain";
  revision: number; attempt: number; proposals: TrainingProposal[];
  removal_reason?: string;
  removal_impact?: Record<string, {id:string;title:string}[]>;
  clarification_questions: string[]; clarification_answers: Record<string,string>; removed_claim_ids: string[];
  saved_version?: KnowledgeVersion;
}
