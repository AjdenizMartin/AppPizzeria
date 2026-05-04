import { useEffect, useState } from 'react';
import { useSearchParams } from 'react-router-dom';
import { orderService } from '../services/api';
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

  const fetchTracking = async () => {
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
  };

  useEffect(() => {
    if (!order) {
      return;
    }
    const interval = setInterval(fetchTracking, 30000);
    return () => clearInterval(interval);
  }, [order, orderId, email, phone]);

  return (
    <div className="max-w-3xl mx-auto space-y-6">
      <h1 className="text-3xl font-bold">Track your order</h1>
      <div className="bg-white rounded-xl shadow-sm p-6 space-y-4">
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <input
            placeholder="Order ID"
            value={orderId}
            onChange={(event) => setOrderId(event.target.value)}
            className="px-4 py-2 border rounded-lg"
          />
          <input
            placeholder="Email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="px-4 py-2 border rounded-lg"
          />
          <input
            placeholder="Phone"
            value={phone}
            onChange={(event) => setPhone(event.target.value)}
            className="px-4 py-2 border rounded-lg"
          />
        </div>
        <button
          onClick={fetchTracking}
          disabled={loading}
          className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-2 rounded-lg"
        >
          {loading ? 'Loading...' : 'Track order'}
        </button>
        {error && <div className="text-red-600 text-sm">{error}</div>}
      </div>

      {order && (
        <div className="space-y-4">
          <h2 className="text-xl font-semibold">
            Order #{order.id} · {toVisualStatus(order.status)}
          </h2>
          <ReceiptDisplay order={order} businessName="Pizzeria App" />
        </div>
      )}
    </div>
  );
}
