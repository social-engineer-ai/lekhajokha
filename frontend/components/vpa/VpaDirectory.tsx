"use client";

import { useState } from "react";
import { VpaEntry } from "@/lib/types/vpa";
import { Input } from "@/components/ui/input";
import { VpaRow } from "./VpaRow";

interface VpaDirectoryProps {
  entries: VpaEntry[];
  clientId: string;
  onUpdate: () => void;
  onEdit: (entry: VpaEntry) => void;
}

const SOURCE_OPTIONS = [
  { value: "", label: "All Sources" },
  { value: "transaction_aggregate", label: "Txn Aggregate" },
  { value: "reconciliation", label: "Reconciliation" },
  { value: "manual", label: "Manual" },
  { value: "cashfree", label: "Cashfree" },
  { value: "whatsapp_profile", label: "WhatsApp" },
];

export function VpaDirectory({ entries, clientId, onUpdate, onEdit }: VpaDirectoryProps) {
  const [search, setSearch] = useState("");
  const [sourceFilter, setSourceFilter] = useState("");
  const [verifiedFilter, setVerifiedFilter] = useState<string>("");

  const filtered = entries.filter((e) => {
    if (search) {
      const term = search.toLowerCase();
      if (
        !e.vpa.toLowerCase().includes(term) &&
        !(e.resolved_name || "").toLowerCase().includes(term) &&
        !(e.gstin || "").toLowerCase().includes(term)
      ) {
        return false;
      }
    }
    if (sourceFilter && e.source !== sourceFilter) return false;
    if (verifiedFilter === "verified" && !e.is_verified) return false;
    if (verifiedFilter === "unverified" && e.is_verified) return false;
    return true;
  });

  return (
    <div className="space-y-3">
      {/* Filters */}
      <div className="flex gap-3">
        <Input
          placeholder="Search VPA, name, or GSTIN..."
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="max-w-xs"
        />
        <select
          value={sourceFilter}
          onChange={(e) => setSourceFilter(e.target.value)}
          className="border rounded-md px-3 py-2 text-sm bg-background"
        >
          {SOURCE_OPTIONS.map((opt) => (
            <option key={opt.value} value={opt.value}>{opt.label}</option>
          ))}
        </select>
        <select
          value={verifiedFilter}
          onChange={(e) => setVerifiedFilter(e.target.value)}
          className="border rounded-md px-3 py-2 text-sm bg-background"
        >
          <option value="">All Status</option>
          <option value="verified">Verified</option>
          <option value="unverified">Unverified</option>
        </select>
      </div>

      {/* Table */}
      <div className="rounded-md border overflow-x-auto">
        <table className="w-full text-left">
          <thead>
            <tr className="border-b bg-muted/50">
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">VPA</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Name</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">GSTIN</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Source</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Confidence</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground text-center">Verified</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground text-center">Txns</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Last Seen</th>
              <th className="px-3 py-2 text-xs font-medium text-muted-foreground">Actions</th>
            </tr>
          </thead>
          <tbody>
            {filtered.length === 0 ? (
              <tr>
                <td colSpan={9} className="px-3 py-8 text-center text-sm text-muted-foreground">
                  {entries.length === 0
                    ? "No VPA entries yet. Run resolution or add manually."
                    : "No entries match your filters."}
                </td>
              </tr>
            ) : (
              filtered.map((entry) => (
                <VpaRow
                  key={entry.id}
                  entry={entry}
                  clientId={clientId}
                  onUpdate={onUpdate}
                  onEdit={onEdit}
                />
              ))
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
