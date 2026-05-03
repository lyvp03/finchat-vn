"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  MessageSquare,
  LineChart,
  Newspaper,
  Settings,
  Coins
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { name: "Dashboard", href: "/dashboard", icon: LayoutDashboard },
  { name: "Chatbot", href: "/chat", icon: MessageSquare },
  { name: "Gold Prices", href: "/prices", icon: LineChart },
  { name: "News", href: "/news", icon: Newspaper },
  { name: "Settings", href: "/settings", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <div className="flex flex-row md:flex-col h-auto md:h-screen w-full md:w-64 lg:w-72 border-b md:border-b-0 md:border-r border-border/50 bg-background/50 backdrop-blur-xl px-4 py-3 md:px-5 md:py-6 overflow-x-auto md:overflow-x-visible shrink-0 z-10 sticky top-0 md:static">
      <div className="flex items-center gap-2 px-2 md:mb-8 mr-6 md:mr-0 shrink-0">
        <div className="p-1.5 bg-amber-500/20 rounded-lg">
          <Coins className="h-5 w-5 md:h-6 md:w-6 text-amber-500" />
        </div>
        <span className="text-xl md:text-2xl font-bold tracking-tight text-foreground hidden sm:block md:block">
          Finchat<span className="text-amber-500 font-medium"> vn</span>
        </span>
      </div>

      <nav className="flex flex-row md:flex-col flex-1 space-x-1 md:space-x-0 md:space-y-1 overflow-x-auto md:overflow-x-visible items-center md:items-stretch scrollbar-hide">
        {navItems.map((item) => {
          const isActive = pathname.startsWith(item.href);
          return (
            <Link
              key={item.name}
              href={item.href}
              className={cn(
                "group flex items-center gap-2 md:gap-3 rounded-lg px-3 md:px-4 py-2 md:py-3 text-sm md:text-base font-medium transition-all duration-200 whitespace-nowrap shrink-0",
                isActive
                  ? "bg-amber-500/10 text-amber-500 shadow-sm shadow-amber-500/5 ring-1 ring-amber-500/20"
                  : "text-muted-foreground hover:bg-muted hover:text-foreground"
              )}
            >
              <item.icon className={cn("h-4 w-4 md:h-5 md:w-5", isActive ? "text-amber-500" : "")} />
              <span className="hidden sm:inline md:inline">{item.name}</span>
            </Link>
          );
        })}
      </nav>

      <div className="mt-auto px-2 hidden md:block">
        <div className="rounded-lg bg-card border border-border/50 p-4">
          <p className="text-sm font-medium text-foreground">
            Vietnam Gold Market
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Analytics & Insights
          </p>
        </div>
      </div>
    </div>
  );
}
