"use client";

import { useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { Invoice } from "@/lib/types/invoice";
import { Transaction } from "@/lib/types/bank";
import { formatINR, formatDate } from "@/lib/format";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface ManualMatchModalProps {
  clientId: string;
  onClose: () => void;
  onCreated: () => void;
}

export function ManualMatchModal({ clientId, onClose, onCreated }: ManualMatchModalProps) {
  const [invoices, setInvoices] = useState<Invoice[]>([]);
  const [transactions, setTransactions] = useState<Transaction[]>([]);
  const [selectedInvoiceId, setSelectedInvoiceId] = useState("");
  const [selectedTransactionId, setSelectedTransactionId] = useState("");
  const [matchedAmount, setMatchedAmount] = useState("");
  const [notes, setNotes] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [loadingData, setLoadingData] = useState(true);

  useEffect(() => {
    const load = async () => {
      try {
        const [invs, txns] = await Promise.all([
          apiFetch<Invoice[]>(`/clients/${clientId}/invoices?status=completed`),
          apiFetch<Transaction[]>(`/clients/${clientId}/transactions?recon_status=unmatched`),
        ]);
        setInvoices(invs.filter((i) => i.is_active));
        setTransactions(txns);
      } catch {
        setError("Failed to load data");
      } finally {
        setLoadingData(false);
      }
    };
    load();
  }, [clientId]);

  const selectedInvoice = invoices.find((i) => i.id === selectedInvoiceId);

  const handleCreate = async () => {
    if (!selectedInvoiceId || !selectedTransactionId) {
      setError("Please select both an invoice and a transaction");
      return;
    }

    setSaving(true);
    setError(null);

    try {
      const body: Record<string, any> = {
        invoice_id: selectedInvoiceId,
        transaction_id: selectedTransactionId,
      };
      if (matchedAmount) body.matched_amount = parseFloat(matchedAmount);
      if (notes) body.notes = notes;

      await apiFetch(`/clients/${clientId}/reconciliation/matches`, {
        method: "POST",
        body: JSON.stringify(body),
      });
      onCreated();
    } catch (err: any) {
      setError(err.message || "Failed to create match");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Manual Match</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            ✕
          </button>
        </div>

        {loadingData ? (
          <p className="text-sm text-muted-foreground py-4">Loading invoices and transactions...</p>
        ) : (
          <div className="space-y-4">
            <div>
              <Label className="text-sm">Invoice</Label>
              <select
                value={selectedInvoiceId}
                onChange={(e) => {
                  setSelectedInvoiceId(e.target.value);
                  const inv = invoices.find((i) => i.id === e.target.value);
                  if (inv?.total_amount) setMatchedAmount(inv.total_amount.toString());
                }}
                className="w-full h-9 text-sm border rounded px-2 bg-background mt-1"
              >
                <option value="">Select an invoice...</option>
                {invoices.map((inv) => (
                  <option key={inv.id} value={inv.id}>
                    {inv.invoice_number || inv.file_name} — {inv.invoice_type} — {inv.total_amount != null ? formatINR(inv.total_amount) : "N/A"}
                    {inv.invoice_date ? ` — ${formatDate(inv.invoice_date)}` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div>
              <Label className="text-sm">Transaction</Label>
              <select
                value={selectedTransactionId}
                onChange={(e) => setSelectedTransactionId(e.target.value)}
                className="w-full h-9 text-sm border rounded px-2 bg-background mt-1"
              >
                <option value="">Select a transaction...</option>
                {transactions.map((txn) => (
                  <option key={txn.id} value={txn.id}>
                    {formatDate(txn.transaction_date)} — {txn.transaction_type} — {formatINR(txn.amount)}
                    {txn.parsed_counterparty ? ` — ${txn.parsed_counterparty}` : ""}
                  </option>
                ))}
              </select>
            </div>

            <div className="grid grid-cols-2 gap-3">
              <div>
                <Label className="text-xs">Matched Amount</Label>
                <Input
                  type="number"
                  step="0.01"
                  value={matchedAmount}
                  onChange={(e) => setMatchedAmount(e.target.value)}
                  placeholder={selectedInvoice?.total_amount?.toString() || "0.00"}
                  className="h-8 text-sm"
                />
              </div>
              <div>
                <Label className="text-xs">Notes (optional)</Label>
                <Input
                  value={notes}
                  onChange={(e) => setNotes(e.target.value)}
                  className="h-8 text-sm"
                  placeholder="Reason for manual match"
                />
              </div>
            </div>

            {error && <p className="text-sm text-destructive">{error}</p>}

            <div className="flex justify-end gap-2">
              <Button variant="outline" size="sm" onClick={onClose}>
                Cancel
              </Button>
              <Button size="sm" onClick={handleCreate} disabled={saving || !selectedInvoiceId || !selectedTransactionId}>
                {saving ? "Creating..." : "Create Match"}
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
