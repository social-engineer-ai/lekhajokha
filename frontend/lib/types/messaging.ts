export interface Message {
  id: string;
  client_id: string;
  accountant_id: string;
  channel: "whatsapp" | "email";
  direction: "inbound" | "outbound";
  content: string;
  subject: string | null;
  status: "pending" | "sent" | "delivered" | "read" | "failed";
  message_type: "text" | "notification" | "document";
  attachment_path: string | null;
  attachment_name: string | null;
  external_id: string | null;
  error_message: string | null;
  triggered_by: string;
  created_at: string;
  updated_at: string;
}

export interface MessagingConfig {
  id: string;
  accountant_id: string;
  whatsapp_enabled: boolean;
  email_enabled: boolean;
  twilio_account_sid: string | null;
  twilio_whatsapp_number: string | null;
  smtp_host: string | null;
  smtp_port: number;
  smtp_username: string | null;
  smtp_from_email: string | null;
  smtp_use_tls: boolean;
  created_at: string;
  updated_at: string;
}

export interface MessageTemplate {
  id: string;
  accountant_id: string | null;
  trigger_event: string;
  channel: "whatsapp" | "email";
  subject_template: string | null;
  body_template: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

export interface TestMessageResponse {
  success: boolean;
  message: string | null;
  error: string | null;
}
