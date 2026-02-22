"use client";

import { useState } from "react";
import { apiFetch } from "@/lib/api";
import { InvoiceDetail } from "@/lib/types/invoice";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";

interface InvoiceEditModalProps {
  invoice: InvoiceDetail;
  clientId: string;
  onClose: () => void;
  onSaved: () => void;
}

export function InvoiceEditModal({
  invoice,
  clientId,
  onClose,
  onSaved,
}: InvoiceEditModalProps) {
  const [form, setForm] = useState({
    invoice_number: invoice.invoice_number || "",
    invoice_date: invoice.invoice_date || "",
    invoice_type: invoice.invoice_type || "purchase",
    seller_name: invoice.seller_name || "",
    seller_gstin: invoice.seller_gstin || "",
    buyer_name: invoice.buyer_name || "",
    buyer_gstin: invoice.buyer_gstin || "",
    place_of_supply: invoice.place_of_supply || "",
    taxable_amount: invoice.taxable_amount?.toString() || "",
    cgst_amount: invoice.cgst_amount?.toString() || "",
    sgst_amount: invoice.sgst_amount?.toString() || "",
    igst_amount: invoice.igst_amount?.toString() || "",
    total_tax: invoice.total_tax?.toString() || "",
    total_amount: invoice.total_amount?.toString() || "",
  });
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const update = (field: string, value: string) => {
    setForm((prev) => ({ ...prev, [field]: value }));
  };

  const handleSave = async () => {
    setSaving(true);
    setError(null);

    try {
      const body: Record<string, any> = {};
      // Only send changed fields
      if (form.invoice_number) body.invoice_number = form.invoice_number;
      if (form.invoice_date) body.invoice_date = form.invoice_date;
      if (form.invoice_type) body.invoice_type = form.invoice_type;
      if (form.seller_name) body.seller_name = form.seller_name;
      if (form.seller_gstin) body.seller_gstin = form.seller_gstin;
      if (form.buyer_name) body.buyer_name = form.buyer_name;
      if (form.buyer_gstin) body.buyer_gstin = form.buyer_gstin;
      if (form.place_of_supply) body.place_of_supply = form.place_of_supply;
      if (form.taxable_amount) body.taxable_amount = parseFloat(form.taxable_amount);
      if (form.cgst_amount) body.cgst_amount = parseFloat(form.cgst_amount);
      if (form.sgst_amount) body.sgst_amount = parseFloat(form.sgst_amount);
      if (form.igst_amount) body.igst_amount = parseFloat(form.igst_amount);
      if (form.total_tax) body.total_tax = parseFloat(form.total_tax);
      if (form.total_amount) body.total_amount = parseFloat(form.total_amount);

      await apiFetch(`/clients/${clientId}/invoices/${invoice.id}`, {
        method: "PUT",
        body: JSON.stringify(body),
      });
      onSaved();
    } catch (err: any) {
      setError(err.message || "Save failed");
    } finally {
      setSaving(false);
    }
  };

  return (
    <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50">
      <div className="bg-background rounded-lg shadow-lg p-6 w-full max-w-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-semibold">Edit Invoice Fields</h3>
          <button onClick={onClose} className="text-muted-foreground hover:text-foreground">
            ✕
          </button>
        </div>

        <div className="grid grid-cols-2 gap-3">
          <EditField label="Invoice Number" value={form.invoice_number} onChange={(v) => update("invoice_number", v)} />
          <EditField label="Invoice Date" value={form.invoice_date} onChange={(v) => update("invoice_date", v)} type="date" />

          <div>
            <Label className="text-xs">Invoice Type</Label>
            <select
              value={form.invoice_type}
              onChange={(e) => update("invoice_type", e.target.value)}
              className="w-full h-8 text-sm border rounded px-2 bg-background"
            >
              <option value="sales">Sales</option>
              <option value="purchase">Purchase</option>
            </select>
          </div>
          <EditField label="Place of Supply" value={form.place_of_supply} onChange={(v) => update("place_of_supply", v)} />

          <EditField label="Seller Name" value={form.seller_name} onChange={(v) => update("seller_name", v)} />
          <EditField label="Seller GSTIN" value={form.seller_gstin} onChange={(v) => update("seller_gstin", v)} />
          <EditField label="Buyer Name" value={form.buyer_name} onChange={(v) => update("buyer_name", v)} />
          <EditField label="Buyer GSTIN" value={form.buyer_gstin} onChange={(v) => update("buyer_gstin", v)} />

          <EditField label="Taxable Amount" value={form.taxable_amount} onChange={(v) => update("taxable_amount", v)} type="number" />
          <EditField label="CGST" value={form.cgst_amount} onChange={(v) => update("cgst_amount", v)} type="number" />
          <EditField label="SGST" value={form.sgst_amount} onChange={(v) => update("sgst_amount", v)} type="number" />
          <EditField label="IGST" value={form.igst_amount} onChange={(v) => update("igst_amount", v)} type="number" />
          <EditField label="Total Tax" value={form.total_tax} onChange={(v) => update("total_tax", v)} type="number" />
          <EditField label="Total Amount" value={form.total_amount} onChange={(v) => update("total_amount", v)} type="number" />
        </div>

        {error && <p className="text-sm text-destructive mt-3">{error}</p>}

        <div className="flex justify-end gap-2 mt-4">
          <Button variant="outline" size="sm" onClick={onClose}>
            Cancel
          </Button>
          <Button size="sm" onClick={handleSave} disabled={saving}>
            {saving ? "Saving..." : "Save Changes"}
          </Button>
        </div>
      </div>
    </div>
  );
}

function EditField({
  label,
  value,
  onChange,
  type = "text",
}: {
  label: string;
  value: string;
  onChange: (v: string) => void;
  type?: string;
}) {
  return (
    <div>
      <Label className="text-xs">{label}</Label>
      <Input
        type={type}
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="h-8 text-sm"
        step={type === "number" ? "0.01" : undefined}
      />
    </div>
  );
}
