export interface User {
  id: number;
  username: string;
}

export interface Client {
  id: number;
  name: string;
  slug: string;
  contact_name?: string;
  contact_email?: string;
  contact_phone?: string;
  address?: string;
  city?: string;
  business_type?: string;
  notes?: string;
  status: 'active' | 'inactive' | 'suspended';
  dashboard_url?: string;
  onboarding_date?: string;
  offboarding_date?: string;
  created_at: string;
  updated_at: string;
}

export interface ServiceCatalog {
  id: number;
  name: string;
  description?: string;
  default_monthly_price?: number;
  default_setup_price?: number;
  category?: string;
  is_active: boolean;
}

export interface ClientService {
  id: number;
  client_id: number;
  service_id: number;
  monthly_price?: number;
  setup_price?: number;
  status: 'active' | 'paused' | 'cancelled';
  started_at?: string;
  ended_at?: string;
  notes?: string;
  service?: ServiceCatalog; // Joined relation
}

export interface Invoice {
  id: number;
  client_id: number;
  invoice_number?: string;
  invoice_date?: string;
  due_date?: string;
  amount?: number;
  tax_amount?: number;
  total_amount?: number;
  currency: string;
  status: 'pending' | 'paid' | 'overdue' | 'cancelled';
  concept?: string;
  file_path?: string;
  file_name?: string;
  ai_extracted_data?: Record<string, any>;
  ai_confidence?: number;
  payment_date?: string;
  notes?: string;
  created_at: string;
  updated_at: string;
  client?: Client; // Joined relation
}

export interface DashboardStats {
  active_clients: number;
  mrr: number;
  pending_invoices_count: number;
  ytd_revenue: number;
}
