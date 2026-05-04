import { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../hooks/useCart';
import { useAuth } from '../hooks/useAuth';
import { orderService } from '../services/api';

export function CheckoutPage() {
  const navigate = useNavigate();
  const { items, getSubtotal, getTotal, deliveryFee, clearCart } = useCart();
  const { isAuthenticated } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'cash'>('card');

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-4xl mb-4">🛒</p>
        <p className="text-gray-600 mb-4">Your basket is empty</p>
        <button
          onClick={() => navigate('/')}
          className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-2 rounded-lg transition-colors"
        >
          Back to Menu
        </button>
      </div>
    );
  }

  const handleCheckout = async () => {
    setLoading(true);
    setError('');

    try {
      const orderPayload = {
        items: items.map((item) => ({
          product_id: item.id,
          quantity: item.quantity,
          extras: '',
        })),
      };

      if (paymentMethod === 'cash') {
        const result = await orderService.createCashCheckout(orderPayload);
        clearCart();
        navigate(`/order-confirmation/${result.order_id}?method=cash`);
      } else {
        const order = await orderService.create(orderPayload);
        const checkoutItems = items.map((item) => ({
          name: item.name,
          price: item.price,
          quantity: item.quantity,
        }));
        const { url } = await orderService.createCheckoutSession(checkoutItems, order.order_id);
        clearCart();
        window.location.href = url;
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : 'Checkout failed');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Checkout</h1>

      {!isAuthenticated && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-4 mb-6">
          <p className="text-amber-800">
            <span className="font-semibold">Guest checkout</span> - Your order details will be sent to your email.
          </p>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 text-red-600 rounded-lg">
          {error}
        </div>
      )}

      <div className="bg-white rounded-xl shadow-md p-6 mb-6">
        <h2 className="font-semibold mb-4">Order Summary</h2>
        <div className="space-y-3 mb-4">
          {items.map((item) => (
            <div key={item.id} className="flex justify-between text-sm">
              <span>{item.name} x{item.quantity}</span>
              <span>€{(item.price * item.quantity).toFixed(2)}</span>
            </div>
          ))}
        </div>
        <div className="border-t pt-4 space-y-2">
          <div className="flex justify-between text-gray-600">
            <span>Subtotal</span>
            <span>€{getSubtotal().toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-gray-600">
            <span>Delivery</span>
            <span>€{deliveryFee.toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-xl font-bold pt-2 border-t">
            <span>Total</span>
            <span>€{getTotal().toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="bg-white rounded-xl shadow-md p-6 mb-6">
        <h2 className="font-semibold mb-4">Payment Method</h2>
        <div className="space-y-3">
          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="radio"
              name="payment"
              value="card"
              checked={paymentMethod === 'card'}
              onChange={() => setPaymentMethod('card')}
              className="w-5 h-5 text-amber-500"
            />
            <span className="text-2xl">💳</span>
            <div>
              <p className="font-medium">Pay by Card</p>
              <p className="text-sm text-gray-500">Secure payment via Stripe</p>
            </div>
          </label>

          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 transition-colors">
            <input
              type="radio"
              name="payment"
              value="cash"
              checked={paymentMethod === 'cash'}
              onChange={() => setPaymentMethod('cash')}
              className="w-5 h-5 text-amber-500"
            />
            <span className="text-2xl">💵</span>
            <div>
              <p className="font-medium">Cash on Delivery</p>
              <p className="text-sm text-gray-500">Pay when your order arrives</p>
            </div>
          </label>
        </div>
      </div>

      <button
        onClick={handleCheckout}
        disabled={loading}
        className="w-full bg-amber-500 hover:bg-amber-600 text-white py-4 rounded-xl font-semibold text-lg transition-colors disabled:opacity-50"
      >
        {loading
          ? 'Processing...'
          : paymentMethod === 'cash'
            ? `Place order for €${getTotal().toFixed(2)}`
            : `Pay €${getTotal().toFixed(2)}`}
      </button>
    </div>
  );
}
