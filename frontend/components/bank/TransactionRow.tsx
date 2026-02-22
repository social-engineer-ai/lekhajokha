"use client";

import { useState } from "react";
import { Transaction } from "@/lib/types/bank";
import { Badge } from "@/components/ui/badge";
import { formatINR, formatDate } from "@/lib/format";

interface TransactionRowProps {
  transaction: Transaction;
}

export function TransactionRow({ transaction: txn }: TransactionRowProps) {
  const [expanded, setExpanded] = useState(false);

  return (
    <>
      <tr
        onClick={() => setExpanded(!expanded)}
        className="border-b last:border-0 cursor-pointer hover:bg-muted/50 transition-colors"
      >
        <td className="p-2 text-xs tabular-nums">{formatDate(txn.transaction_date)}</td>
        <td className="p-2 text-xs max-w-[250px]">
          <span className="block truncate">
            {txn.parsed_counterparty || txn.raw_description}
          </span>
        </td>
        <td className="p-2 text-xs">
          {txn.transaction_mode && (
            <Badge variant="secondary" className="text-[10px] px-1 py-0">
              {txn.transaction_mode}
            </Badge>
          )}
        </td>
        <td
          className={`p-2 text-xs text-right tabular-nums font-medium ${
            txn.transaction_type === "credit" ? "text-green-600" : "text-red-600"
          }`}
        >
          {txn.transaction_type === "credit" ? "+" : "-"}
          {formatINR(txn.amount)}
        </td>
        <td className="p-2 text-xs text-right tabular-nums text-muted-foreground">
          {txn.running_balance != null ? formatINR(txn.running_balance) : "-"}
        </td>
        <td className="p-2">
          <Badge
            variant={txn.recon_status === "matched" ? "default" : "secondary"}
            className="text-[10px] px-1 py-0"
          >
            {txn.recon_status}
          </Badge>
        </td>
      </tr>
      {expanded && (
        <tr className="bg-muted/30">
          <td colSpan={6} className="p-3">
            <div className="grid grid-cols-2 gap-x-8 gap-y-1 text-xs">
              <div>
                <span className="text-muted-foreground">Raw Description:</span>
                <p className="break-all">{txn.raw_description}</p>
              </div>
              <div>
                <span className="text-muted-foreground">Value Date:</span>
                <p>{txn.value_date ? formatDate(txn.value_date) : "-"}</p>
              </div>
              {txn.parsed_counterparty && (
                <div>
                  <span className="text-muted-foreground">Counterparty:</span>
                  <p>{txn.parsed_counterparty}</p>
                </div>
              )}
              {txn.parsed_bank_ifsc && (
                <div>
                  <span className="text-muted-foreground">Bank IFSC:</span>
                  <p>{txn.parsed_bank_ifsc}</p>
                </div>
              )}
              {txn.parsed_upi_id && (
                <div>
                  <span className="text-muted-foreground">UPI ID:</span>
                  <p>{txn.parsed_upi_id}</p>
                </div>
              )}
              {txn.reference_number && (
                <div>
                  <span className="text-muted-foreground">Reference:</span>
                  <p>{txn.reference_number}</p>
                </div>
              )}
              {txn.category && (
                <div>
                  <span className="text-muted-foreground">Category:</span>
                  <p>{txn.category}{txn.sub_category ? ` / ${txn.sub_category}` : ""}</p>
                </div>
              )}
            </div>
          </td>
        </tr>
      )}
    </>
  );
}
