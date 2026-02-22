export interface TallyConfig {
  id: string;
  accountant_id: string;
  tally_host: string;
  tally_port: number;
  company_name: string | null;
  is_connected: boolean;
  last_sync_at: string | null;
}

export interface TallyConnectionTest {
  connected: boolean;
  company_name: string | null;
  error: string | null;
}

export type TallySyncScope = "invoices_only" | "invoices_and_reconciled" | "all";
