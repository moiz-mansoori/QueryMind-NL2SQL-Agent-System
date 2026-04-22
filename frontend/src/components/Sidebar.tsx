"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  AlertTriangle,
  Database,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Query", icon: Search },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/failures", label: "Failures", icon: AlertTriangle },
];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed top-0 left-0 h-screen w-[220px] bg-[#111118] border-r border-[#1E1E2E] flex flex-col z-50">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-6 border-b border-[#1E1E2E]">
        <Database className="w-6 h-6 text-[#00D4FF]" />
        <span className="text-lg font-bold tracking-tight text-white">
          QueryMind
        </span>
      </div>

      {/* Navigation */}
      <nav className="flex-1 flex flex-col gap-1 px-3 py-4">
        {NAV_ITEMS.map(({ href, label, icon: Icon }) => {
          const isActive = pathname === href;
          return (
            <Link
              key={href}
              href={href}
              className={`
                flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                transition-all duration-200
                ${
                  isActive
                    ? "bg-[#00D4FF]/10 text-[#00D4FF] shadow-[inset_0_0_0_1px_rgba(0,212,255,0.2)]"
                    : "text-[#8888A0] hover:text-white hover:bg-white/5"
                }
              `}
            >
              <Icon className="w-[18px] h-[18px]" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-5 py-4 border-t border-[#1E1E2E]">
        <p className="text-[11px] text-[#555] leading-tight">
          NL2SQL Agent System
        </p>
      </div>
    </aside>
  );
}
