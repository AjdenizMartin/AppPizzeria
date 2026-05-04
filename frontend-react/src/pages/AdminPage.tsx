import { useCallback, useEffect, useMemo, useState } from 'react';
import type { FormEvent } from 'react';
import { AxiosError } from 'axios';
import { useNavigate } from 'react-router-dom';
import { MENU_CATEGORIES, ORDER_STATUS_TRANSITIONS } from '../constants/catalog';
import { useAuth } from '../hooks/useAuth';
import {
  buildApiUrl,
  observabilityService,
  orderService,
  productService,
} from '../services/api';
import type { AuditEventsResponse, MetricsResponse, OpsStatusResponse, Order, Product } from '../types';

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

type ProductFormState = {
  name: string;
  price: string;
  category: string;
  description: string;
  file: File | null;
};

const EMPTY_PRODUCT_FORM: ProductFormState = {
  name: '',
  price: '',
  category: '',
  description: '',
  file: null,
};

function formatApiError(error: unknown, fallback: string) {
  if (error instanceof AxiosError) {
    const detail = error.response?.data?.detail;
    if (typeof detail === 'string') {
      return detail;
    }
    if (Array.isArray(detail)) {
      return detail
        .map((item) => item.msg || item.message || JSON.stringify(item))
        .join(' | ');
    }
  }

  if (error instanceof Error && error.message) {
    return error.message;
  }

  return fallback;
}

function buildProductPayload(form: ProductFormState) {
  const data = new FormData();
  data.append('name', form.name.trim());
  data.append('price', form.price);
  data.append('category', form.category);
  data.append('description', form.description.trim());
  if (form.file) {
    data.append('file', form.file);
  }
  return data;
}

