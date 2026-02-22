export interface InvoiceSummary {
  id: string;
  invoice_number: string | null;
  invoice_date: string | null;
  invoice_type: "sales" | "purchase";
  seller_name: string | null;
  buyer_name: string | null;
  total_amount: number | null;
}

export interface TransactionSummary {
  id: string;
  transaction_date: string;
  raw_description: string;
  amount: number;
  transaction_type: "debit" | "credit";
  parsed_counterparty: string | null;
  transaction_mode: string | null;
}

export interface ReconciliationMatch {
  id: string;
  client_id: string;
  invoice_id: string;
  transaction_id: string;
  confidence_score: number;
  matched_amount: number;
  is_confirmed: boolean;
  match_method: "auto" | "manual";
  notes: string | null;
  created_at: string;
  updated_at: string;
  invoice_summary: InvoiceSummary | null;
  transaction_summary: TransactionSummary | null;
}

export interface ReconciliationSummary {
  total_invoices: number;
  matched_invoices: number;
  unmatched_invoices: number;
  total_transactions: number;
  matched_transactions: number;
  unmatched_transactions: number;
  total_invoice_amount: number;
  matched_invoice_amount: number;
  unmatched_invoice_amount: number;
}
