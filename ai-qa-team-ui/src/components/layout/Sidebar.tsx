"use client";

import Link from "next/link";
import { motion } from "framer-motion";
import { LayoutDashboard, Settings, FolderOpen, Play, TestTube } from "lucide-react";

export default function Sidebar() {
  const menu = [
    { label: "Dashboard", icon: LayoutDashboard, href: "/dashboard" },
    { label: "Projects", icon: FolderOpen, href: "/projects" },
    { label: "Scenarios", icon: TestTube, href: "/scenarios" },
    { label: "Executions", icon: Play, href: "/executions" },
    { label: "Settings", icon: Settings, href: "/settings" },
  ];

  return (
    <aside className="w-64 h-full border-r bg-white dark:bg-neutral-900 dark:border-neutral-800 p-4 flex flex-col">
      <h1 className="text-xl font-bold mb-6 dark:text-neutral-100">AI QA Team</h1>

      <nav className="space-y-2">
        {menu.map((item, i) => (
          <motion.div
            key={i}
            initial={{ opacity: 0, x: -10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ delay: i * 0.05 }}
          >
            <Link
              href={item.href}
              className="flex items-center gap-3 px-3 py-2 rounded-lg hover:bg-neutral-100 dark:hover:bg-neutral-800"
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
            </Link>
          </motion.div>
        ))}
      </nav>
    </aside>
  );
}
