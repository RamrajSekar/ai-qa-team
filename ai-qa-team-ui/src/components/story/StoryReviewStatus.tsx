import Link from "next/link";
import {DesignBadge} from "@/components/projects/DesignWorkspace";

export interface StoryReviewSummary {
 state:string;finding_count:number;blocker_count:number;
 story_approval?:{state:string;approved_by_name?:string;basis?:string};comparison_state?:string;
 unresolved_finding_count?:number;unresolved_blocker_count?:number;
}
export default function StoryReviewStatus({projectId,storyId,summary,loading,error}:{projectId:string;storyId:string;summary?:StoryReviewSummary;loading:boolean;error:boolean}){
 const unavailable=error||(!loading&&!summary);
 const state=summary?.story_approval?.state||(summary?.state==="reviewed"?"approved":summary?.state==="stale"?"needs_review":"in_review");
 const label=loading?"Loading":unavailable?"Unavailable":state==="approved"?(summary?.story_approval?.basis==="manual_review"?"Approved · Manual review":"Approved"):state==="needs_review"?"Needs review":"In review";
 const comparison=loading?"Loading":unavailable?"Unavailable":summary?.comparison_state==="needs_refresh"||(!summary?.comparison_state&&summary?.state==="stale")?"Needs refresh":summary?.comparison_state==="current"?"Current":"Not compared";
 const findings=summary?.unresolved_finding_count??(summary?.state==="needs_review"?summary.finding_count:0);
 const blockers=summary?.unresolved_blocker_count??(summary?.state==="needs_review"?summary.blocker_count:0);
 const href=`/projects/${encodeURIComponent(projectId)}/stories/${encodeURIComponent(storyId)}#story-analysis`;
 return <><td className="p-3 border"><Link href={href} className="design-back-link"><DesignBadge tone={state==="approved"&&!unavailable?"positive":undefined}>{label}</DesignBadge></Link>{state==="approved"&&summary?.story_approval?.approved_by_name&&<p className="text-xs">{summary.story_approval.approved_by_name}</p>}</td>
 <td className="p-3 border"><Link href={href} className="design-back-link"><DesignBadge>{comparison}</DesignBadge></Link>{summary&&!unavailable&&<p className="text-xs">{findings} unresolved findings · {blockers} blockers</p>}</td></>;
}
