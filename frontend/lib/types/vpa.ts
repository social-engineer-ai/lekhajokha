export interface VpaEntry {
  id: string;
  client_id: string;
  vpa: string;
  resolved_name: string | null;
  gstin: string | null;
  pan: string | null;
  source: "transaction_aggregate" | "reconciliation" | "whatsapp_profile" | "manual" | "cashfree";
  confidence: number;
  is_verified: boolean;
  transaction_count: number;
  last_seen_at: string | null;
  notes: string | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface VpaResolutionSummary {
  total_vpa_entries: number;
  verified_count: number;
  unverified_count: number;
  total_upi_transactions: number;
  tagged_transactions: number;
  untagged_transactions: number;
  sources_breakdown: Record<string, number>;
}

export interface CashfreeVerifyResponse {
  vpa: string;
  registered_name: string | null;
  is_valid: boolean;
  source: string;
}
