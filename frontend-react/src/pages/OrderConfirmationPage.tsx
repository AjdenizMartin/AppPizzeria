import { useEffect, useState } from 'react';
import { useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { orderService } from '../services/api';
import type { Order } from '../types';
import { ReceiptDisplay } from '../components/ReceiptDisplay';

export function OrderConfirmationPage() {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const paymentMethod = searchParams.get('method') || 'card';
  const [order, setOrder] = useState<Order | null>(null);
  const [error, setError] = useState('');

  const email =
    searchParams.get('email') || localStorage.getItem('pizzeria_last_order_contact_email') || '';
  const phone =
    searchParams.get('phone') || localStorage.getItem('pizzeria_last_order_contact_phone') || '';

  useEffect(() => {
    async function loadOrder() {
      if (!orderId) {
        return;
      }
      try {
        const tracked = await orderService.getTracking(Number(orderId), {
          email: email || undefined,
          phone: phone || undefined,
        });
        setOrder(tracked);
        localStorage.removeItem('pizzeria_pending_order_id');
        localStorage.removeItem('pizzeria_cart');
      } catch {
        setError('Order created, but details are not available yet.');
      }
    }
    loadOrder();
  }, [orderId, email, phone]);

  return (
    <div className="max-w-2xl mx-auto py-12 space-y-6">
      <div className="text-center">
        <div className="text-6xl mb-6">🎉</div>
        <h1 className="text-2xl font-bold mb-2">Order Confirmed</h1>
        <p className="text-gray-600">Order #{orderId}</p>
      </div>

      <div className="bg-green-50 border border-green-200 rounded-lg p-4">
        <p className="text-green-800">
          {paymentMethod === 'cash'
            ? 'Cash order received and sent to kitchen.'
            : 'Card payment successful and order sent to kitchen.'}
        </p>
      </div>

      {error && <div className="bg-amber-50 text-amber-700 p-4 rounded-lg">{error}</div>}

      {order && (
        <div className="space-y-4">
          <ReceiptDisplay order={order} businessName="Pizzeria App" />
          <p className="text-sm text-gray-500">
            Estimated delivery: 25-35 minutes (may vary during busy periods)
          </p>
          <button
            onClick={() =>
              navigate(
                `/order-tracking?orderId=${order.id}&email=${encodeURIComponent(email)}&phone=${encodeURIComponent(phone)}`
              )
            }
            className="bg-gray-900 hover:bg-gray-800 text-white px-4 py-2 rounded-lg"
          >
            Track this order
          </button>
        </div>
      )}

      <button
        onClick={() => navigate('/')}
        className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
      >
        Back to menu
      </button>
    </div>
  );
}
