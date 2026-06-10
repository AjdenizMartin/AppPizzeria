import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { AxiosError } from 'axios';
import { useNavigate } from 'react-router-dom';
import { MENU_CATEGORIES, ORDER_STATUS_TRANSITIONS } from '../constants/catalog';
import { useAuth } from '../hooks/useAuth';
import { buildApiUrl, observabilityService, orderService, productService, reportsService, restaurantService } from '../services/api';
import type { AuditEventsResponse, MetricsResponse, OpeningHour, OpsStatusResponse, Order, Product, RestaurantSettingsAdmin, SalesReportResponse } from '../types';

const STATUS_COLORS: Record<string, string> = {
  created: 'bg-gray-100 text-gray-800',
  paid: 'bg-blue-100 text-blue-800',
  accepted: 'bg-green-100 text-green-800',
  printing: 'bg-yellow-100 text-yellow-800',
  printed: 'bg-indigo-100 text-indigo-800',
  ready: 'bg-teal-100 text-teal-800',
  delivered: 'bg-emerald-100 text-emerald-800',
  failed: 'bg-red-100 text-red-800',
  cancelled: 'bg-stone-100 text-stone-800',
  pending: 'bg-slate-100 text-slate-800',
};

const PLACEHOLDER_IMAGE = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" fill="%23f4ede2"><rect width="400" height="300"/><text x="50%" y="50%" font-family="Arial" font-size="24" fill="%235f4336" text-anchor="middle" dy=".3em">Pizzeria</text></svg>'
);

const ALERT_THRESHOLDS = {
  createdUnpaidMinutes: 15,
  acceptedOrPrintingMinutes: 25,
  readyUndeliveredMinutes: 20,
};
const WEEKDAY_LABELS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'];
const ORDER_PAGE_SIZE = 10;

