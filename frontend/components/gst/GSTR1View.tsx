"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GSTR1Response } from "@/lib/types/gst";

interface GSTR1ViewProps {
  data: GSTR1Response;
}

function fmt(n: number): string {
  return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

export function GSTR1View({ data }: GSTR1ViewProps) {
  return (
    <div className="space-y-6">
      {/* B2B Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">B2B Invoices (Buyer has GSTIN)</CardTitle>
        </CardHeader>
        <CardContent>
          {data.b2b.length === 0 ? (
            <p className="text-sm text-muted-foreground">No B2B invoices for this period</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">Buyer GSTIN</th>
                    <th className="pb-2 pr-4">Invoice #</th>
                    <th className="pb-2 pr-4">Date</th>
                    <th className="pb-2 pr-4 text-right">Value</th>
                    <th className="pb-2 pr-4 text-right">Rate</th>
                    <th className="pb-2 pr-4 text-right">Taxable</th>
                    <th className="pb-2 pr-4 text-right">CGST</th>
                    <th className="pb-2 pr-4 text-right">SGST</th>
                    <th className="pb-2 text-right">IGST</th>
                  </tr>
                </thead>
                <tbody>
                  {data.b2b.flatMap((buyer) =>
                    buyer.inv.map((inv, idx) => (
                      <tr key={`${buyer.ctin}-${idx}`} className="border-b last:border-0">
                        <td className="py-2 pr-4 font-mono text-xs">{buyer.ctin}</td>
                        <td className="py-2 pr-4">{inv.inum}</td>
                        <td className="py-2 pr-4">{inv.idt}</td>
                        <td className="py-2 pr-4 text-right">{fmt(inv.val)}</td>
                        <td className="py-2 pr-4 text-right">
                          {inv.itms.map((i) => `${i.itm_det.rt}%`).join(", ")}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          {fmt(inv.itms.reduce((s, i) => s + i.itm_det.txval, 0))}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          {fmt(inv.itms.reduce((s, i) => s + i.itm_det.camt, 0))}
                        </td>
                        <td className="py-2 pr-4 text-right">
                          {fmt(inv.itms.reduce((s, i) => s + i.itm_det.samt, 0))}
                        </td>
                        <td className="py-2 text-right">
                          {fmt(inv.itms.reduce((s, i) => s + i.itm_det.iamt, 0))}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* B2CS Section */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">B2C Small (No Buyer GSTIN)</CardTitle>
        </CardHeader>
        <CardContent>
          {data.b2cs.length === 0 ? (
            <p className="text-sm text-muted-foreground">No B2C invoices for this period</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">Type</th>
                    <th className="pb-2 pr-4">Place of Supply</th>
                    <th className="pb-2 pr-4 text-right">Rate %</th>
                    <th className="pb-2 pr-4 text-right">Taxable Value</th>
                    <th className="pb-2 pr-4 text-right">CGST</th>
                    <th className="pb-2 pr-4 text-right">SGST</th>
                    <th className="pb-2 text-right">IGST</th>
                  </tr>
                </thead>
                <tbody>
                  {data.b2cs.map((entry, idx) => (
                    <tr key={idx} className="border-b last:border-0">
                      <td className="py-2 pr-4">{entry.sply_ty}</td>
                      <td className="py-2 pr-4">{entry.pos}</td>
                      <td className="py-2 pr-4 text-right">{entry.rt}%</td>
                      <td className="py-2 pr-4 text-right">{fmt(entry.txval)}</td>
                      <td className="py-2 pr-4 text-right">{fmt(entry.camt)}</td>
                      <td className="py-2 pr-4 text-right">{fmt(entry.samt)}</td>
                      <td className="py-2 text-right">{fmt(entry.iamt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* HSN Summary */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">HSN Summary</CardTitle>
        </CardHeader>
        <CardContent>
          {data.hsn.length === 0 ? (
            <p className="text-sm text-muted-foreground">No HSN data available</p>
          ) : (
            <div className="overflow-x-auto">
              <table className="w-full text-sm">
                <thead>
                  <tr className="border-b text-left text-muted-foreground">
                    <th className="pb-2 pr-4">HSN Code</th>
                    <th className="pb-2 pr-4">Description</th>
                    <th className="pb-2 pr-4 text-right">Qty</th>
                    <th className="pb-2 pr-4 text-right">Taxable</th>
                    <th className="pb-2 pr-4 text-right">CGST</th>
                    <th className="pb-2 pr-4 text-right">SGST</th>
                    <th className="pb-2 text-right">IGST</th>
                  </tr>
                </thead>
                <tbody>
                  {data.hsn.map((entry, idx) => (
                    <tr key={idx} className="border-b last:border-0">
                      <td className="py-2 pr-4 font-mono">{entry.hsn_sc}</td>
                      <td className="py-2 pr-4">{entry.desc}</td>
                      <td className="py-2 pr-4 text-right">{entry.qty}</td>
                      <td className="py-2 pr-4 text-right">{fmt(entry.txval)}</td>
                      <td className="py-2 pr-4 text-right">{fmt(entry.camt)}</td>
                      <td className="py-2 pr-4 text-right">{fmt(entry.samt)}</td>
                      <td className="py-2 text-right">{fmt(entry.iamt)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Totals */}
      <div className="flex justify-between text-sm bg-muted/50 p-4 rounded-lg">
        <span>
          Total Invoices: <strong>{data.total_invoices}</strong>
        </span>
        <span>
          Total Taxable: <strong>{fmt(data.total_taxable)}</strong>
        </span>
        <span>
          Total Tax: <strong>{fmt(data.total_tax)}</strong>
        </span>
      </div>
    </div>
  );
}
