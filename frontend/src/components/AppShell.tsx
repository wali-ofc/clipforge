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
    description: "Find and render short clips",
    icon: ClapperIcon,
    match: (path) => path === "/" || path.startsWith("/jobs"),
  },
  {
    href: "/segmenter",
    label: "Segmenter",
    description: "Cut and join by timestamp",
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
      // storage is optional
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
        // storage is optional
      }
      return next;
    });
  }

  return (
    <div className="flex min-h-screen flex-col">
      {/* Compact top navigation for tablet and phone widths. */}
      <div className="flex w-full shrink-0 flex-col border-b border-line bg-paper-0 lg:hidden">
        <div className="flex items-center justify-between gap-3 px-5 py-3">
          <Link href="/" className="flex items-center gap-2.5" aria-label="ClipForge home">
            <LogoMark className="h-8 w-8" />
            <span className="text-[14px] font-extrabold tracking-[-0.04em] text-ink-900">
              CLIPFORGE
            </span>
          </Link>
          <span className="tally tally--live text-ink-600">Local</span>
        </div>
        <nav className="flex border-t border-line" aria-label="Tools (compact)">
          {navItems.map((item) => {
            const active = item.match(pathname);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                aria-current={active ? "page" : undefined}
                className={[
                  "flex flex-1 items-center justify-center gap-2 border-r border-line py-2.5 text-[12px] font-bold tracking-[-0.02em] last:border-r-0",
                  active ? "bg-accent-50 text-accent-700" : "text-ink-600",
                ].join(" ")}
              >
                <Icon className="h-4 w-4" />
                {item.label}
              </Link>
            );
          })}
        </nav>
      </div>

      <div className="flex min-h-0 flex-1">
      <aside
        className={[
          "sticky top-0 hidden h-screen shrink-0 flex-col border-r border-line bg-paper-0 transition-[width] duration-200 ease-out lg:flex",
          collapsed ? "w-[68px]" : "w-[246px]",
        ].join(" ")}
      >
        <div
          className={[
            "flex h-[74px] shrink-0 items-center border-b border-line",
            collapsed ? "justify-center px-2" : "justify-between gap-2 px-3",
          ].join(" ")}
        >
          <Link href="/" className="flex min-w-0 flex-1 items-center gap-2 overflow-hidden" aria-label="ClipForge home">
            <LogoMark className="h-8 w-8 shrink-0" />
            {!collapsed ? (
              <span className="block min-w-0 leading-none">
                <span className="block truncate text-[14px] font-extrabold tracking-[-0.04em] text-ink-900">
                  CLIPFORGE
                </span>
                <span className="mono mt-1 block truncate text-[8px] font-medium uppercase tracking-[0.14em] text-ink-500">
                  Local video workshop
                </span>
              </span>
            ) : null}
          </Link>
          {!collapsed ? (
            <button
              type="button"
              onClick={toggle}
              className="btn btn-quiet h-8 w-8 shrink-0 border border-line-strong"
              title="Collapse sidebar"
              aria-label="Collapse sidebar"
            >
              <PanelLeftIcon className="h-4 w-4" />
            </button>
          ) : null}
        </div>

        {collapsed ? (
          <div className="flex shrink-0 justify-center border-b border-line py-2">
            <button
              type="button"
              onClick={toggle}
              className="btn btn-quiet h-8 w-8 border border-line-strong"
              title="Expand sidebar"
              aria-label="Expand sidebar"
            >
              <PanelLeftIcon className="h-4 w-4 rotate-180" />
            </button>
          </div>
        ) : null}

        <nav className="flex-1 overflow-y-auto py-3" aria-label="Tools">
          {!collapsed ? (
            <p className="meta px-4 pb-2 pt-1">Tools</p>
          ) : null}
          {navItems.map((item) => {
            const active = item.match(pathname);
            const Icon = item.icon;
            return (
              <Link
                key={item.href}
                href={item.href}
                title={collapsed ? item.label : undefined}
                aria-current={active ? "page" : undefined}
                className={[
                  "group relative flex items-center border-b border-line py-3 transition-colors duration-150",
                  collapsed ? "justify-center px-2" : "gap-3 px-4",
                  active ? "bg-paper-50 text-ink-900" : "text-ink-600 hover:bg-paper-50 hover:text-ink-900",
                ].join(" ")}
              >
                <span
                  aria-hidden="true"
                  className={[
                    "absolute inset-y-0 left-0 w-[3px]",
                    active ? "bg-accent-500" : "bg-transparent group-hover:bg-line-strong",
                  ].join(" ")}
                />
                <Icon className={["h-[18px] w-[18px] shrink-0", active ? "text-accent-500" : "text-ink-500"].join(" ")} />
                {!collapsed ? (
                  <span className="block min-w-0">
                    <span className="block truncate text-[13px] font-bold tracking-[-0.02em]">
                      {item.label}
                    </span>
                    <span className="mono mt-0.5 block truncate text-[10px] text-ink-500">
                      {item.description}
                    </span>
                  </span>
                ) : null}
              </Link>
            );
          })}
        </nav>

        <div className="shrink-0 border-t border-line p-4">
          <div className="tally tally--live">
            <span className="h-1.5 w-1.5 shrink-0 rounded-full bg-ok-500" />
            {!collapsed ? <span className="text-ink-600">Runs on this machine</span> : null}
          </div>
          {!collapsed ? (
            <p className="mono mt-2 text-[9px] uppercase leading-4 tracking-[0.12em] text-ink-400">
              No cloud · No account
            </p>
          ) : null}
        </div>
      </aside>

      <div className="flex min-w-0 flex-1 flex-col">{children}</div>
      </div>
    </div>
  );
}
