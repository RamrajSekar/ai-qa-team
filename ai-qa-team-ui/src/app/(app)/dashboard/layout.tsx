"use client";

import { useEffect } from "react";
// import Sidebar from "@/components/layout/Sidebar";
// import { Topbar } from "@/components/layout/Topbar";
import { useAuth } from "@/components/providers/AuthProvider";

// export default function DashboardLayout({
//   children,
// }: {
//   children: React.ReactNode;
// }) {
//   const { refreshSubscription } = useAuth();

//   useEffect(() => {
//     // Always refresh limits/usage once dashboard layout loads
//     refreshSubscription();
//   }, [refreshSubscription]);

//   return (
//     <div className="flex min-h-screen bg-[var(--qs-bg-soft)]">
//       {/* Sidebar */}
//       <Sidebar />

//       {/* Main Content */}
//       <div className="flex flex-col flex-1">
//         <Topbar />
//         <main className="p-6">{children}</main>
//       </div>
//     </div>
//   );
// }

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { refreshSubscription } = useAuth();

  useEffect(() => {
    refreshSubscription(); // refresh usage & limits
  }, [refreshSubscription]);

  // ❗ No sidebar/topbar here — global layout already includes them
  return <>{children}</>;
}