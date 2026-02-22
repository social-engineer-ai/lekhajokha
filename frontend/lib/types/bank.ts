export interface BankStatement {
  id: string;
  bank_account_id: string;
  client_id: string;
  file_name: string;
  file_size_bytes: number;
  is_password_protected: boolean;
  period_from: string | null;
  period_to: string | null;
  processing_status: "pending" | "processing" | "completed" | "failed";
  processing_error: string | null;
  transactions_count: number;
  created_at: string;
}

export interface BankStatementDetail extends BankStatement {
  transactions: Transaction[];
}

export interface Transaction {
  id: string;
  bank_statement_id: string;
  bank_account_id: string;
  client_id: string;
  transaction_date: string;
  value_date: string | null;
  reference_number: string | null;
  cheque_ref_no: string | null;
  raw_description: string;
  parsed_counterparty: string | null;
  parsed_bank_ifsc: string | null;
  parsed_upi_id: string | null;
  transaction_mode: string | null;
  amount: number;
  transaction_type: "debit" | "credit";
  running_balance: number | null;
  category: string | null;
  sub_category: string | null;
  recon_status: "unmatched" | "matched" | "manual";
  tally_sync_status: "pending" | "synced" | "error";
  created_at: string;
  updated_at: string;
}

export interface Job {
  id: string;
  client_id: string;
  job_type: string;
  status: "pending" | "processing" | "completed" | "failed";
  result_summary: string | null;
  error_message: string | null;
  created_at: string;
  completed_at: string | null;
}

export interface BankAccount {
  id: string;
  client_id: string;
  bank_name: string;
  account_number: string;
  ifsc_code: string | null;
  branch_name: string | null;
  account_type: string;
  is_primary: boolean;
  is_active: boolean;
  created_at: string;
}