export function AdminPage() {
  const navigate = useNavigate();
  const { isAdmin, loading: authLoading } = useAuth();
  const [orders, setOrders] = useState<Order[]>([]);
  const [products, setProducts] = useState<Product[]>([]);
  const [metrics, setMetrics] = useState<MetricsResponse | null>(null);
  const [opsStatus, setOpsStatus] = useState<OpsStatusResponse | null>(null);
  const [auditEvents, setAuditEvents] = useState<AuditEventsResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [productMessage, setProductMessage] = useState('');
  const [productSearch, setProductSearch] = useState('');
  const [productForm, setProductForm] = useState<ProductFormState>(EMPTY_PRODUCT_FORM);
  const [editingProductId, setEditingProductId] = useState<number | null>(null);
  const [savingProduct, setSavingProduct] = useState(false);

  const fetchDashboard = useCallback(async () => {
    try {
      const [ordersData, metricsData, productsData] = await Promise.all([
        orderService.getAdminOrders(),
        observabilityService.getMetrics(),
        productService.getAll(),
      ]);
      const [opsData, eventsData] = await Promise.all([
        observabilityService.getOpsStatus(),
        observabilityService.getAuditEvents(undefined, 10),
      ]);
      setOrders(ordersData);
      setMetrics(metricsData);
      setOpsStatus(opsData);
      setAuditEvents(eventsData);
      setProducts(productsData);
      setError('');
    } catch (err) {
      setError(formatApiError(err, 'Failed to load dashboard data'));
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    if (!authLoading && !isAdmin) {
      navigate('/');
    }
  }, [authLoading, isAdmin, navigate]);

  useEffect(() => {
    if (!isAdmin) {
      return;
    }

    fetchDashboard();
    const interval = setInterval(fetchDashboard, 30000);
    return () => clearInterval(interval);
  }, [isAdmin, fetchDashboard]);

  const visibleProducts = useMemo(() => {
    const normalized = productSearch.trim().toLowerCase();
    if (!normalized) {
      return products;
    }
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
      setError('');
      await fetchDashboard();
    } catch (err) {
      setError(
        formatApiError(err, `Invalid transition for order #${orderId}. Use one of the allowed next states.`)
      );
    }
  };

  const handleReprint = async (orderId: number) => {
    try {
      await orderService.reprint(orderId);
      setError('');
      await fetchDashboard();
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
      const savedProduct = editingProductId
        ? await productService.update(editingProductId, payload)
        : await productService.create(payload);

      setProductMessage(
        editingProductId
          ? `Product "${savedProduct.name}" updated successfully.`
          : `Product "${savedProduct.name}" created successfully.`
      );
      resetProductForm();
      await fetchDashboard();
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
      file: null,
    });
    setProductMessage(`Editing "${product.name}"`);
  };

  const handleDeleteProduct = async (productId: number) => {
    try {
      await productService.remove(productId);
      if (editingProductId === productId) {
        resetProductForm();
      }
      setProductMessage('Product deleted.');
      await fetchDashboard();
    } catch (err) {
      setProductMessage(formatApiError(err, 'Could not delete product'));
    }
  };

  if (authLoading || loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">📋</div>
          <p className="text-gray-600">Loading control room...</p>
        </div>
      </div>
    );
  }

  if (!isAdmin) {
    return null;
  }

  return (
    <div className="space-y-8">
      <section className="rounded-3xl bg-gradient-to-r from-stone-950 via-orange-900 to-orange-600 text-white p-8 shadow-xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="uppercase tracking-[0.3em] text-xs text-orange-200 mb-3">
              React Control Room
            </p>
            <h1 className="text-3xl md:text-4xl font-bold mb-3">Pizzeria operations dashboard</h1>
            <p className="text-orange-100 max-w-3xl">
              Manage products, control kitchen flow, monitor print health and keep the storefront
              ready without leaving the React app.
            </p>
          </div>
          <div className="flex gap-3">
            <button
              onClick={fetchDashboard}
              className="rounded-xl bg-white/15 hover:bg-white/20 px-4 py-3 text-sm font-semibold"
            >
              Refresh dashboard
            </button>
            <button
              onClick={handleResetMetrics}
              className="rounded-xl border border-white/20 bg-black/15 hover:bg-black/25 px-4 py-3 text-sm font-semibold"
            >
              Reset metrics
            </button>
          </div>
        </div>
      </section>

      <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-sm text-gray-500">Products</p>
          <p className="text-3xl font-bold mt-2">{products.length}</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-sm text-gray-500">Categories</p>
          <p className="text-3xl font-bold mt-2">{new Set(products.map((product) => product.category)).size}</p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-sm text-gray-500">Open orders</p>
          <p className="text-3xl font-bold mt-2">
            {orders.filter((order) => !['cancelled', 'delivered'].includes(order.status)).length}
          </p>
        </div>
        <div className="bg-white rounded-2xl shadow-sm p-5">
          <p className="text-sm text-gray-500">Print failures</p>
          <p className="text-3xl font-bold mt-2 text-orange-600">
            {metrics?.business_events.print_job_failed || 0}
          </p>
        </div>
      </section>

      {error && <div className="rounded-2xl bg-red-50 text-red-700 p-4">{error}</div>}

      <section className="grid grid-cols-1 xl:grid-cols-[1.05fr_1.35fr] gap-6">
        <article className="bg-white rounded-3xl shadow-sm p-6">
          <div className="flex items-center justify-between gap-4 mb-5">
            <div>
              <p className="uppercase tracking-[0.25em] text-xs text-orange-500 mb-2">Catalog</p>
              <h2 className="text-2xl font-bold">
                {editingProductId ? 'Edit product' : 'Create product'}
              </h2>
            </div>
            {editingProductId && (
              <button
                onClick={resetProductForm}
                className="rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-gray-50"
              >
                Cancel edit
              </button>
            )}
          </div>

          {productMessage && (
            <div className="mb-4 rounded-2xl bg-amber-50 text-amber-800 p-4 text-sm">
              {productMessage}
            </div>
          )}

          <form onSubmit={handleProductSubmit} className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Name</label>
              <input
                required
                value={productForm.name}
                onChange={(event) =>
                  setProductForm((current) => ({ ...current, name: event.target.value }))
                }
                className="w-full rounded-xl border px-4 py-3 outline-none focus:border-orange-400"
                placeholder="Smoky Pepperoni Feast"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Price</label>
              <input
                required
                type="number"
                step="0.01"
                min="0"
                value={productForm.price}
                onChange={(event) =>
                  setProductForm((current) => ({ ...current, price: event.target.value }))
                }
                className="w-full rounded-xl border px-4 py-3 outline-none focus:border-orange-400"
                placeholder="12.50"
              />
            </div>

            <div>
              <label className="block text-sm font-medium text-gray-700 mb-1">Category</label>
              <select
                required
                value={productForm.category}
                onChange={(event) =>
                  setProductForm((current) => ({ ...current, category: event.target.value }))
                }
                className="w-full rounded-xl border px-4 py-3 outline-none focus:border-orange-400"
              >
                <option value="">Select category</option>
                {MENU_CATEGORIES.map((category) => (
                  <option key={category} value={category}>
                    {category}
                  </option>
                ))}
              </select>
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Description</label>
              <textarea
                rows={4}
                value={productForm.description}
                onChange={(event) =>
                  setProductForm((current) => ({ ...current, description: event.target.value }))
                }
                className="w-full rounded-xl border px-4 py-3 outline-none focus:border-orange-400"
                placeholder="Short, persuasive product description."
              />
            </div>

            <div className="md:col-span-2">
              <label className="block text-sm font-medium text-gray-700 mb-1">Image</label>
              <input
                type="file"
                accept="image/*"
                onChange={(event) =>
                  setProductForm((current) => ({
                    ...current,
                    file: event.target.files?.[0] || null,
                  }))
                }
                className="w-full rounded-xl border px-4 py-3 outline-none focus:border-orange-400"
              />
            </div>

            <div className="md:col-span-2">
              <button
                type="submit"
                disabled={savingProduct}
                className="w-full rounded-xl bg-orange-500 hover:bg-orange-600 text-white px-4 py-3 font-semibold disabled:opacity-60"
              >
                {savingProduct
                  ? 'Saving...'
                  : editingProductId
                    ? 'Save product changes'
                    : 'Publish product'}
              </button>
            </div>
          </form>
        </article>

        <article className="bg-white rounded-3xl shadow-sm p-6">
          <div className="flex flex-wrap items-center justify-between gap-4 mb-5">
            <div>
              <p className="uppercase tracking-[0.25em] text-xs text-orange-500 mb-2">Live menu</p>
              <h2 className="text-2xl font-bold">Products</h2>
            </div>
            <input
              type="search"
              value={productSearch}
              onChange={(event) => setProductSearch(event.target.value)}
              placeholder="Search by name, category or description"
              className="w-full md:w-80 rounded-xl border px-4 py-3 outline-none focus:border-orange-400"
            />
          </div>

          {visibleProducts.length === 0 ? (
            <div className="rounded-2xl border border-dashed p-8 text-center text-gray-500">
              No products match the current filter.
            </div>
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              {visibleProducts.map((product) => (
                <article key={product.id} className="overflow-hidden rounded-2xl border">
                  <img
                    src={product.image_url ? buildApiUrl(product.image_url) : PLACEHOLDER_IMAGE}
                    alt={product.name}
                    className="h-40 w-full object-cover"
                    onError={(event) => {
                      event.currentTarget.src = PLACEHOLDER_IMAGE;
                    }}
                  />
                  <div className="p-4 space-y-3">
                    <div className="flex items-start justify-between gap-4">
                      <div>
                        <h3 className="font-semibold text-lg">{product.name}</h3>
                        <p className="text-sm text-gray-500">{product.category}</p>
                      </div>
                      <span className="text-lg font-bold text-orange-600">
                        EUR {Number(product.price).toFixed(2)}
                      </span>
                    </div>
                    <p className="text-sm text-gray-600 min-h-[2.5rem]">
                      {product.description || 'No description yet.'}
                    </p>
                    <div className="flex gap-2">
                      <button
                        onClick={() => startEditingProduct(product)}
                        className="flex-1 rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-gray-50"
                      >
                        Edit
                      </button>
                      <button
                        onClick={() => handleDeleteProduct(product.id)}
                        className="flex-1 rounded-xl bg-red-50 text-red-600 px-4 py-2 text-sm font-semibold hover:bg-red-100"
                      >
                        Delete
                      </button>
                    </div>
                  </div>
                </article>
              ))}
            </div>
          )}
        </article>
      </section>

      {metrics && (
        <section className="grid grid-cols-1 md:grid-cols-4 gap-4">
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="text-xs text-gray-500">Requests</p>
            <p className="text-2xl font-bold">{metrics.total_requests}</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="text-xs text-gray-500">Errors (5xx)</p>
            <p className="text-2xl font-bold text-red-600">{metrics.total_errors}</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="text-xs text-gray-500">Avg latency</p>
            <p className="text-2xl font-bold">{metrics.average_latency_ms.toFixed(1)} ms</p>
          </div>
          <div className="bg-white rounded-2xl shadow-sm p-4">
            <p className="text-xs text-gray-500">In flight</p>
            <p className="text-2xl font-bold">{metrics.in_flight_requests}</p>
          </div>
        </section>
      )}

      {opsStatus && (
        <section className="bg-white rounded-3xl shadow-sm p-6">
          <div className="flex flex-wrap items-center justify-between gap-3 mb-4">
            <h2 className="text-2xl font-bold">Operational status</h2>
            <span
              className={`px-3 py-1 rounded-full text-sm font-semibold ${
                opsStatus.status === 'green'
                  ? 'bg-emerald-100 text-emerald-700'
                  : opsStatus.status === 'yellow'
                    ? 'bg-amber-100 text-amber-700'
                    : 'bg-red-100 text-red-700'
              }`}
            >
              {opsStatus.status.toUpperCase()}
            </span>
          </div>
          <p className="text-sm text-gray-600 mb-4">
            Error rate: {opsStatus.stats.error_rate_percent.toFixed(2)}% · Print failures:{' '}
            {opsStatus.stats.print_failures}
          </p>
          {opsStatus.recent_critical_events.length > 0 ? (
            <div className="space-y-3">
              {opsStatus.recent_critical_events.slice(0, 5).map((event, index) => (
                <div key={`${event.timestamp}-${index}`} className="rounded-2xl border p-3 text-sm">
                  <p className="font-semibold text-gray-900">{event.event}</p>
                  <p className="text-gray-600">{event.detail}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(event.timestamp).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No critical events recorded.</p>
          )}
        </section>
      )}

      {auditEvents && (
        <section className="bg-white rounded-3xl shadow-sm p-6">
          <h2 className="text-2xl font-bold mb-4">Recent audit events</h2>
          {auditEvents.events.length > 0 ? (
            <div className="space-y-3">
              {auditEvents.events.map((event, index) => (
                <div key={`${event.timestamp}-${index}`} className="rounded-2xl border p-3 text-sm">
                  <p className="font-semibold text-gray-900">{event.event}</p>
                  <p className="text-gray-600">{event.detail}</p>
                  <p className="text-xs text-gray-400 mt-1">
                    {new Date(event.timestamp).toLocaleString()}
                  </p>
                </div>
              ))}
            </div>
          ) : (
            <p className="text-sm text-gray-500">No audit events available.</p>
          )}
        </section>
      )}

      <section className="space-y-4">
        <div>
          <p className="uppercase tracking-[0.25em] text-xs text-orange-500 mb-2">Kitchen flow</p>
          <h2 className="text-2xl font-bold">Orders</h2>
        </div>

        {orders.length === 0 ? (
          <div className="bg-white rounded-3xl shadow-sm p-12 text-center text-gray-500">
            No orders yet.
          </div>
        ) : (
          <div className="space-y-4">
            {orders.map((order) => {
              const currentStatus = String(order.status || 'created').toLowerCase();
              const allowedStatuses = [currentStatus, ...(ORDER_STATUS_TRANSITIONS[currentStatus] || [])];

              return (
                <article key={order.id} className="bg-white rounded-3xl shadow-sm p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4 mb-4">
                    <div>
                      <h3 className="text-xl font-bold">Order #{order.id}</h3>
                      <p className="text-sm text-gray-500">
                        {order.items.length} item{order.items.length !== 1 ? 's' : ''}
                      </p>
                    </div>
                    <div className="text-right">
                      <span
                        className={`px-3 py-1 rounded-full text-sm font-medium ${
                          STATUS_COLORS[order.status] || 'bg-gray-100'
                        }`}
                      >
                        {order.status}
                      </span>
                      <p className="text-lg font-bold mt-2">EUR {Number(order.total_price).toFixed(2)}</p>
                    </div>
                  </div>

                  <div className="border-t pt-4 mb-4 space-y-2">
                    {order.items.map((item) => (
                      <div key={item.id} className="flex justify-between text-sm">
                        <span>
                          {item.quantity}x {item.product_name}
                          {item.extras ? ` · ${item.extras}` : ''}
                        </span>
                        <span>EUR {Number(item.price).toFixed(2)}</span>
                      </div>
                    ))}
                  </div>

                  <div className="flex flex-col lg:flex-row gap-3 lg:items-center lg:justify-between">
                    <div className="flex flex-wrap items-center gap-3">
                      <select
                        value={currentStatus}
                        onChange={(event) => handleStatusChange(order.id, event.target.value)}
                        className="rounded-xl border px-4 py-2 text-sm outline-none focus:border-orange-400"
                      >
                        {allowedStatuses.map((status, index) => (
                          <option key={`${order.id}-${status}-${index}`} value={status}>
                            {status}
                          </option>
                        ))}
                      </select>
                      <button
                        onClick={() => handleReprint(order.id)}
                        className="rounded-xl border px-4 py-2 text-sm font-semibold hover:bg-gray-50"
                      >
                        Reprint ticket
                      </button>
                    </div>

                    {order.print_jobs.length > 0 && (
                      <div className="flex flex-wrap gap-2">
                        {order.print_jobs.map((job) => (
                          <span
                            key={job.id}
                            className={`px-3 py-1 rounded-full text-xs font-medium ${
                              STATUS_COLORS[job.status] || 'bg-gray-100'
                            }`}
                          >
                            Print #{job.id} · {job.status}
                          </span>
                        ))}
                      </div>
                    )}
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </section>
    </div>
  );
}
