"use client";

import { useState } from "react";
import { ReconciliationMatch } from "@/lib/types/reconciliation";
import { formatINR, formatDate } from "@/lib/format";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { apiFetch } from "@/lib/api";

interface MatchRowProps {
  match: ReconciliationMatch;
  clientId: string;
  onUpdate: () => void;
}

export function MatchRow({ match, clientId, onUpdate }: MatchRowProps) {
  const [expanded, setExpanded] = useState(false);
  const [loading, setLoading] = useState(false);

  const inv = match.invoice_summary;
  const txn = match.transaction_summary;

  const confidenceVariant =
    match.confidence_score >= 80
      ? "default"
      : match.confidence_score >= 60
      ? "secondary"
      : "destructive";

  const handleConfirm = async () => {
    setLoading(true);
    try {
      await apiFetch(`/clients/${clientId}/reconciliation/matches/${match.id}`, {
        method: "PUT",
        body: JSON.stringify({ is_confirmed: true }),
      });
      onUpdate();
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  const handleRemove = async () => {
    setLoading(true);
    try {
      await apiFetch(`/clients/${clientId}/reconciliation/matches/${match.id}`, {
        method: "DELETE",
      });
      onUpdate();
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  };

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="cursor-pointer hover:bg-muted/30 border-t"
      >
        <td className="px-3 py-2">
          {inv?.invoice_number || <span className="text-muted-foreground italic">N/A</span>}
          {inv?.invoice_date && (
            <span className="text-xs text-muted-foreground ml-2">
              {formatDate(inv.invoice_date)}
            </span>
          )}
        </td>
        <td className="px-3 py-2 max-w-[200px] truncate">
          {txn?.transaction_date && formatDate(txn.transaction_date)}
          {txn?.parsed_counterparty && (
            <span className="text-xs text-muted-foreground ml-2">{txn.parsed_counterparty}</span>
          )}
        </td>
        <td className="px-3 py-2 text-right tabular-nums">
          {formatINR(match.matched_amount)}
        </td>
        <td className="px-3 py-2 text-center">
          <Badge variant={confidenceVariant}>{match.confidence_score}%</Badge>
        </td>
        <td className="px-3 py-2 text-center">
          <Badge variant={match.is_confirmed ? "default" : "secondary"}>
            {match.is_confirmed ? "Confirmed" : "Pending"}
          </Badge>
        </td>
        <td className="px-3 py-2 text-center">
          <div className="flex gap-1 justify-center" onClick={(e) => e.stopPropagation()}>
            {!match.is_confirmed && (
              <Button size="sm" variant="outline" onClick={handleConfirm} disabled={loading}>
                Confirm
              </Button>
            )}
            <Button size="sm" variant="outline" onClick={handleRemove} disabled={loading}>
              Remove
            </Button>
          </div>
        </td>
      </tr>
      {expanded && (
        <tr>
          <td colSpan={6} className="px-4 py-3 bg-muted/20">
            <div className="grid grid-cols-2 gap-4 text-sm">
              <div>
                <h4 className="font-medium mb-1">Invoice</h4>
                <div className="space-y-1 text-muted-foreground">
                  <div>Number: {inv?.invoice_number || "—"}</div>
                  <div>Date: {inv?.invoice_date ? formatDate(inv.invoice_date) : "—"}</div>
                  <div>Type: {inv?.invoice_type}</div>
                  <div>Seller: {inv?.seller_name || "—"}</div>
                  <div>Buyer: {inv?.buyer_name || "—"}</div>
                  <div>Total: {inv?.total_amount != null ? formatINR(inv.total_amount) : "—"}</div>
                </div>
              </div>
              <div>
                <h4 className="font-medium mb-1">Transaction</h4>
                <div className="space-y-1 text-muted-foreground">
                  <div>Date: {txn?.transaction_date ? formatDate(txn.transaction_date) : "—"}</div>
                  <div>Mode: {txn?.transaction_mode || "—"}</div>
                  <div>Type: {txn?.transaction_type}</div>
                  <div>Amount: {txn ? formatINR(txn.amount) : "—"}</div>
                  <div>Counterparty: {txn?.parsed_counterparty || "—"}</div>
                  <div className="truncate">Desc: {txn?.raw_description || "—"}</div>
                </div>
              </div>
            </div>
            {match.notes && (
              <div className="mt-2 text-xs text-muted-foreground">
                Notes: {match.notes}
              </div>
            )}
            <div className="mt-1 text-xs text-muted-foreground">
              Method: {match.match_method} | Confidence: {match.confidence_score}%
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
