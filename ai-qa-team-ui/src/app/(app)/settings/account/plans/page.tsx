import Link from "next/link";
import Pricing from "@/components/marketing/Pricing";
import "@/components/marketing/marketing.css";

export default function AccountPlansPage() {
  return <div>
    <Link className="workspace-button" href="/settings/account">Back to account</Link>
    <div className="public-landing"><Pricing workspace /></div>
  </div>;
}
