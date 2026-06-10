import axios, { AxiosError } from 'axios';
import type {
  AuthResponse,
  AuditEventsResponse,
  CheckoutResponse,
  MetricsResponse,
  OpsStatusResponse,
  Order,
  OpeningHour,
  Product,
  RestaurantStatus,
  RestaurantSettings,
  RestaurantSettingsAdmin,
  SalesReportResponse,
  User,
} from '../types';

function resolveApiBaseUrl() {
  const configured = (import.meta.env.VITE_API_URL || '').trim().replace(/\/$/, '');
  const { hostname, port, protocol } = window.location;

  if (configured) {
    const configuredUrl = new URL(configured, window.location.origin);
    const isLocalBackend =
      ['localhost', '127.0.0.1'].includes(configuredUrl.hostname) && configuredUrl.port === '8000';
    if (isLocalBackend && port === '8000') {
      return '';
    }
    return configured;
  }

  if (port === '5173' || port === '4173') {
    return `${protocol}//${hostname === '0.0.0.0' ? '127.0.0.1' : hostname}:8000`;
  }

  return '';
}

export const API_BASE_URL = resolveApiBaseUrl();

export function buildApiUrl(path: string) {
  if (!path) {
    return API_BASE_URL || '';
  }
  if (/^https?:\/\//.test(path)) {
    return path;
  }
  if (!API_BASE_URL) {
    return path;
  }
  return `${API_BASE_URL}${path.startsWith('/') ? path : `/${path}`}`;
}

const api = axios.create({
  baseURL: API_BASE_URL,
  headers: {
    'Content-Type': 'application/json',
  },
});

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('pizzeria_auth_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401 && localStorage.getItem('pizzeria_auth_token')) {
      localStorage.removeItem('pizzeria_auth_token');
      window.location.href = '/';
    }
    return Promise.reject(error);
  }
);

export const authService = {
  async login(email: string, password: string): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/auth/login', { email, password });
    localStorage.setItem('pizzeria_auth_token', data.access_token);
    return data;
  },

  async register(payload: {
    email: string;
    password: string;
    full_name?: string;
    address_line?: string;
    city?: string;
    postal_code?: string;
    phone?: string;
  }): Promise<AuthResponse> {
    const { data } = await api.post<AuthResponse>('/auth/register', payload);
    localStorage.setItem('pizzeria_auth_token', data.access_token);
    return data;
  },

  async me(): Promise<User> {
    const { data } = await api.get<User>('/auth/me');
    return data;
  },

  async updateProfile(payload: Partial<User>): Promise<User> {
    const { data } = await api.patch<User>('/auth/me/profile', payload);
    return data;
  },

  logout(): void {
    localStorage.removeItem('pizzeria_auth_token');
  },
};

