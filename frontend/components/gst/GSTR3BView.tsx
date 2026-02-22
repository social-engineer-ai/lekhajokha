"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GSTR3BResponse } from "@/lib/types/gst";

interface GSTR3BViewProps {
  data: GSTR3BResponse;
}

function fmt(n: number): string {
  return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

function TaxRow({ label, igst, cgst, sgst, cess }: { label: string; igst: number; cgst: number; sgst: number; cess: number }) {
  return (
    <tr className="border-b last:border-0">
      <td className="py-2 pr-4">{label}</td>
      <td className="py-2 pr-4 text-right">{fmt(igst)}</td>
      <td className="py-2 pr-4 text-right">{fmt(cgst)}</td>
      <td className="py-2 pr-4 text-right">{fmt(sgst)}</td>
      <td className="py-2 text-right">{fmt(cess)}</td>
    </tr>
  );
}

export function GSTR3BView({ data }: GSTR3BViewProps) {
  const os = data.outward_supplies;
  const itc = data.eligible_itc;
  const tl = data.tax_liability;

  return (
    <div className="space-y-6">
      {/* Section 3.1: Outward Supplies */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">3.1 - Outward Supplies</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-4">Nature</th>
                <th className="pb-2 pr-4 text-right">Taxable Value</th>
                <th className="pb-2 pr-4 text-right">IGST</th>
                <th className="pb-2 pr-4 text-right">CGST</th>
                <th className="pb-2 text-right">SGST</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <td className="py-2 pr-4">Taxable outward supplies</td>
                <td className="py-2 pr-4 text-right">{fmt(os.taxable.txval)}</td>
                <td className="py-2 pr-4 text-right">{fmt(os.taxable.igst)}</td>
                <td className="py-2 pr-4 text-right">{fmt(os.taxable.cgst)}</td>
                <td className="py-2 text-right">{fmt(os.taxable.sgst)}</td>
              </tr>
              <tr className="border-b">
                <td className="py-2 pr-4">Exempt supplies</td>
                <td className="py-2 pr-4 text-right">{fmt(os.exempt.txval)}</td>
                <td className="py-2 pr-4 text-right">-</td>
                <td className="py-2 pr-4 text-right">-</td>
                <td className="py-2 text-right">-</td>
              </tr>
              <tr className="border-b last:border-0">
                <td className="py-2 pr-4">Nil-rated supplies</td>
                <td className="py-2 pr-4 text-right">{fmt(os.nil_rated.txval)}</td>
                <td className="py-2 pr-4 text-right">-</td>
                <td className="py-2 pr-4 text-right">-</td>
                <td className="py-2 text-right">-</td>
              </tr>
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Section 3.2: Inter-state supplies */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">3.2 - Inter-State Supplies (Unregistered)</CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-2 gap-4 text-sm">
            <div>
              <p className="text-muted-foreground">Taxable Value</p>
              <p className="font-medium">{fmt(data.inter_state_supplies.txval)}</p>
            </div>
            <div>
              <p className="text-muted-foreground">IGST</p>
              <p className="font-medium">{fmt(data.inter_state_supplies.igst)}</p>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Section 4: Eligible ITC */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">4 - Eligible Input Tax Credit</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-4">Details</th>
                <th className="pb-2 pr-4 text-right">IGST</th>
                <th className="pb-2 pr-4 text-right">CGST</th>
                <th className="pb-2 pr-4 text-right">SGST</th>
                <th className="pb-2 text-right">Cess</th>
              </tr>
            </thead>
            <tbody>
              <TaxRow label="ITC from purchases" igst={itc.igst} cgst={itc.cgst} sgst={itc.sgst} cess={itc.cess} />
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Section 6.1: Tax Liability */}
      <Card>
        <CardHeader>
          <CardTitle className="text-base">6.1 - Tax Liability</CardTitle>
        </CardHeader>
        <CardContent>
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-left text-muted-foreground">
                <th className="pb-2 pr-4">Description</th>
                <th className="pb-2 pr-4 text-right">IGST</th>
                <th className="pb-2 pr-4 text-right">CGST</th>
                <th className="pb-2 text-right">SGST</th>
              </tr>
            </thead>
            <tbody>
              <tr className="border-b">
                <td className="py-2 pr-4">Output Tax</td>
                <td className="py-2 pr-4 text-right">{fmt(tl.igst)}</td>
                <td className="py-2 pr-4 text-right">{fmt(tl.cgst)}</td>
                <td className="py-2 text-right">{fmt(tl.sgst)}</td>
              </tr>
              <tr className="border-b">
                <td className="py-2 pr-4">Less: ITC</td>
                <td className="py-2 pr-4 text-right">{fmt(itc.igst)}</td>
                <td className="py-2 pr-4 text-right">{fmt(itc.cgst)}</td>
                <td className="py-2 text-right">{fmt(itc.sgst)}</td>
              </tr>
              <tr className="font-semibold">
                <td className="py-2 pr-4">Net Payable</td>
                <td className="py-2 pr-4 text-right">{fmt(tl.net_igst)}</td>
                <td className="py-2 pr-4 text-right">{fmt(tl.net_cgst)}</td>
                <td className="py-2 text-right">{fmt(tl.net_sgst)}</td>
              </tr>
            </tbody>
          </table>
        </CardContent>
      </Card>

      {/* Net payable summary */}
      <div className="bg-muted/50 p-4 rounded-lg text-center">
        <p className="text-sm text-muted-foreground">Total Net Tax Payable</p>
        <p className={`text-3xl font-bold mt-1 ${data.net_tax_payable > 0 ? "text-red-600" : "text-green-600"}`}>
          {fmt(data.net_tax_payable)}
        </p>
      </div>
    </div>
  );
}
