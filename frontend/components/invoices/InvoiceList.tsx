"use client";

import { useState } from "react";
import { Invoice } from "@/lib/types/invoice";
import { Badge } from "@/components/ui/badge";
import { InvoiceDetail } from "./InvoiceDetail";

interface InvoiceListProps {
  invoices: Invoice[];
  clientId: string;
  onRefresh: () => void;
}

export function InvoiceList({ invoices, clientId, onRefresh }: InvoiceListProps) {
  const [expandedId, setExpandedId] = useState<string | null>(null);

  if (invoices.length === 0) {
    return (
      <div className="text-center py-8 text-muted-foreground">
        <p className="text-sm">No invoices found</p>
      </div>
    );
  }

  return (
    <div className="border rounded-lg overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-muted/50">
          <tr>
            <th className="text-left px-3 py-2 font-medium">Invoice #</th>
            <th className="text-left px-3 py-2 font-medium">Date</th>
            <th className="text-left px-3 py-2 font-medium">Seller / Buyer</th>
            <th className="text-right px-3 py-2 font-medium">Amount</th>
            <th className="text-center px-3 py-2 font-medium">Type</th>
            <th className="text-center px-3 py-2 font-medium">Status</th>
          </tr>
        </thead>
        <tbody>
          {invoices.map((inv) => (
            <InvoiceRow
              key={inv.id}
              invoice={inv}
              clientId={clientId}
              isExpanded={expandedId === inv.id}
              onToggle={() => setExpandedId(expandedId === inv.id ? null : inv.id)}
              onRefresh={onRefresh}
            />
          ))}
        </tbody>
      </table>
    </div>
  );
}

function InvoiceRow({
  invoice,
  clientId,
  isExpanded,
  onToggle,
  onRefresh,
}: {
  invoice: Invoice;
  clientId: string;
  isExpanded: boolean;
  onToggle: () => void;
  onRefresh: () => void;
}) {
  const statusVariant =
    invoice.processing_status === "completed"
      ? "default"
      : invoice.processing_status === "failed"
      ? "destructive"
      : "secondary";

  const typeVariant = invoice.invoice_type === "sales" ? "default" : "secondary";

  return (
    <>
      <tr
        onClick={onToggle}
        className="cursor-pointer hover:bg-muted/30 border-t"
      >
        <td className="px-3 py-2">
          {invoice.invoice_number || (
            <span className="text-muted-foreground italic">Pending</span>
          )}
        </td>
        <td className="px-3 py-2">
          {invoice.invoice_date || (
            <span className="text-muted-foreground">—</span>
          )}
        </td>
        <td className="px-3 py-2 max-w-[200px] truncate">
          {invoice.seller_name || invoice.buyer_name || invoice.file_name}
        </td>
        <td className="px-3 py-2 text-right tabular-nums">
          {invoice.total_amount != null
            ? `₹${Number(invoice.total_amount).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`
            : "—"}
        </td>
        <td className="px-3 py-2 text-center">
          <Badge variant={typeVariant}>{invoice.invoice_type}</Badge>
        </td>
        <td className="px-3 py-2 text-center">
          <Badge variant={statusVariant}>{invoice.processing_status}</Badge>
        </td>
      </tr>
      {isExpanded && (
        <tr>
          <td colSpan={6} className="p-0">
            <InvoiceDetail
              invoiceId={invoice.id}
              clientId={clientId}
              onRefresh={onRefresh}
            />
          </td>
        </tr>
      )}
    </>
  );
}
