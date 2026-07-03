"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Search,
  LayoutDashboard,
  AlertTriangle,
  Database,
  ExternalLink,
} from "lucide-react";

const NAV_ITEMS = [
  { href: "/", label: "Query", icon: Search },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/failures", label: "Failures", icon: AlertTriangle },
];

const TECH_STACK = ["LangGraph", "Groq", "pgvector", "Next.js"];

export default function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed top-0 left-0 h-screen w-[220px] bg-[#111118] border-r border-[#1E1E2E] flex flex-col z-50">
      {/* Logo */}
      <div className="flex items-center gap-2.5 px-5 py-6 border-b border-[#1E1E2E]">
        <div className="w-8 h-8 rounded-lg bg-[#00D4FF]/10 border border-[#00D4FF]/20 flex items-center justify-center">
          <Database className="w-4 h-4 text-[#00D4FF]" />
        </div>
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
                relative flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium
                transition-all duration-200
                ${
                  isActive
                    ? "bg-[#00D4FF]/10 text-[#00D4FF] shadow-[inset_0_0_0_1px_rgba(0,212,255,0.2)]"
                    : "text-[#8888A0] hover:text-white hover:bg-white/5"
                }
              `}
            >
              {isActive && (
                <span className="absolute left-0 top-1/2 -translate-y-1/2 w-0.5 h-5 bg-[#00D4FF] rounded-r-full" />
              )}
              <Icon className="w-[18px] h-[18px]" />
              {label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="px-4 py-4 border-t border-[#1E1E2E] space-y-3">
        {/* Tech Stack Pills */}
        <div className="flex flex-wrap gap-1.5">
          {TECH_STACK.map((tech) => (
            <span
              key={tech}
              className="px-2 py-0.5 text-[9px] font-bold uppercase tracking-wider rounded-md bg-white/5 text-[#555] border border-[#1E1E2E]"
            >
              {tech}
            </span>
          ))}
        </div>
        {/* GitHub Link */}
        <a
          href="https://github.com"
          target="_blank"
          rel="noopener noreferrer"
          className="flex items-center gap-2 text-[11px] text-[#555] hover:text-white transition-colors"
        >
          {/* GitHub SVG icon */}
          <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="currentColor" aria-hidden="true">
            <path d="M12 2C6.477 2 2 6.484 2 12.017c0 4.425 2.865 8.18 6.839 9.504.5.092.682-.217.682-.483 0-.237-.008-.868-.013-1.703-2.782.605-3.369-1.343-3.369-1.343-.454-1.158-1.11-1.466-1.11-1.466-.908-.62.069-.608.069-.608 1.003.07 1.531 1.032 1.531 1.032.892 1.53 2.341 1.088 2.91.832.092-.647.35-1.088.636-1.338-2.22-.253-4.555-1.113-4.555-4.951 0-1.093.39-1.988 1.029-2.688-.103-.253-.446-1.272.098-2.65 0 0 .84-.27 2.75 1.026A9.564 9.564 0 0112 6.844c.85.004 1.705.115 2.504.337 1.909-1.296 2.747-1.027 2.747-1.027.546 1.379.202 2.398.1 2.651.64.7 1.028 1.595 1.028 2.688 0 3.848-2.339 4.695-4.566 4.943.359.309.678.92.678 1.855 0 1.338-.012 2.419-.012 2.747 0 .268.18.58.688.482A10.019 10.019 0 0022 12.017C22 6.484 17.522 2 12 2z" />
          </svg>
          <span>View on GitHub</span>
        </a>
      </div>
    </aside>
  );
}
