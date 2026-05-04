export interface Product {
  id: number;
  name: string;
  description: string | null;
  price: number;
  category: string;
  image_url: string | null;
}

export interface CartItem extends Product {
  quantity: number;
}

export interface User {
  id: number;
  email: string;
  full_name: string | null;
  address_line: string | null;
  city: string | null;
  postal_code: string | null;
  phone: string | null;
  is_admin: boolean;
}

export interface OrderItem {
  id: number;
  product_id: number;
  product_name: string;
  quantity: number;
  price: number;
  extras: string | null;
}

export interface PrintJob {
  id: number;
  status: 'pending' | 'printing' | 'printed' | 'failed';
  attempt_count: number;
  max_attempts: number;
  last_error: string | null;
  locked_by: string | null;
  created_at: string;
  updated_at: string;
  printed_at: string | null;
}

export interface Order {
  id: number;
  status: string;
  total_price: number;
  items: OrderItem[];
  print_jobs: PrintJob[];
}

export interface AuthResponse {
  access_token: string;
  user: User;
}

export interface CheckoutResponse {
  url: string;
}

export interface MetricsResponse {
  total_requests: number;
  total_errors: number;
  in_flight_requests: number;
  average_latency_ms: number;
  status_codes: Record<string, number>;
  business_events: Record<string, number>;
  recent_critical_events: Array<{ event: string; detail: string; timestamp: string }>;
  alerts: string[];
  stats: {
    print_failures: number;
    error_rate_percent: number;
  };
}

export interface OpsStatusResponse {
  status: 'green' | 'yellow' | 'red';
  alerts: string[];
  stats: {
    print_failures: number;
    error_rate_percent: number;
  };
  recent_critical_events: Array<{ event: string; detail: string; timestamp: string }>;
}

export interface AuditEventsResponse {
  events: Array<{ event: string; detail: string; timestamp: string }>;
  count: number;
}