export const productService = {
  async getAll(): Promise<Product[]> {
    const { data } = await api.get<Product[]>('/products');
    return data;
  },

  async create(payload: FormData): Promise<Product> {
    const { data } = await api.post<Product>('/admin/products', payload, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async update(productId: number, payload: FormData): Promise<Product> {
    const { data } = await api.put<Product>(`/admin/products/${productId}`, payload, {
      headers: { 'Content-Type': 'multipart/form-data' },
    });
    return data;
  },

  async remove(productId: number): Promise<{ message: string }> {
    const { data } = await api.delete<{ message: string }>(`/admin/products/${productId}`);
    return data;
  },

  async getAdminAll(includeInactive = true): Promise<Product[]> {
    const { data } = await api.get<Product[]>(
      `/admin/products?include_inactive=${includeInactive ? 'true' : 'false'}`
    );
    return data;
  },

  async archive(productId: number, archived: boolean): Promise<Product> {
    const payload = new FormData();
    payload.append('archived', String(archived));
    const { data } = await api.patch<Product>(`/admin/products/${productId}/archive`, payload);
    return data;
  },
};

export const orderService = {
  async create(payload: {
    items: { product_id: number; quantity: number; extras?: string }[];
    customer_name: string;
    customer_email: string;
    customer_phone: string;
    fulfillment_method: 'delivery' | 'collection';
    delivery_address: string;
    delivery_city: string;
    delivery_postal_code: string;
    delivery_notes?: string;
    payment_method: 'card' | 'cash';
  }): Promise<{ order_id: number; total: number; status: string }> {
    const { data } = await api.post('/orders', payload);
    return data;
  },

  async createCashCheckout(payload: {
    items: { product_id: number; quantity: number; extras?: string }[];
    customer_name: string;
    customer_email: string;
    customer_phone: string;
    fulfillment_method: 'delivery' | 'collection';
    delivery_address: string;
    delivery_city: string;
    delivery_postal_code: string;
    delivery_notes?: string;
    payment_method: 'card' | 'cash';
  }): Promise<{ order_id: number; total: number; status: string; payment_method: string }> {
    const { data } = await api.post('/orders/cash-checkout', payload);
    return data;
  },

  async createCheckoutSession(orderId: number): Promise<CheckoutResponse> {
    const { data } = await api.post<CheckoutResponse>('/create-checkout-session', {
      order_id: orderId,
    });
    return data;
  },

  async getAdminOrders(limit = 80): Promise<Order[]> {
    const { data } = await api.get<Order[]>(`/admin/orders?limit=${limit}`);
    return data;
  },

  async getAdminOrdersFiltered(payload: {
    status?: string;
    date_from?: string;
    date_to?: string;
    search?: string;
    payment_method?: string;
    limit?: number;
    offset?: number;
  }): Promise<Order[]> {
    const params = new URLSearchParams();
    if (payload.status) params.set('status', payload.status);
    if (payload.date_from) params.set('date_from', payload.date_from);
    if (payload.date_to) params.set('date_to', payload.date_to);
    if (payload.search) params.set('search', payload.search);
    if (payload.payment_method) params.set('payment_method', payload.payment_method);
    params.set('limit', String(payload.limit ?? 40));
    params.set('offset', String(payload.offset ?? 0));
    const { data } = await api.get<Order[]>(`/admin/orders?${params.toString()}`);
    return data;
  },

  async updateStatus(orderId: number, status: string): Promise<Order> {
    const { data } = await api.patch<Order>(`/admin/orders/${orderId}/status`, { status });
    return data;
  },

  async reprint(orderId: number): Promise<{ order_id: number; print_job: PrintJob }> {
    const { data } = await api.post<{ order_id: number; print_job: PrintJob }>(
      `/admin/orders/${orderId}/reprint`
    );
    return data;
  },

  async getTracking(
    orderId: number,
    query: { email?: string; phone?: string }
  ): Promise<Order> {
    const params = new URLSearchParams();
    if (query.email) {
      params.set('email', query.email);
    }
    if (query.phone) {
      params.set('phone', query.phone);
    }
    const { data } = await api.get<Order>(`/orders/${orderId}/tracking?${params.toString()}`);
    return data;
  },
};

export const observabilityService = {
  async getMetrics(): Promise<MetricsResponse> {
    const { data } = await api.get<MetricsResponse>('/metrics');
    return data;
  },

  async getOpsStatus(): Promise<OpsStatusResponse> {
    const { data } = await api.get<OpsStatusResponse>('/ops/status');
    return data;
  },

  async getAuditEvents(event?: string, limit = 20): Promise<AuditEventsResponse> {
    const params = new URLSearchParams({ limit: String(limit) });
    if (event) {
      params.set('event', event);
    }
    const { data } = await api.get<AuditEventsResponse>(
      `/admin/metrics/events?${params.toString()}`
    );
    return data;
  },

  async resetMetrics(): Promise<{ ok: boolean; message: string }> {
    const { data } = await api.post<{ ok: boolean; message: string }>('/admin/metrics/reset');
    return data;
  },
};

export const reportsService = {
  async getDailySales(date: string): Promise<SalesReportResponse> {
    const { data } = await api.get<SalesReportResponse>(`/admin/reports/sales?date=${date}`);
    return data;
  },
};

export const restaurantService = {
  async getPublicSettings(): Promise<RestaurantSettings> {
    const { data } = await api.get<RestaurantSettings>('/restaurant/settings');
    return data;
  },
  async getAdminSettings(): Promise<RestaurantSettingsAdmin> {
    const { data } = await api.get<RestaurantSettingsAdmin>('/admin/restaurant/settings');
    return data;
  },
  async updateAdminSettings(
    payload: Omit<RestaurantSettingsAdmin, 'updated_at'>
  ): Promise<RestaurantSettingsAdmin> {
    const { data } = await api.patch<RestaurantSettingsAdmin>('/admin/restaurant/settings', payload);
    return data;
  },
  async getStatus(): Promise<RestaurantStatus> {
    const { data } = await api.get<RestaurantStatus>('/restaurant/status');
    return data;
  },
  async getOpeningHours(): Promise<OpeningHour[]> {
    const { data } = await api.get<OpeningHour[]>('/admin/restaurant/opening-hours');
    return data;
  },
  async updateOpeningHours(payload: OpeningHour[]): Promise<OpeningHour[]> {
    const { data } = await api.put<OpeningHour[]>('/admin/restaurant/opening-hours', payload);
    return data;
  },
  async updateTemporaryClosure(payload: {
    temporary_closed: boolean;
    temporary_closed_message?: string;
  }): Promise<RestaurantSettingsAdmin> {
    const { data } = await api.patch<RestaurantSettingsAdmin>(
      '/admin/restaurant/temporary-closure',
      payload
    );
    return data;
  },
};

export type PrintJob = {
  id: number;
  status: string;
  attempt_count: number;
  max_attempts: number;
  last_error: string | null;
  locked_by: string | null;
  created_at: string;
  updated_at: string;
  printed_at: string | null;
};

export default api;
