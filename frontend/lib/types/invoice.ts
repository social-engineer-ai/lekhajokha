export interface InvoiceLineItem {
  id: string;
  invoice_id: string;
  line_number: number;
  description: string;
  hsn_sac_code: string | null;
  quantity: number | null;
  unit: string | null;
  unit_price: number | null;
  amount: number;
  gst_rate: number | null;
  cgst_amount: number | null;
  sgst_amount: number | null;
  igst_amount: number | null;
  created_at: string;
}

export interface Invoice {
  id: string;
  client_id: string;
  invoice_type: "sales" | "purchase";
  file_name: string;
  file_size_bytes: number;
  invoice_number: string | null;
  invoice_date: string | null;
  seller_name: string | null;
  seller_gstin: string | null;
  buyer_name: string | null;
  buyer_gstin: string | null;
  place_of_supply: string | null;
  taxable_amount: number | null;
  cgst_amount: number | null;
  sgst_amount: number | null;
  igst_amount: number | null;
  total_tax: number | null;
  total_amount: number | null;
  processing_status: "pending" | "processing" | "completed" | "failed";
  processing_error: string | null;
  ocr_confidence: number | null;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface InvoiceDetail extends Invoice {
  line_items: InvoiceLineItem[];
}
