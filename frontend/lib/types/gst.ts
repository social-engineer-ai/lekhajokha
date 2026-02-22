export interface GSTSummary {
  period: string;
  total_sales_invoices: number;
  total_purchase_invoices: number;
  total_output_tax: number;
  total_input_tax: number;
  net_tax_liability: number;
}

export interface GSTR1Response {
  period: string;
  gstin: string;
  b2b: B2BEntry[];
  b2cs: B2CSEntry[];
  hsn: HSNEntry[];
  total_invoices: number;
  total_taxable: number;
  total_tax: number;
}

export interface B2BEntry {
  ctin: string;
  inv: B2BInvoice[];
}

export interface B2BInvoice {
  inum: string;
  idt: string;
  val: number;
  pos: string;
  rchrg: string;
  inv_typ: string;
  itms: { num: number; itm_det: TaxDetail }[];
}

export interface TaxDetail {
  rt: number;
  txval: number;
  camt: number;
  samt: number;
  iamt: number;
}

export interface B2CSEntry {
  rt: number;
  pos: string;
  sply_ty: string;
  txval: number;
  camt: number;
  samt: number;
  iamt: number;
}

export interface HSNEntry {
  hsn_sc: string;
  desc: string;
  qty: number;
  txval: number;
  camt: number;
  samt: number;
  iamt: number;
  rt: number;
}

export interface GSTR3BResponse {
  period: string;
  gstin: string;
  outward_supplies: {
    taxable: { txval: number; igst: number; cgst: number; sgst: number; cess: number };
    exempt: { txval: number };
    nil_rated: { txval: number };
    non_gst: { txval: number };
  };
  inter_state_supplies: { txval: number; igst: number };
  eligible_itc: { igst: number; cgst: number; sgst: number; cess: number };
  tax_liability: {
    cgst: number;
    sgst: number;
    igst: number;
    cess: number;
    net_cgst: number;
    net_sgst: number;
    net_igst: number;
  };
  total_output_tax: number;
  total_itc: number;
  net_tax_payable: number;
}