function getTodayDateInputValue() {
  const today = new Date();
  const year = today.getFullYear();
  const month = String(today.getMonth() + 1).padStart(2, '0');
  const day = String(today.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

type ProductFormState = {
  name: string;
  price: string;
  category: string;
  description: string;
  is_available: boolean;
  file: File | null;
};

const EMPTY_PRODUCT_FORM: ProductFormState = {
  name: '',
  price: '',
  category: '',
  description: '',
  is_available: true,
  file: null,
};

function formatApiError(error: unknown, fallback: string) {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') return detail;
    if (Array.isArray(detail)) {
      return detail.map((item) => item.msg || item.message || JSON.stringify(item)).join(' | ');
    }
  }
  if (error instanceof Error && error.message) return error.message;
  return fallback;
}

function buildProductPayload(form: ProductFormState) {
  const data = new FormData();
  data.append('name', form.name.trim());
  data.append('price', form.price);
  data.append('category', form.category);
  data.append('description', form.description.trim());
  data.append('is_available', String(form.is_available));
  if (form.file) data.append('file', form.file);
  return data;
}

function minutesSince(timestamp: string) {
  const now = Date.now();
  const past = new Date(timestamp).getTime();
  return Math.max(0, Math.floor((now - past) / 60000));
}

function getOrderAlerts(order: Order) {
  const alerts: string[] = [];
  const minsFromCreated = minutesSince(order.created_at);
  const minsFromUpdated = minutesSince(order.updated_at);

  if (order.print_jobs.some((job) => job.status === 'failed')) {
    alerts.push('Print failed. Reprint required.');
  }
  if (order.status === 'created' && minsFromCreated >= ALERT_THRESHOLDS.createdUnpaidMinutes) {
    alerts.push('Pending payment for too long.');
  }
  if (
    ['accepted', 'printing'].includes(order.status) &&
    minsFromUpdated >= ALERT_THRESHOLDS.acceptedOrPrintingMinutes
  ) {
    alerts.push('Kitchen delay: accepted/printing too long.');
  }
  if (order.status === 'ready' && minsFromUpdated >= ALERT_THRESHOLDS.readyUndeliveredMinutes) {
    alerts.push('Ready order not delivered yet.');
  }
  return alerts;
}

function getTimelineState(order: Order, step: string) {
  const current = order.status.toLowerCase();
  const sequence = ['created', 'paid', 'accepted', 'printing', 'printed', 'ready', 'delivered'];
  const currentIndex = sequence.indexOf(current);
  const stepIndex = sequence.indexOf(step);
  if (current === 'cancelled' || current === 'failed') {
    return 'muted';
  }
  if (currentIndex >= stepIndex) return 'done';
  return 'pending';
}

function formatStepLabel(step: string) {
  const map: Record<string, string> = {
    created: 'received',
    paid: 'paid',
    accepted: 'accepted/preparing',
    printing: 'printing',
    printed: 'printed',
    ready: 'ready',
    delivered: 'delivered',
  };
  return map[step] || step;
}

function normalizeEventStatus(event: { new_status?: string; status?: string }) {
  return (event.new_status || event.status || '').toLowerCase();
}

export function AdminPage() {
  const navigate = useNavigate();
  const { isAdmin, loading: authLoading, role } = useAuth();
  const canManageOrders = role === 'owner' || role === 'manager' || role === 'staff';
  const canManageProducts = role === 'owner' || role === 'manager';
  const canSeeReports = role === 'owner' || role === 'manager';
  const canManageSettings = role === 'owner';

  const [orders, setOrders] = useState<Order[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [opsStatus, setOpsStatus] = useState<OpsStatusResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEventsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');

  const [statusFilter, setStatusFilter] = useState('');
  const [paymentFilter, setPaymentFilter] = useState('');
  const [orderDate] = useState(() => getTodayDateInputValue());
  const [searchFilter, setSearchFilter] = useState('');
  const [offset, setOffset] = useState(0);
  const [hasMore, setHasMore] = useState(false);

  const [productMessage, setProductMessage] = useState('');
  const [productSearch, setProductSearch] = useState('');
  const [productForm, setProductForm] = useState<ProductFormState>(EMPTY_PRODUCT_FORM);
  const [editingProductId, setEditingProductId] = useState<number | null>(null);
  const [savingProduct, setSavingProduct] = useState(false);
  const [reportDate, setReportDate] = useState(new Date().toISOString().slice(0, 10));
  const [salesReport, setSalesReport] = useState<SalesReportResponse | null>(null);
  const [salesLoading, setSalesLoading] = useState(false);
  const [restaurantSettings, setRestaurantSettings] = useState<RestaurantSettingsAdmin | null>(null);
  const [settingsSaving, setSettingsSaving] = useState(false);
  const [settingsMessage, setSettingsMessage] = useState('');
  const [openingHours, setOpeningHours] = useState<OpeningHour[]>([]);

  const fetchOrders = useCallback(
    async (nextOffset = 0, append = false) => {
      const response = await orderService.getAdminOrdersFiltered({
        status: statusFilter || undefined,
        payment_method: paymentFilter || undefined,
        date_from: orderDate,
        date_to: orderDate,
        search: searchFilter.trim() || undefined,
        limit: ORDER_PAGE_SIZE,
        offset: nextOffset,
      });
      setHasMore(response.length === ORDER_PAGE_SIZE);
      setOffset(nextOffset);
      setOrders((current) => (append ? [...current, ...response] : response));
    },
    [statusFilter, paymentFilter, orderDate, searchFilter]
  );

  const fetchDashboard = useCallback(async () => {
    try {
      const [metricsData, productsData] = await Promise.all([
        observabilityService.getMetrics(),
        productService.getAdminAll(true),
      ]);
      const [opsData, eventsData, settingsData, hoursData] = await Promise.all([
        observabilityService.getOpsStatus(),
        observabilityService.getAuditEvents(undefined, 10),
        restaurantService.getAdminSettings(),
        restaurantService.getOpeningHours(),
      ]);
      await fetchOrders(0, false);
      setMetrics(metricsData);
      setOpsStatus(opsData);
      setAuditEvents(eventsData);
      setRestaurantSettings(settingsData);
      setOpeningHours(hoursData);
      setProducts(productsData);
      setError('');
    } catch (err) {
      setError(formatApiError(err, 'Failed to load dashboard data'));
    } finally {
      setLoading(false);
    }
  }, [fetchOrders]);

  const fetchSalesReport = useCallback(async (targetDate: string) => {
    setSalesLoading(true);
    try {
      const data = await reportsService.getDailySales(targetDate);
      setSalesReport(data);
    } catch (err) {
      setError(formatApiError(err, 'Failed to load sales report'));
    } finally {
      setSalesLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !isAdmin) navigate('/');
  }, [authLoading, isAdmin, navigate]);

  useEffect(() => {
    if (!isAdmin) return;
    queueMicrotask(() => {
      void fetchDashboard();
      void fetchSalesReport(reportDate);
    });
    const interval = setInterval(fetchDashboard, 30000);
    return () => clearInterval(interval);
  }, [isAdmin, fetchDashboard, fetchSalesReport, reportDate]);

  useEffect(() => {
    if (!isAdmin) return;
    queueMicrotask(() => {
      fetchOrders(0, false).catch(() => {
        setError('Could not apply order filters');
      });
    });
  }, [isAdmin, fetchOrders]);

  const visibleProducts = useMemo(() => {
    const normalized = productSearch.trim().toLowerCase();
    if (!normalized) return products;
    return products.filter((product) => {
      const haystack = `${product.name} ${product.description || ''} ${product.category}`.toLowerCase();
      return haystack.includes(normalized);
    });
  }, [productSearch, products]);

  const resetProductForm = useCallback(() => {
    setProductForm(EMPTY_PRODUCT_FORM);
    setEditingProductId(null);
  }, []);

  const handleStatusChange = async (orderId: number, newStatus: string) => {
    try {
      await orderService.updateStatus(orderId, newStatus);
      await fetchOrders(offset, false);
      setError('');
    } catch (err) {
      setError(formatApiError(err, `Invalid transition for order #${orderId}.`));
    }
  };

  const handleReprint = async (orderId: number) => {
    try {
      await orderService.reprint(orderId);
      await fetchOrders(offset, false);
      setError('');
    } catch (err) {
      setError(formatApiError(err, 'Failed to reprint order'));
    }
  };

  const handleResetMetrics = async () => {
    try {
      await observabilityService.resetMetrics();
      await fetchDashboard();
    } catch (err) {
      setError(formatApiError(err, 'Failed to reset metrics'));
    }
  };

  const handleProductSubmit = async (event: FormEvent) => {
    event.preventDefault();
    setSavingProduct(true);
    setProductMessage('');
    try {
      const payload = buildProductPayload(productForm);
      const saved = editingProductId
        ? await productService.update(editingProductId, payload)
        : await productService.create(payload);
      setProductMessage(
        editingProductId ? `Product "${saved.name}" updated.` : `Product "${saved.name}" created.`
      );
      resetProductForm();
      const freshProducts = await productService.getAdminAll(true);
      setProducts(freshProducts);
    } catch (err) {
      setProductMessage(formatApiError(err, 'Could not save product'));
    } finally {
      setSavingProduct(false);
    }
  };

  const startEditingProduct = (product: Product) => {
    setEditingProductId(product.id);
    setProductForm({
      name: product.name,
      price: String(product.price),
      category: product.category,
      description: product.description || '',
      is_available: product.is_available,
      file: null,
    });
    setProductMessage(`Editing "${product.name}"`);
  };

  const handleDeleteProduct = async (productId: number) => {
    try {
      await productService.remove(productId);
      if (editingProductId === productId) resetProductForm();
      setProductMessage('Product removed/archived.');
      setProducts(await productService.getAdminAll(true));
    } catch (err) {
      setProductMessage(formatApiError(err, 'Could not delete product'));
    }
  };

  const handleArchiveProduct = async (productId: number, archived: boolean) => {
    try {
      await productService.archive(productId, archived);
      setProductMessage(archived ? 'Product archived.' : 'Product restored.');
      setProducts(await productService.getAdminAll(true));
    } catch (err) {
      setProductMessage(formatApiError(err, 'Could not update archive status'));
    }
  };

  const handleRestaurantSettingsSave = async (event: FormEvent) => {
    event.preventDefault();
    if (!restaurantSettings) return;
    setSettingsSaving(true);
    setSettingsMessage('');
    try {
      const updated = await restaurantService.updateAdminSettings({
        restaurant_name: restaurantSettings.restaurant_name,
        public_phone: restaurantSettings.public_phone,
        whatsapp_number: restaurantSettings.whatsapp_number,
        address: restaurantSettings.address,
        delivery_fee: Number(restaurantSettings.delivery_fee),
        minimum_order_amount: Number(restaurantSettings.minimum_order_amount),
        estimated_delivery_minutes: Number(restaurantSettings.estimated_delivery_minutes),
        is_accepting_orders: restaurantSettings.is_accepting_orders,
        temporary_closed: restaurantSettings.temporary_closed,
        temporary_closed_message: restaurantSettings.temporary_closed_message || '',
        banner_text: restaurantSettings.banner_text || '',
      });
      setRestaurantSettings(updated);
      setSettingsMessage('Restaurant settings updated.');
    } catch (err) {
      setSettingsMessage(formatApiError(err, 'Could not update restaurant settings'));
    } finally {
      setSettingsSaving(false);
    }
  };

  const handleOpeningHoursSave = async () => {
    try {
      const updated = await restaurantService.updateOpeningHours(openingHours);
      setOpeningHours(updated);
      setSettingsMessage('Opening hours updated.');
    } catch (err) {
      setSettingsMessage(formatApiError(err, 'Could not update opening hours'));
    }
  };


  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">📋</div>
          <p className="text-gray-600 dark:text-slate-300">Loading control room...</p>
        </div>
      </div>
    );
  }
  if (!isAdmin) return null;

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-gradient-to-r from-stone-950 via-orange-900 to-orange-600 text-white p-8 shadow-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="uppercase tracking-[0.3em] text-xs text-orange-200 mb-3">React Control Room</p>
            <h1 className="text-3xl md:text-4xl font-bold mb-3">Pizzeria operations dashboard</h1>
            <p className="text-orange-100 max-w-3xl">
              Manage products, control kitchen flow and monitor print health in one place.
            </p>
          </div>
          <div className="flex gap-3">
            <button onClick={fetchDashboard} className="rounded-xl bg-white/15 hover:bg-white/20 px-4 py-3 text-sm font-semibold">
              Refresh dashboard
            </button>
            <button onClick={handleResetMetrics} className="rounded-xl border border-white/20 bg-black/15 hover:bg-black/25 px-4 py-3 text-sm font-semibold">
              Reset metrics
            </button>
          </div>
        </div>
      </section>

      {canManageSettings && <section className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
        <h2 className="text-2xl font-bold">Restaurant settings</h2>
        {restaurantSettings ? (
          <form onSubmit={handleRestaurantSettingsSave} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Restaurant name</label>
              <input value={restaurantSettings.restaurant_name} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, restaurant_name: event.target.value } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Public phone</label>
              <input value={restaurantSettings.public_phone} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, public_phone: event.target.value } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">WhatsApp</label>
              <input value={restaurantSettings.whatsapp_number} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, whatsapp_number: event.target.value } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Address</label>
              <input value={restaurantSettings.address} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, address: event.target.value } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Delivery fee (EUR)</label>
              <input type="number" step="0.01" min="0" value={restaurantSettings.delivery_fee} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, delivery_fee: Number(event.target.value) } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Minimum order (EUR)</label>
              <input type="number" step="0.01" min="0" value={restaurantSettings.minimum_order_amount} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, minimum_order_amount: Number(event.target.value) } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Estimated delivery (minutes)</label>
              <input type="number" min="1" max="240" value={restaurantSettings.estimated_delivery_minutes} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, estimated_delivery_minutes: Number(event.target.value) } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div className="flex items-end">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-slate-200">
                <input type="checkbox" checked={restaurantSettings.is_accepting_orders} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, is_accepting_orders: event.target.checked } : s))} />
                Accepting orders
              </label>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Banner text</label>
              <input value={restaurantSettings.banner_text || ''} onChange={(event) => setRestaurantSettings((s) => (s ? { ...s, banner_text: event.target.value } : s))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div className="md:col-span-2 rounded-xl border p-4 space-y-3">
              <h3 className="font-semibold">Temporary closure</h3>
              <label className="flex items-center gap-2 text-sm">
                <input
                  type="checkbox"
                  checked={restaurantSettings.temporary_closed}
                  onChange={(event) =>
                    setRestaurantSettings((s) =>
                      s ? { ...s, temporary_closed: event.target.checked } : s
                    )
                  }
                />
                Temporarily closed
              </label>
              <input
                value={restaurantSettings.temporary_closed_message || ''}
                onChange={(event) =>
                  setRestaurantSettings((s) =>
                    s ? { ...s, temporary_closed_message: event.target.value } : s
                  )
                }
                className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400"
                placeholder="Temporary closure message"
              />
            </div>
            <div className="md:col-span-2">
              <button type="submit" disabled={settingsSaving} className="rounded-xl bg-orange-500 hover:bg-orange-600 text-white px-5 py-3 font-semibold disabled:opacity-60">
                {settingsSaving ? 'Saving...' : 'Save restaurant settings'}
              </button>
            </div>
            {settingsMessage && (
              <div className="md:col-span-2 rounded-xl bg-amber-50 text-amber-800 p-3 text-sm">
                {settingsMessage}
              </div>
            )}
          </form>
        ) : (
          <p className="text-sm text-gray-500 dark:text-slate-400">Loading restaurant settings...</p>
        )}
        <div className="rounded-xl border p-4 space-y-3">
          <h3 className="font-semibold">Weekly opening hours</h3>
          <div className="space-y-2">
            {openingHours.map((hour, idx) => (
              <div key={`${hour.day_of_week}-${idx}`} className="grid grid-cols-1 md:grid-cols-4 gap-2">
                <input value={WEEKDAY_LABELS[hour.day_of_week] || `Day ${hour.day_of_week}`} disabled className="rounded border px-2 py-2 text-sm bg-gray-50 dark:bg-slate-800" />
                <input value={hour.opens_at} onChange={(event) => setOpeningHours((curr) => curr.map((x, i) => i === idx ? { ...x, opens_at: event.target.value } : x))} className="rounded border px-2 py-2 text-sm" />
                <input value={hour.closes_at} onChange={(event) => setOpeningHours((curr) => curr.map((x, i) => i === idx ? { ...x, closes_at: event.target.value } : x))} className="rounded border px-2 py-2 text-sm" />
                <label className="flex items-center gap-2 text-sm"><input type="checkbox" checked={hour.is_closed} onChange={(event) => setOpeningHours((curr) => curr.map((x, i) => i === idx ? { ...x, is_closed: event.target.checked } : x))} />Closed</label>
              </div>
            ))}
          </div>
          <button onClick={handleOpeningHoursSave} className="rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-slate-800 dark:bg-slate-800">Save opening hours</button>
        </div>
      </section>}

      {canSeeReports && <section className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
        <div className="flex items-center justify-between gap-3">
          <h2 className="text-2xl font-bold">Daily sales report</h2>
          <div className="flex items-center gap-2">
            <input
              type="date"
              value={reportDate}
              onChange={(event) => setReportDate(event.target.value)}
              className="rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-3 py-2"
            />
            <button
              onClick={() => fetchSalesReport(reportDate)}
              className="rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-3 py-2 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-slate-800 dark:bg-slate-800"
            >
              Refresh report
            </button>
          </div>
        </div>
        {salesLoading && <p className="text-sm text-gray-500 dark:text-slate-400">Loading report...</p>}
        {salesReport && (
          <>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="rounded-xl bg-gray-50 dark:bg-slate-800 p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Revenue</p><p className="text-lg font-bold">EUR {salesReport.revenue_total.toFixed(2)}</p></div>
              <div className="rounded-xl bg-gray-50 dark:bg-slate-800 p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Orders</p><p className="text-lg font-bold">{salesReport.total_orders}</p></div>
              <div className="rounded-xl bg-gray-50 dark:bg-slate-800 p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Avg ticket</p><p className="text-lg font-bold">EUR {salesReport.average_ticket.toFixed(2)}</p></div>
              <div className="rounded-xl bg-gray-50 dark:bg-slate-800 p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Items sold</p><p className="text-lg font-bold">{salesReport.total_items_sold}</p></div>
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
              <div className="rounded-xl border p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Cash</p><p className="font-semibold">EUR {salesReport.cash_total.toFixed(2)}</p></div>
              <div className="rounded-xl border p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Card</p><p className="font-semibold">EUR {salesReport.card_total.toFixed(2)}</p></div>
              <div className="rounded-xl border p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Paid/completed</p><p className="font-semibold">{salesReport.paid_or_completed_orders}</p></div>
              <div className="rounded-xl border p-3"><p className="text-xs text-gray-500 dark:text-slate-400">Cancelled</p><p className="font-semibold">{salesReport.cancelled_orders}</p></div>
            </div>
            <div>
              <h3 className="text-lg font-semibold mb-2">Top products</h3>
              {salesReport.top_products.length === 0 ? (
                <p className="text-sm text-gray-500 dark:text-slate-400">No sales for this date.</p>
              ) : (
                <div className="space-y-2">
                  {salesReport.top_products.map((item) => (
                    <div key={`${item.product_id}-${item.product_name}`} className="rounded-xl border p-3 flex items-center justify-between gap-3 text-sm">
                      <span className="font-medium">{item.product_name}</span>
                      <span>{item.quantity_sold} sold · EUR {item.revenue.toFixed(2)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </>
        )}
      </section>}

      <section className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h2 className="text-2xl font-bold">Order filters</h2>
            <p className="text-sm text-gray-500 dark:text-slate-400">Showing today's orders: {orderDate}</p>
          </div>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-4 gap-3">
          <select value={statusFilter} onChange={(event) => setStatusFilter(event.target.value)} className="rounded-xl border px-4 py-2">
            <option value="">All status</option>
            {Object.keys(ORDER_STATUS_TRANSITIONS).map((status) => (
              <option key={status} value={status}>{status}</option>
            ))}
          </select>
          <select value={paymentFilter} onChange={(event) => setPaymentFilter(event.target.value)} className="rounded-xl border px-4 py-2">
            <option value="">All payments</option>
            <option value="card">card</option>
            <option value="cash">cash</option>
          </select>
          <input
            value={searchFilter}
            onChange={(event) => setSearchFilter(event.target.value)}
            placeholder="Order ID, name, phone, email"
            className="rounded-xl border px-4 py-2 md:col-span-2"
          />
        </div>
      </section>

      {error && <div className="rounded-2xl bg-red-50 text-red-700 p-4">{error}</div>}

      {canManageOrders && <section className="space-y-4">
        <h2 className="text-2xl font-bold">Orders</h2>
        {orders.length === 0 ? (
          <div className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-12 text-center text-gray-500 dark:text-slate-400">No orders found.</div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => {
              const currentStatus = String(order.status || 'created').toLowerCase();
              const allowedStatuses = [
                currentStatus,
                ...(ORDER_STATUS_TRANSITIONS[currentStatus] || []),
              ];
              const latestPrint = order.print_jobs[0];
              const alerts = getOrderAlerts(order);
              return (
                <article key={order.id} className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <h3 className="text-xl font-bold">Order #{order.id}</h3>
                      <p className="text-sm text-gray-500 dark:text-slate-400">
                        {order.customer_name} · {order.customer_phone} · {order.customer_email || 'no email'}
                      </p>
                      <p className="text-sm text-gray-600 dark:text-slate-300">
                        {order.delivery_address}, {order.delivery_city} {order.delivery_postal_code}
                      </p>
                      {order.delivery_notes && (
                        <p className="text-sm text-gray-600 dark:text-slate-300">Notes: {order.delivery_notes}</p>
                      )}
                    </div>
                    <div className="text-right">
                      <span className={`px-3 py-1 rounded-full text-sm font-medium ${STATUS_COLORS[order.status] || 'bg-gray-100'}`}>
                        {order.status}
                      </span>
                      <p className="text-sm text-gray-500 dark:text-slate-400 mt-2">Payment: {order.payment_method}</p>
                      <p className="text-lg font-bold">EUR {Number(order.total_price).toFixed(2)}</p>
                      <p className="text-xs text-gray-500 dark:text-slate-400">
                        Created: {new Date(order.created_at).toLocaleString()}
                      </p>
                      <p className="text-xs text-gray-500 dark:text-slate-400">
                        Updated: {new Date(order.updated_at).toLocaleString()}
                      </p>
                    </div>
                  </div>

                  {alerts.length > 0 && (
                    <div className="rounded-xl bg-amber-50 border border-amber-200 p-3 text-sm text-amber-800">
                      {alerts.join(' ')}
                    </div>
                  )}

                  {order.status_events && order.status_events.length > 0 ? (
                    <div className="space-y-2">
                      {order.status_events.map((event, idx) => (
                        <div key={`${order.id}-evt-${idx}`} className="rounded-lg bg-gray-50 dark:bg-slate-800 px-3 py-2 text-xs">
                          <span className="font-semibold">{formatStepLabel(normalizeEventStatus(event))}</span>
                          <span className="ml-2 text-gray-600 dark:text-slate-300">
                            {new Date(event.created_at).toLocaleString()}
                          </span>
                          {event.source && (
                            <span className="ml-2 rounded bg-white px-2 py-0.5 text-gray-600 dark:text-slate-300 border">
                              {event.source}
                            </span>
                          )}
                        </div>
                      ))}
                    </div>
                  ) : (
                    <div className="grid grid-cols-2 md:grid-cols-7 gap-2 text-xs">
                      {['created', 'paid', 'accepted', 'printing', 'printed', 'ready', 'delivered'].map((step) => {
                        const state = getTimelineState(order, step);
                        const classes = state === 'done'
                          ? 'bg-emerald-100 text-emerald-700'
                          : state === 'pending'
                            ? 'bg-gray-100 text-gray-500 dark:text-slate-400'
                            : 'bg-red-100 text-red-700';
                        return (
                          <div key={`${order.id}-${step}`} className={`rounded-lg px-2 py-1 text-center ${classes}`}>
                            {formatStepLabel(step)}
                          </div>
                        );
                      })}
                    </div>
                  )}
                  {['failed', 'cancelled'].includes(order.status) && (
                    <div className="text-sm text-red-700">
                      Order ended as {order.status}.
                    </div>
                  )}

                  <div className="border-t pt-3 space-y-2">
                    {order.items.map((item) => (
                      <div key={item.id} className="flex justify-between text-sm">
                        <span>{item.quantity}x {item.product_name}{item.extras ? ` · ${item.extras}` : ''}</span>
                        <span>EUR {Number(item.price).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-col lg:flex-row lg:items-center lg:justify-between gap-3">
                    <div className="flex flex-wrap gap-2 items-center">
                      <select
                        value={currentStatus}
                        onChange={(event) => handleStatusChange(order.id, event.target.value)}
                        className="rounded-xl border px-4 py-2 text-sm"
                      >
                        {allowedStatuses.map((status, index) => (
                          <option key={`${order.id}-${status}-${index}`} value={status}>{status}</option>
                        ))}
                      </select>
                      <button onClick={() => handleReprint(order.id)} className="rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-slate-800 dark:bg-slate-800">
                        Reprint ticket
                      </button>
                    </div>
                    <div className="text-sm text-gray-600 dark:text-slate-300">
                      {latestPrint
                        ? `Print #${latestPrint.id} · ${latestPrint.status}${
                            latestPrint.last_error ? ` · error: ${latestPrint.last_error}` : ''
                          }`
                        : 'No print job yet'}
                    </div>
                  </div>
                </article>
              );
            })}
            {hasMore && (
              <button
                onClick={() => fetchOrders(offset + ORDER_PAGE_SIZE, true)}
                className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 font-semibold hover:bg-gray-50 dark:hover:bg-slate-800 dark:bg-slate-800"
              >
                Load more
              </button>
            )}
          </div>
        )}
      </section>}

      {canManageProducts && <section className="grid grid-cols-1 xl:grid-cols-[1.05fr_1.35fr] gap-6">
        <article className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex items-center justify-between gap-4 mb-5">
            <div>
              <p className="uppercase tracking-[0.25em] text-xs text-orange-500 mb-2">Catalog</p>
              <h2 className="text-2xl font-bold">{editingProductId ? 'Edit product' : 'Create product'}</h2>
            </div>
            {editingProductId && (
              <button onClick={resetProductForm} className="rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-slate-800 dark:bg-slate-800">
                Cancel edit
              </button>
            )}
          </div>
          {productMessage && <div className="mb-4 rounded-2xl bg-amber-50 text-amber-800 p-4 text-sm">{productMessage}</div>}
          <form onSubmit={handleProductSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Name</label>
              <input required value={productForm.name} onChange={(event) => setProductForm((current) => ({ ...current, name: event.target.value }))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" placeholder="Smoky Pepperoni Feast" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Price</label>
              <input required type="number" step="0.01" min="0" value={productForm.price} onChange={(event) => setProductForm((current) => ({ ...current, price: event.target.value }))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" placeholder="12.50" />
            </div>
            <div>
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Category</label>
              <select required value={productForm.category} onChange={(event) => setProductForm((current) => ({ ...current, category: event.target.value }))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400">
                <option value="">Select category</option>
                {MENU_CATEGORIES.map((category) => <option key={category} value={category}>{category}</option>)}
              </select>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Description</label>
              <textarea rows={4} value={productForm.description} onChange={(event) => setProductForm((current) => ({ ...current, description: event.target.value }))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" placeholder="Short, persuasive product description." />
            </div>
            <div className="md:col-span-2">
              <label className="flex items-center gap-2 text-sm font-medium text-gray-700 dark:text-slate-200">
                <input
                  type="checkbox"
                  checked={productForm.is_available}
                  onChange={(event) =>
                    setProductForm((current) => ({
                      ...current,
                      is_available: event.target.checked,
                    }))
                  }
                />
                Available for orders
              </label>
            </div>
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 dark:text-slate-200 mb-1">Image</label>
              <input type="file" accept="image/*" onChange={(event) => setProductForm((current) => ({ ...current, file: event.target.files?.[0] || null }))} className="w-full rounded-xl border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 px-4 py-3 outline-none focus:border-orange-400" />
            </div>
            <div className="md:col-span-2">
              <button type="submit" disabled={savingProduct} className="w-full rounded-xl bg-orange-500 hover:bg-orange-600 text-white px-4 py-3 font-semibold disabled:opacity-60">
                {savingProduct ? 'Saving...' : editingProductId ? 'Save product changes' : 'Publish product'}
              </button>
            </div>
          </form>
        </article>

        <article className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
            <div>
              <p className="uppercase tracking-[0.25em] text-xs text-orange-500 mb-2">Live menu</p>
              <h2 className="text-2xl font-bold">Products</h2>
            </div>
            <input type="search" value={productSearch} onChange={(event) => setProductSearch(event.target.value)} placeholder="Search by name, category or description" className="w-full md:w-80 rounded-xl border px-4 py-3 outline-none focus:border-orange-400" />
          </div>
          {visibleProducts.length === 0 ? (
            <div className="rounded-2xl border border-dashed p-8 text-center text-gray-500 dark:text-slate-400">No products match the current filter.</div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {visibleProducts.map((product) => (
                <article key={product.id} className="overflow-hidden rounded-2xl border">
                  <img src={product.image_url ? buildApiUrl(product.image_url) : PLACEHOLDER_IMAGE} alt={product.name} className="h-40 w-full object-cover" onError={(event) => { event.currentTarget.src = PLACEHOLDER_IMAGE; }} />
                  <div className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="font-semibold text-lg">{product.name}</h3>
                        <p className="text-sm text-gray-500 dark:text-slate-400">{product.category}</p>
                      </div>
                      <span className="text-lg font-bold text-orange-600">EUR {Number(product.price).toFixed(2)}</span>
                    </div>
                    <div>
                      <span className={`rounded-full px-2 py-1 text-xs font-semibold ${product.is_available ? 'bg-emerald-100 text-emerald-700' : 'bg-red-100 text-red-700'}`}>
                        {product.is_available ? 'Available' : 'Sold out'}
                      </span>
                      <span className={`ml-2 rounded-full px-2 py-1 text-xs font-semibold ${product.is_active ? 'bg-blue-100 text-blue-700' : 'bg-slate-200 text-slate-700'}`}>
                        {product.is_active ? 'Active' : 'Archived'}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 dark:text-slate-300 min-h-[2.5rem]">{product.description || 'No description yet.'}</p>
                    <div className="flex gap-2">
                      <button onClick={() => startEditingProduct(product)} className="flex-1 rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-gray-50 dark:hover:bg-slate-800 dark:bg-slate-800">Edit</button>
                      <button onClick={() => handleArchiveProduct(product.id, product.is_active)} className="flex-1 rounded-xl bg-amber-50 text-amber-700 px-4 py-2 text-sm font-semibold hover:bg-amber-100">
                        {product.is_active ? 'Archive' : 'Restore'}
                      </button>
                      <button onClick={() => handleDeleteProduct(product.id)} className="flex-1 rounded-xl bg-red-50 text-red-600 px-4 py-2 text-sm font-semibold hover:bg-red-100">Delete</button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </article>
      </section>}

      {metrics && (
        <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-4"><p className="text-xs text-gray-500 dark:text-slate-400">Requests</p><p className="text-2xl font-bold">{metrics.total_requests}</p></div>
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-4"><p className="text-xs text-gray-500 dark:text-slate-400">Errors (5xx)</p><p className="text-2xl font-bold text-red-600">{metrics.total_errors}</p></div>
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-4"><p className="text-xs text-gray-500 dark:text-slate-400">Avg latency</p><p className="text-2xl font-bold">{metrics.average_latency_ms.toFixed(1)} ms</p></div>
          <div className="bg-white dark:bg-slate-900 rounded-2xl shadow-sm border border-slate-200 dark:border-slate-700 p-4"><p className="text-xs text-gray-500 dark:text-slate-400">In flight</p><p className="text-2xl font-bold">{metrics.in_flight_requests}</p></div>
        </section>
      )}

      {opsStatus && (
        <section className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-2xl font-bold">Operational status</h2>
            <span className={`px-3 py-1 rounded-full text-sm font-semibold ${
              opsStatus.status === 'green'
                ? 'bg-emerald-100 text-emerald-700'
                : opsStatus.status === 'yellow'
                  ? 'bg-amber-100 text-amber-700'
                  : 'bg-red-100 text-red-700'
            }`}>{opsStatus.status.toUpperCase()}</span>
          </div>
          <p className="text-sm text-gray-600 dark:text-slate-300 mb-4">
            Error rate: {opsStatus.stats.error_rate_percent.toFixed(2)}% · Print failures: {opsStatus.stats.print_failures}
          </p>
          {opsStatus.recent_critical_events.length > 0 ? (
            <div className="space-y-3">
              {opsStatus.recent_critical_events.slice(0, 5).map((event, index) => (
                <div key={`${event.timestamp}-${index}`} className="rounded-2xl border p-3 text-sm">
                  <p className="font-semibold text-gray-900 dark:text-slate-100">{event.event}</p>
                  <p className="text-gray-600 dark:text-slate-300">{event.detail}</p>
                  <p className="text-xs text-gray-400 mt-1">{new Date(event.timestamp).toLocaleString()}</p>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-gray-500 dark:text-slate-400">No critical events recorded.</p>}
        </section>
      )}

      {auditEvents && (
        <section className="bg-white dark:bg-slate-900 rounded-3xl shadow-sm border border-slate-200 dark:border-slate-700 p-6">
          <h2 className="text-2xl font-bold mb-4">Recent audit events</h2>
          {auditEvents.events.length > 0 ? (
            <div className="space-y-3">
              {auditEvents.events.map((event, index) => (
                <div key={`${event.timestamp}-${index}`} className="rounded-2xl border p-3 text-sm">
                  <p className="font-semibold text-gray-900 dark:text-slate-100">{event.event}</p>
                  <p className="text-gray-600 dark:text-slate-300">{event.detail}</p>
                  <p className="text-xs text-gray-400 mt-1">{new Date(event.timestamp).toLocaleString()}</p>
                </div>
              ))}
            </div>
          ) : <p className="text-sm text-gray-500 dark:text-slate-400">No audit events available.</p>}
        </section>
      )}
    </div>
  );
}
