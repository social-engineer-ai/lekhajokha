"use client";

import { useCallback, useEffect, useState } from "react";
import { apiFetch } from "@/lib/api";
import { InvoiceDetail as InvoiceDetailType } from "@/lib/types/invoice";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { InvoiceEditModal } from "./InvoiceEditModal";

interface InvoiceDetailProps {
  invoiceId: string;
  clientId: string;
  onRefresh: () => void;
}

export function InvoiceDetail({ invoiceId, clientId, onRefresh }: InvoiceDetailProps) {
  const [invoice, setInvoice] = useState<InvoiceDetailType | null>(null);
  const [loading, setLoading] = useState(true);
  const [editing, setEditing] = useState(false);

  const loadInvoice = useCallback(async () => {
    setLoading(true);
    try {
      const data = await apiFetch<InvoiceDetailType>(
        `/clients/${clientId}/invoices/${invoiceId}`
      );
      setInvoice(data);
    } catch {
      // ignore
    } finally {
      setLoading(false);
    }
  }, [clientId, invoiceId]);

  useEffect(() => {
    loadInvoice();
  }, [loadInvoice]);

  if (loading) {
    return (
      <div className="p-4 text-sm text-muted-foreground">Loading details...</div>
    );
  }

  if (!invoice) {
    return (
      <div className="p-4 text-sm text-destructive">Failed to load invoice details</div>
    );
  }

  const confidenceColor =
    invoice.ocr_confidence != null
      ? invoice.ocr_confidence >= 80
        ? "text-green-600"
        : invoice.ocr_confidence >= 50
        ? "text-yellow-600"
        : "text-red-600"
      : "";

  return (
    <div className="bg-muted/20 p-4 space-y-4">
      {/* Header row */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-3">
          <span className="text-xs text-muted-foreground">
            File: {invoice.file_name}
          </span>
          {invoice.ocr_confidence != null && (
            <span className={`text-xs font-medium ${confidenceColor}`}>
              OCR Confidence: {Number(invoice.ocr_confidence).toFixed(0)}%
            </span>
          )}
        </div>
        <Button variant="outline" size="sm" onClick={() => setEditing(true)}>
          Edit Fields
        </Button>
      </div>

      {/* Field grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-3 text-sm">
        <Field label="Invoice #" value={invoice.invoice_number} />
        <Field label="Date" value={invoice.invoice_date} />
        <Field label="Type" value={invoice.invoice_type} />
        <Field label="Place of Supply" value={invoice.place_of_supply} />
        <Field label="Seller" value={invoice.seller_name} />
        <Field label="Seller GSTIN" value={invoice.seller_gstin} />
        <Field label="Buyer" value={invoice.buyer_name} />
        <Field label="Buyer GSTIN" value={invoice.buyer_gstin} />
        <Field label="Taxable Amount" value={formatAmount(invoice.taxable_amount)} />
        <Field label="CGST" value={formatAmount(invoice.cgst_amount)} />
        <Field label="SGST" value={formatAmount(invoice.sgst_amount)} />
        <Field label="IGST" value={formatAmount(invoice.igst_amount)} />
        <Field label="Total Tax" value={formatAmount(invoice.total_tax)} />
        <Field label="Total Amount" value={formatAmount(invoice.total_amount)} highlight />
      </div>

      {/* Processing error */}
      {invoice.processing_error && (
        <p className="text-xs text-destructive">{invoice.processing_error}</p>
      )}

      {/* Line items */}
      {invoice.line_items.length > 0 && (
        <div>
          <h4 className="text-xs font-medium mb-2 text-muted-foreground">
            Line Items ({invoice.line_items.length})
          </h4>
          <div className="border rounded overflow-hidden">
            <table className="w-full text-xs">
              <thead className="bg-muted/50">
                <tr>
                  <th className="text-left px-2 py-1.5 font-medium">#</th>
                  <th className="text-left px-2 py-1.5 font-medium">Description</th>
                  <th className="text-left px-2 py-1.5 font-medium">HSN</th>
                  <th className="text-right px-2 py-1.5 font-medium">Qty</th>
                  <th className="text-left px-2 py-1.5 font-medium">Unit</th>
                  <th className="text-right px-2 py-1.5 font-medium">Rate</th>
                  <th className="text-right px-2 py-1.5 font-medium">Amount</th>
                </tr>
              </thead>
              <tbody>
                {invoice.line_items.map((item) => (
                  <tr key={item.id} className="border-t">
                    <td className="px-2 py-1.5">{item.line_number}</td>
                    <td className="px-2 py-1.5 max-w-[200px] truncate">
                      {item.description}
                    </td>
                    <td className="px-2 py-1.5">{item.hsn_sac_code || "—"}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      {item.quantity != null ? Number(item.quantity) : "—"}
                    </td>
                    <td className="px-2 py-1.5">{item.unit || "—"}</td>
                    <td className="px-2 py-1.5 text-right tabular-nums">
                      {item.unit_price != null
                        ? Number(item.unit_price).toLocaleString("en-IN", {
                            minimumFractionDigits: 2,
                          })
                        : "—"}
                    </td>
                    <td className="px-2 py-1.5 text-right tabular-nums font-medium">
                      {Number(item.amount).toLocaleString("en-IN", {
                        minimumFractionDigits: 2,
                      })}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}

      {/* Edit modal */}
      {editing && (
        <InvoiceEditModal
          invoice={invoice}
          clientId={clientId}
          onClose={() => setEditing(false)}
          onSaved={() => {
            setEditing(false);
            loadInvoice();
            onRefresh();
          }}
        />
      )}
    </div>
  );
}

function Field({
  label,
  value,
  highlight,
}: {
  label: string;
  value: string | null | undefined;
  highlight?: boolean;
}) {
  return (
    <div>
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className={`text-sm ${highlight ? "font-semibold" : ""}`}>
        {value || <span className="text-muted-foreground">—</span>}
      </p>
    </div>
  );
}

function formatAmount(value: number | null | undefined): string | null {
  if (value == null) return null;
  return `₹${Number(value).toLocaleString("en-IN", { minimumFractionDigits: 2 })}`;
}
