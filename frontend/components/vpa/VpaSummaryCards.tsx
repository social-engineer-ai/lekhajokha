"use client";

import { VpaResolutionSummary } from "@/lib/types/vpa";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";

interface VpaSummaryCardsProps {
  summary: VpaResolutionSummary;
}

export function VpaSummaryCards({ summary }: VpaSummaryCardsProps) {
  return (
    <div className="grid grid-cols-4 gap-4">
      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Total VPAs
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{summary.total_vpa_entries}</div>
          <p className="text-xs text-muted-foreground mt-1">
            in directory
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Verified
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-green-600">{summary.verified_count}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.unverified_count} unverified
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            UPI Transactions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold">{summary.total_upi_transactions}</div>
          <p className="text-xs text-muted-foreground mt-1">
            {summary.tagged_transactions} tagged
          </p>
        </CardContent>
      </Card>

      <Card>
        <CardHeader className="pb-2">
          <CardTitle className="text-sm font-medium text-muted-foreground">
            Untagged UPI Txns
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="text-2xl font-bold text-orange-600">{summary.untagged_transactions}</div>
          <p className="text-xs text-muted-foreground mt-1">
            need resolution
          </p>
        </CardContent>
      </Card>
    </div>
  );
}
