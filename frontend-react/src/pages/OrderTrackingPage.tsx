import { useCallback, useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { orderService, restaurantService } from '../services/api';
import type { Order } from '../types';
import { ReceiptDisplay } from '../components/ReceiptDisplay';

function toVisualStatus(status: string) {
  const normalized = status.toLowerCase();
  if (normalized === 'created') return 'received';
  if (normalized === 'paid') return 'paid';
  if (normalized === 'accepted' || normalized === 'printing') return 'preparing';
  if (normalized === 'printed') return 'printed';
  if (normalized === 'ready') return 'ready';
  if (normalized === 'delivered') return 'delivered';
  if (normalized === 'cancelled') return 'cancelled';
  return normalized;
}

export function OrderTrackingPage() {
  const [searchParams] = useSearchParams();
  const [orderId, setOrderId] = useState(searchParams.get('orderId') || '');
  const [email, setEmail] = useState(searchParams.get('email') || '');
  const [phone, setPhone] = useState(searchParams.get('phone') || '');
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const [order, setOrder] = useState<Order | null>(null);
  const [restaurantName, setRestaurantName] = useState('Pizzeria');

  const fetchTracking = useCallback(async () => {
    if (!orderId.trim()) {
      setError('Order ID is required');
      return;
    }
    if (!email.trim() && !phone.trim()) {
      setError('Enter email or phone');
      return;
    }

    setLoading(true);
    setError('');
    try {
      const tracked = await orderService.getTracking(Number(orderId), {
        email: email.trim() || undefined,
        phone: phone.trim() || undefined,
      });
      setOrder(tracked);
    } catch {
      setError('Order not found');
      setOrder(null);
    } finally {
      setLoading(false);
    }
  }, [email, orderId, phone]);

  useEffect(() => {
    restaurantService.getPublicSettings().then((s) => setRestaurantName(s.restaurant_name)).catch(() => {});
  }, []);

  useEffect(() => {
    if (!order) {
      return;
    }
    const interval = setInterval(fetchTracking, 30000);
    return () => clearInterval(interval);
  }, [order, fetchTracking]);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Track your order</h1>
      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            placeholder="Order ID"
            value={orderId}
            onChange={(event) => setOrderId(event.target.value)}
            className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded-lg placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
          <input
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded-lg placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
          <input
            placeholder="Phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className="px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded-lg placeholder:text-slate-400 dark:placeholder:text-slate-500"
          />
        </div>
        <button
          onClick={fetchTracking}
          disabled={loading}
          className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-2 rounded-lg"
        >
          {loading ? 'Loading...' : 'Track order'}
        </button>
        {error && <div className="text-red-600 dark:text-red-300 text-sm">{error}</div>}
      </div>

      {order && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">
            Order #{order.id} · {toVisualStatus(order.status)}
          </h2>
          <ReceiptDisplay order={order} businessName={restaurantName} />
          <div className="bg-white dark:bg-slate-900 rounded-xl shadow-sm border border-slate-200 dark:border-slate-700 p-4">
            <h3 className="font-semibold mb-3">Timeline</h3>
            <div className="space-y-2 text-sm">
              {(order.status_events && order.status_events.length > 0
                ? order.status_events
                : [{ created_at: order.created_at, status: order.status, label: toVisualStatus(order.status) }]
              ).map((event, idx) => (
                <div key={`track-evt-${idx}`} className="flex items-center justify-between rounded-lg bg-gray-50 dark:bg-slate-800 px-3 py-2">
                  <span>{event.label || toVisualStatus(event.status || event.new_status || order.status)}</span>
                  <span className="text-gray-500 dark:text-slate-400">{new Date(event.created_at).toLocaleString()}</span>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}
