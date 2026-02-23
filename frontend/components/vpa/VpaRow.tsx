"use client";

import { useState } from "react";
import { VpaEntry } from "@/lib/types/vpa";
import { apiFetch } from "@/lib/api";
import { formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

interface VpaRowProps {
  entry: VpaEntry;
  clientId: string;
  onUpdate: () => void;
  onEdit: (entry: VpaEntry) => void;
}

const SOURCE_BADGE: Record<string, { label: string; className: string }> = {
  transaction_aggregate: { label: "Txn Aggregate", className: "bg-blue-100 text-blue-800" },
  reconciliation: { label: "Reconciliation", className: "bg-green-100 text-green-800" },
  manual: { label: "Manual", className: "bg-gray-100 text-gray-800" },
  cashfree: { label: "Cashfree", className: "bg-purple-100 text-purple-800" },
  whatsapp_profile: { label: "WhatsApp", className: "bg-orange-100 text-orange-800" },
};

export function VpaRow({ entry, clientId, onUpdate, onEdit }: VpaRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [verifying, setVerifying] = useState(false);
  const [deleting, setDeleting] = useState(false);

  const sourceBadge = SOURCE_BADGE[entry.source] || { label: entry.source, className: "bg-gray-100 text-gray-800" };

  const handleVerify = async () => {
    setVerifying(true);
    try {
      await apiFetch(`/clients/${clientId}/vpa/${entry.id}/verify`, { method: "POST" });
      onUpdate();
    } catch {
      // ignore
    } finally {
      setVerifying(false);
    }
  };

  const handleDelete = async () => {
    setDeleting(true);
    try {
      await apiFetch(`/clients/${clientId}/vpa/${entry.id}`, { method: "DELETE" });
      onUpdate();
    } catch {
      // ignore
    } finally {
      setDeleting(false);
    }
  };

  return (
    <>
      <tr
        className="border-b hover:bg-muted/50 cursor-pointer"
        onClick={() => setExpanded(!expanded)}
      >
        <td className="px-3 py-2 text-sm font-mono">{entry.vpa}</td>
        <td className="px-3 py-2 text-sm">{entry.resolved_name || "—"}</td>
        <td className="px-3 py-2 text-sm font-mono">{entry.gstin || "—"}</td>
        <td className="px-3 py-2">
          <span className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${sourceBadge.className}`}>
            {sourceBadge.label}
          </span>
        </td>
        <td className="px-3 py-2">
          <div className="flex items-center gap-2">
            <div className="w-16 h-2 rounded-full bg-muted overflow-hidden">
              <div
                className="h-full rounded-full bg-primary"
                style={{ width: `${Math.min(entry.confidence, 100)}%` }}
              />
            </div>
            <span className="text-xs text-muted-foreground">{entry.confidence}</span>
          </div>
        </td>
        <td className="px-3 py-2 text-center">
          {entry.is_verified ? (
            <span className="text-green-600" title="Verified">&#10003;</span>
          ) : (
            <span className="text-muted-foreground">—</span>
          )}
        </td>
        <td className="px-3 py-2 text-sm text-center">{entry.transaction_count}</td>
        <td className="px-3 py-2 text-sm text-muted-foreground">
          {entry.last_seen_at ? formatDate(entry.last_seen_at) : "—"}
        </td>
        <td className="px-3 py-2">
          <div className="flex gap-1" onClick={(e) => e.stopPropagation()}>
            {!entry.is_verified && (
              <Button size="sm" variant="outline" onClick={handleVerify} disabled={verifying}>
                {verifying ? "..." : "Verify"}
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={() => onEdit(entry)}>
              Edit
            </Button>
            <Button size="sm" variant="outline" onClick={handleDelete} disabled={deleting}>
              {deleting ? "..." : "Delete"}
            </Button>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr className="border-b bg-muted/30">
          <td colSpan={9} className="px-6 py-3">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <span className="text-muted-foreground">PAN:</span>{" "}
                <span className="font-mono">{entry.pan || "—"}</span>
              </div>
              <div>
                <span className="text-muted-foreground">Created:</span>{" "}
                {formatDate(entry.created_at)}
              </div>
              {entry.notes && (
                <div className="col-span-2">
                  <span className="text-muted-foreground">Notes:</span>{" "}
                  {entry.notes}
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
