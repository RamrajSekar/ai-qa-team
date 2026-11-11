import Link from "next/link";
import PlatformAdminGuard from "@/components/platform/PlatformAdminGuard";

export default function PlatformAdminPage() {
  return <PlatformAdminGuard><div className="workspace-page-header"><div><p className="workspace-eyebrow">Control plane</p><h1>Platform Administration</h1><p className="workspace-description">Manage AI QA Team platform operations.</p></div></div><section className="workspace-panel"><div className="workspace-panel-header"><h2>Available now</h2></div><div className="workspace-panel-body"><Link className="workspace-row" href="/platform-admin/prompts"><div><p className="workspace-row-title">Prompt Management</p><p className="workspace-row-subtitle">Manage immutable platform prompt versions and activation.</p></div><span>Open →</span></Link></div></section><section className="workspace-panel"><div className="workspace-panel-header"><h2>Future platform modules</h2></div><div className="platform-future-grid">{["Customers","Customer Onboarding","Subscriptions","Usage","Projects Overview","Platform Settings"].map((item) => <span className="workspace-badge" key={item}>{item}</span>)}</div></section></PlatformAdminGuard>;
}
