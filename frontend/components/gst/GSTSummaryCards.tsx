"use client";

import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import type { GSTSummary } from "@/lib/types/gst";

interface GSTSummaryCardsProps {
  summary: GSTSummary;
}

function fmt(n: number): string {
  return new Intl.NumberFormat("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 }).format(n);
}

export function GSTSummaryCards({ summary }: GSTSummaryCardsProps) {
  return (
    <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Output Tax (Sales)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{fmt(summary.total_output_tax)}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.total_sales_invoices} invoice{summary.total_sales_invoices !== 1 ? "s" : ""}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Input Tax Credit (Purchases)
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className="text-2xl font-bold">{fmt(summary.total_input_tax)}</p>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.total_purchase_invoices} invoice{summary.total_purchase_invoices !== 1 ? "s" : ""}
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Net Tax Liability
          </CardTitle>
        </CardHeader>
        <CardContent>
          <p className={`text-2xl font-bold ${summary.net_tax_liability > 0 ? "text-red-600" : "text-green-600"}`}>
            {fmt(summary.net_tax_liability)}
          </p>
          <p className="text-xs text-muted-foreground mt-1">
            Output - Input
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
