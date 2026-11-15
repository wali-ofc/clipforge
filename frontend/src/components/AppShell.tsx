"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useEffect, useState } from "react";

import {
  ClapperIcon,
  LogoMark,
  PanelLeftIcon,
  ScissorsIcon,
} from "@/components/icons";

type NavItem = {
  href: string;
  label: string;
  description: string;
  icon: typeof ClapperIcon;
  match: (path: string) => boolean;
};

const navItems: NavItem[] = [
  {
    href: "/",
    label: "AI Clipper",
    description: "Auto-find and render short clips",
    icon: ClapperIcon,
    match: (path) => path === "/" || path.startsWith("/jobs"),
  },
  {
    href: "/segmenter",
    label: "Segmenter",
    description: "Cut or join clips by timestamps",
    icon: ScissorsIcon,
    match: (path) => path.startsWith("/segmenter"),
  },
];

export function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname() || "/";
  const [collapsed, setCollapsed] = useState(false);

  useEffect(() => {
    try {
      const saved = window.localStorage.getItem("clipforge.sidebarCollapsed");
      if (saved === "1") setCollapsed(true);
    } catch {
      // ignore
    }
  }, []);

  function toggle() {
    setCollapsed((value) => {
      const next = !value;
      try {
        window.localStorage.setItem(
          "clipforge.sidebarCollapsed",
          next ? "1" : "0",
        );
      } catch {
        // ignore
      }
      return next;
    });
  }

  return (
    <div className="flex min-h-screen bg-paper-100 text-ink-900">
      <aside
        className={[
          "sticky top-0 flex h-screen shrink-0 flex-col border-r border-line bg-paper-50/95 backdrop-blur-sm transition-[width] duration-200",
          collapsed ? "w-[72px]" : "w-[248px]",
        ].join(" ")}
      >
        <div
          className={[
            "flex h-16 items-center border-b border-line",
            collapsed ? "justify-center px-2" : "justify-between px-3",
          ].join(" ")}
        >
          <Link href="/" className="flex items-center gap-2.5 overflow-hidden rounded-lg">
            <LogoMark className="h-9 w-9 shrink-0" />
            {!collapsed ? (
              <div className="min-w-0 leading-none">
                <div className="truncate text-[15px] font-semibold tracking-[-0.02em] text-ink-900">
                  ClipForge
                </div>
                <div className="mt-1 truncate text-[9px] font-medium uppercase tracking-[0.18em] text-ink-500">
                  Local tools
                </div>
              </div>
            ) : null}
          </Link>
          {!collapsed ? (
            <button
              type="button"
              onClick={toggle}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-white text-ink-500 transition hover:border-line-strong hover:text-ink-800"
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
            >
              <PanelLeftIcon className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        {collapsed ? (
          <div className="flex justify-center border-b border-line py-2">
            <button
              type="button"
              onClick={toggle}
              className="inline-flex h-8 w-8 items-center justify-center rounded-lg border border-line bg-white text-ink-500 transition hover:border-line-strong hover:text-ink-800"
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <PanelLeftIcon className="h-4 w-4 rotate-180" />
            </button>
          </div>
        ) : null}

        <nav className="flex-1 space-y-1 p-2">
          {!collapsed ? (
            <p className="px-2 pb-1 pt-2 text-[10px] font-semibold uppercase tracking-[0.16em] text-ink-400">
              Tools
            </p>
          ) : null}
          {navItems.map((item) => {
            const active = item.match(pathname);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? item.label : undefined}
                className={[
                  "group flex items-center rounded-xl border transition",
                  collapsed ? "justify-center px-0 py-2.5" : "gap-3 px-3 py-2.5",
                  active
                    ? "border-teal-200 bg-teal-50 text-teal-800"
                    : "border-transparent text-ink-600 hover:border-line hover:bg-white hover:text-ink-900",
                ].join(" ")}
              >
                <span
                  className={[
                    "flex h-8 w-8 shrink-0 items-center justify-center rounded-lg border",
                    active
                      ? "border-teal-200 bg-white text-teal-700"
                      : "border-line bg-paper-100 text-ink-500 group-hover:text-ink-800",
                  ].join(" ")}
                >
                  <Icon className="h-4.5 w-4.5" />
                </span>
                {!collapsed ? (
                  <span className="min-w-0">
                    <span className="block truncate text-sm font-medium">
                      {item.label}
                    </span>
                    <span className="block truncate text-[11px] text-ink-500">
                      {item.description}
                    </span>
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div
          className={[
            "border-t border-line p-2",
            collapsed ? "flex justify-center" : "",
          ].join(" ")}
        >
          <div
            className={[
              "flex items-center gap-2 rounded-lg border border-line bg-white px-2.5 py-2 text-[10px] font-medium text-ink-500",
              collapsed ? "justify-center px-2" : "",
            ].join(" ")}
            title="Runs on this machine"
          >
            <span className="status-dot h-1.5 w-1.5 shrink-0 rounded-full bg-emerald-500" />
            {!collapsed ? <span>Runs on this machine</span> : null}
          </div>
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
    </div>
  );
}