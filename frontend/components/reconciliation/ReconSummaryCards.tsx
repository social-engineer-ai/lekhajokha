"use client";

import { ReconciliationSummary } from "@/lib/types/reconciliation";
import { formatINR } from "@/lib/format";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface ReconSummaryCardsProps {
  summary: ReconciliationSummary;
}

export function ReconSummaryCards({ summary }: ReconSummaryCardsProps) {
  return (
    <div className="grid grid-cols-3 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Invoices
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{summary.matched_invoices}/{summary.total_invoices}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.unmatched_invoices} unmatched
          </p>
          <div className="mt-2 text-sm">
            <div className="flex justify-between">
              <span className="text-muted-foreground">Matched</span>
              <span className="font-medium">{formatINR(summary.matched_invoice_amount)}</span>
            </div>
            <div className="flex justify-between">
              <span className="text-muted-foreground">Unmatched</span>
              <span className="font-medium">{formatINR(summary.unmatched_invoice_amount)}</span>
            </div>
          </div>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Transactions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{summary.matched_transactions}/{summary.total_transactions}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.unmatched_transactions} unmatched
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total Invoice Value
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{formatINR(summary.total_invoice_amount)}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.total_invoices > 0
              ? `${Math.round((summary.matched_invoices / summary.total_invoices) * 100)}% matched`
              : "No invoices"}
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
