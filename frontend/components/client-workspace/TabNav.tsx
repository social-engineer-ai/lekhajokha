"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";

interface TabNavProps {
  clientId: string;
}

const tabs = [
  { label: "Overview", href: "" },
  { label: "Bank", href: "/bank" },
  { label: "Invoices", href: "/invoices" },
  { label: "Reconciliation", href: "/reconciliation" },
  { label: "Tally", href: "/tally" },
  { label: "VPA", href: "/vpa" },
  { label: "Messages", href: "/messages" },
  { label: "GST", href: "/gst" },
];

export function TabNav({ clientId }: TabNavProps) {
  const pathname = usePathname();
  const basePath = `/dashboard/clients/${clientId}`;

  return (
    <div className="border-b">
      <nav className="flex gap-0 -mb-px">
        {tabs.map((tab) => {
          const href = `${basePath}${tab.href}`;
          const isActive =
            tab.href === ""
              ? pathname === basePath
              : pathname.startsWith(href);

          return (
            <Link
              key={tab.label}
              href={href}
              className={cn(
                "px-4 py-2 text-sm font-medium border-b-2 transition-colors",
                isActive
                  ? "border-primary text-primary"
                  : "border-transparent text-muted-foreground hover:text-foreground hover:border-muted"
              )}
            >
              {tab.label}
            </Link>
          );
        })}
      </nav>
    </div>
  );
}
