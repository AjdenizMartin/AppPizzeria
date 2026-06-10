import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useCart } from '../hooks/useCart';
import { useAuth } from '../hooks/useAuth';
import { orderService, restaurantService } from '../services/api';

export function CheckoutPage() {
  const navigate = useNavigate();
  const { items, getSubtotal, deliveryFee, clearCart } = useCart();
  const { isAuthenticated, user } = useAuth();
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [fulfillmentMethod, setFulfillmentMethod] = useState<'delivery' | 'collection'>('delivery');
  const [paymentMethod, setPaymentMethod] = useState<'card' | 'cash'>('card');
  const [customerName, setCustomerName] = useState(user?.full_name || '');
  const [customerEmail, setCustomerEmail] = useState(user?.email || '');
  const [customerPhone, setCustomerPhone] = useState(user?.phone || '');
  const [deliveryAddress, setDeliveryAddress] = useState(user?.address_line || '');
  const [deliveryCity, setDeliveryCity] = useState(user?.city || '');
  const [deliveryPostalCode, setDeliveryPostalCode] = useState(user?.postal_code || '');
  const [deliveryNotes, setDeliveryNotes] = useState('');
  const [fieldErrors, setFieldErrors] = useState<Record<string, string>>({});
  const [settings, setSettings] = useState<{
    delivery_fee: number;
    minimum_order_amount: number;
    is_accepting_orders: boolean;
    estimated_delivery_minutes: number;
    temporary_closed: boolean;
    temporary_closed_message: string | null;
  } | null>(null);
  const [statusMessage, setStatusMessage] = useState('');
  const activeDeliveryFee = fulfillmentMethod === 'delivery' ? Number(settings?.delivery_fee ?? deliveryFee) : 0;
  const orderTotal = getSubtotal() + activeDeliveryFee;

  useEffect(() => {
    if (!user) {
      return;
    }
    queueMicrotask(() => {
      setCustomerName((current) => current || user.full_name || '');
      setCustomerEmail((current) => current || user.email || '');
      setCustomerPhone((current) => current || user.phone || '');
      setDeliveryAddress((current) => current || user.address_line || '');
      setDeliveryCity((current) => current || user.city || '');
      setDeliveryPostalCode((current) => current || user.postal_code || '');
    });
  }, [user]);

  useEffect(() => {
    restaurantService.getPublicSettings().then(setSettings).catch(() => {});
    restaurantService.getStatus().then((s) => setStatusMessage(s.message)).catch(() => {});
    
  }, []);

  if (items.length === 0) {
    return (
      <div className="text-center py-12">
        <p className="text-4xl mb-4">🛒</p>
        <p className="text-gray-600 dark:text-slate-300 mb-4">Your basket is empty</p>
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

    const trimmed = {
      customerName: customerName.trim(),
      customerEmail: customerEmail.trim(),
      customerPhone: customerPhone.trim(),
      deliveryAddress: deliveryAddress.trim(),
      deliveryCity: deliveryCity.trim(),
      deliveryPostalCode: deliveryPostalCode.trim(),
      deliveryNotes: deliveryNotes.trim(),
    };

    const nextFieldErrors: Record<string, string> = {};
    if (!trimmed.customerName) nextFieldErrors.customerName = 'Full name is required.';
    if (!trimmed.customerEmail) nextFieldErrors.customerEmail = 'Email is required.';
    if (!trimmed.customerPhone) nextFieldErrors.customerPhone = 'Phone is required.';
    if (fulfillmentMethod === 'delivery' && !trimmed.deliveryAddress) {
      nextFieldErrors.deliveryAddress = 'Address is required.';
    }
    if (fulfillmentMethod === 'delivery' && !trimmed.deliveryCity) {
      nextFieldErrors.deliveryCity = 'City is required.';
    }
    if (fulfillmentMethod === 'delivery' && !trimmed.deliveryPostalCode) {
      nextFieldErrors.deliveryPostalCode = 'Postal code is required.';
    }
    if (trimmed.customerPhone && trimmed.customerPhone.length < 3) {
      nextFieldErrors.customerPhone = 'Phone must have at least 3 characters.';
    }
    if (trimmed.deliveryCity && trimmed.deliveryCity.length < 2) {
      nextFieldErrors.deliveryCity = 'City must have at least 2 characters.';
    }

    if (Object.keys(nextFieldErrors).length > 0) {
      setFieldErrors(nextFieldErrors);
      setError('Please review the highlighted fields.');
      setLoading(false);
      return;
    }
    setFieldErrors({});

    try {
      const orderPayload = {
        items: items.map((item) => ({
          product_id: item.id,
          quantity: item.quantity,
          extras: (item.extras || '').trim(),
        })),
        customer_name: trimmed.customerName,
        customer_email: trimmed.customerEmail,
        customer_phone: trimmed.customerPhone,
        fulfillment_method: fulfillmentMethod,
        delivery_address: fulfillmentMethod === 'delivery' ? trimmed.deliveryAddress : 'Collection',
        delivery_city: fulfillmentMethod === 'delivery' ? trimmed.deliveryCity : 'Store',
        delivery_postal_code: fulfillmentMethod === 'delivery' ? trimmed.deliveryPostalCode : 'N/A',
        delivery_notes: trimmed.deliveryNotes,
        payment_method: paymentMethod,
      };

      if (paymentMethod === 'cash') {
        const result = await orderService.createCashCheckout(orderPayload);
        localStorage.setItem('pizzeria_last_order_contact_email', customerEmail.trim());
        localStorage.setItem('pizzeria_last_order_contact_phone', customerPhone.trim());
        clearCart();
        navigate(
          `/order-confirmation/${result.order_id}?method=cash&email=${encodeURIComponent(customerEmail.trim())}&phone=${encodeURIComponent(customerPhone.trim())}`
        );
      } else {
        const order = await orderService.create(orderPayload);
        localStorage.setItem('pizzeria_last_order_contact_email', customerEmail.trim());
        localStorage.setItem('pizzeria_last_order_contact_phone', customerPhone.trim());
        const { url } = await orderService.createCheckoutSession(order.order_id);
        localStorage.setItem('pizzeria_pending_order_id', String(order.order_id));
        window.location.href = url;
      }
    } catch (err: unknown) {
      let message = 'Checkout failed';
      if (err && typeof err === 'object' && 'response' in err) {
        const detail = (err as { response?: { data?: { detail?: unknown } } }).response?.data?.detail;
        if (typeof detail === 'string') {
          message = detail;
        } else if (Array.isArray(detail)) {
          message = detail
            .map((item) => {
              if (item && typeof item === 'object' && 'msg' in item) {
                return String((item as { msg?: string }).msg);
              }
              return 'Invalid input field';
            })
            .join(' | ');
        }
      } else if (err instanceof Error) {
        message = err.message;
      }
      setError(`Payment/checkout error: ${message}. Your cart is still saved, please try again.`);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="max-w-2xl mx-auto">
      <h1 className="text-2xl font-bold mb-6">Checkout</h1>

      {!isAuthenticated && (
        <div className="bg-amber-50 dark:bg-amber-950/40 border border-amber-200 dark:border-amber-800 rounded-lg p-4 mb-6">
          <p className="text-amber-900 dark:text-amber-200">
            <span className="font-semibold">Guest checkout</span> - Your order details will be sent to your email.
          </p>
        </div>
      )}

      {error && (
        <div className="mb-4 p-3 bg-red-50 dark:bg-red-950/40 text-red-700 dark:text-red-300 rounded-lg">
          {error}
        </div>
      )}
      {settings && !settings.is_accepting_orders && (
        <div className="mb-4 p-3 bg-amber-50 text-amber-700 rounded-lg">
          The restaurant is not accepting orders right now.
        </div>
      )}
      {settings && settings.temporary_closed && (
        <div className="mb-4 p-3 bg-amber-50 text-amber-700 rounded-lg">
          {settings.temporary_closed_message || statusMessage || 'We are closed right now.'}
        </div>
      )}

      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-md border border-slate-200 dark:border-slate-700 p-6 mb-6">
        <h2 className="font-semibold mb-4">Order details</h2>
        <div className="grid grid-cols-2 gap-3 mb-5">
          <button
            type="button"
            onClick={() => setFulfillmentMethod('delivery')}
            className={`rounded-xl border px-4 py-3 text-left transition-colors ${
              fulfillmentMethod === 'delivery'
                ? 'border-amber-500 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-100'
                : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            <span className="block font-semibold">Delivery</span>
            <span className="text-sm text-gray-500 dark:text-slate-400">Bring it to my address</span>
          </button>
          <button
            type="button"
            onClick={() => setFulfillmentMethod('collection')}
            className={`rounded-xl border px-4 py-3 text-left transition-colors ${
              fulfillmentMethod === 'collection'
                ? 'border-amber-500 bg-amber-50 dark:bg-amber-950/40 text-amber-900 dark:text-amber-100'
                : 'border-slate-200 dark:border-slate-700 hover:bg-slate-50 dark:hover:bg-slate-800'
            }`}
          >
            <span className="block font-semibold">Collection</span>
            <span className="text-sm text-gray-500 dark:text-slate-400">I will collect in store</span>
          </button>
        </div>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          <label className="block">
            <span className="text-sm text-gray-700 dark:text-slate-200">Full name</span>
            <input
              required
              value={customerName}
              onChange={(event) => setCustomerName(event.target.value)}
              className={`mt-1 w-full px-4 py-2 border rounded-lg outline-none ${
                fieldErrors.customerName
                  ? 'border-red-400 focus:ring-2 focus:ring-red-200 focus:border-red-500'
                  : 'focus:ring-2 focus:ring-amber-500 focus:border-amber-500'
              }`}
            />
            {fieldErrors.customerName && <p className="mt-1 text-xs text-red-600">{fieldErrors.customerName}</p>}
          </label>
          <label className="block">
            <span className="text-sm text-gray-700 dark:text-slate-200">Email</span>
            <input
              required
              type="email"
              value={customerEmail}
              onChange={(event) => setCustomerEmail(event.target.value)}
              className={`mt-1 w-full px-4 py-2 border rounded-lg outline-none ${
                fieldErrors.customerEmail
                  ? 'border-red-400 focus:ring-2 focus:ring-red-200 focus:border-red-500'
                  : 'focus:ring-2 focus:ring-amber-500 focus:border-amber-500'
              }`}
            />
            {fieldErrors.customerEmail && <p className="mt-1 text-xs text-red-600">{fieldErrors.customerEmail}</p>}
          </label>
          <label className="block">
            <span className="text-sm text-gray-700 dark:text-slate-200">Phone</span>
            <input
              required
              value={customerPhone}
              onChange={(event) => setCustomerPhone(event.target.value)}
              className={`mt-1 w-full px-4 py-2 border rounded-lg outline-none ${
                fieldErrors.customerPhone
                  ? 'border-red-400 focus:ring-2 focus:ring-red-200 focus:border-red-500'
                  : 'focus:ring-2 focus:ring-amber-500 focus:border-amber-500'
              }`}
            />
            {fieldErrors.customerPhone && <p className="mt-1 text-xs text-red-600">{fieldErrors.customerPhone}</p>}
          </label>
          {fulfillmentMethod === 'delivery' && <label className="block md:col-span-2">
            <span className="text-sm text-gray-700 dark:text-slate-200">Address</span>
            <input
              required
              value={deliveryAddress}
              onChange={(event) => setDeliveryAddress(event.target.value)}
              className={`mt-1 w-full px-4 py-2 border rounded-lg outline-none ${
                fieldErrors.deliveryAddress
                  ? 'border-red-400 focus:ring-2 focus:ring-red-200 focus:border-red-500'
                  : 'focus:ring-2 focus:ring-amber-500 focus:border-amber-500'
              }`}
            />
            {fieldErrors.deliveryAddress && <p className="mt-1 text-xs text-red-600">{fieldErrors.deliveryAddress}</p>}
          </label>}
          {fulfillmentMethod === 'delivery' && <label className="block">
            <span className="text-sm text-gray-700 dark:text-slate-200">City</span>
            <input
              required
              value={deliveryCity}
              onChange={(event) => setDeliveryCity(event.target.value)}
              className={`mt-1 w-full px-4 py-2 border rounded-lg outline-none ${
                fieldErrors.deliveryCity
                  ? 'border-red-400 focus:ring-2 focus:ring-red-200 focus:border-red-500'
                  : 'focus:ring-2 focus:ring-amber-500 focus:border-amber-500'
              }`}
            />
            {fieldErrors.deliveryCity && <p className="mt-1 text-xs text-red-600">{fieldErrors.deliveryCity}</p>}
          </label>}
          {fulfillmentMethod === 'delivery' && <label className="block">
            <span className="text-sm text-gray-700 dark:text-slate-200">Postal code</span>
            <input
              required
              value={deliveryPostalCode}
              onChange={(event) => setDeliveryPostalCode(event.target.value)}
              className={`mt-1 w-full px-4 py-2 border rounded-lg outline-none ${
                fieldErrors.deliveryPostalCode
                  ? 'border-red-400 focus:ring-2 focus:ring-red-200 focus:border-red-500'
                  : 'focus:ring-2 focus:ring-amber-500 focus:border-amber-500'
              }`}
            />
            {fieldErrors.deliveryPostalCode && (
              <p className="mt-1 text-xs text-red-600">{fieldErrors.deliveryPostalCode}</p>
            )}
          </label>}
          <label className="block md:col-span-2">
            <span className="text-sm text-gray-700 dark:text-slate-200">
              {fulfillmentMethod === 'delivery' ? 'Delivery notes' : 'Collection notes'}
            </span>
            <textarea
              value={deliveryNotes}
              onChange={(event) => setDeliveryNotes(event.target.value)}
              className="mt-1 w-full px-4 py-2 border border-slate-300 dark:border-slate-600 bg-white dark:bg-slate-900 text-slate-900 dark:text-slate-100 rounded-lg focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none"
              rows={3}
            />
          </label>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-md border border-slate-200 dark:border-slate-700 p-6 mb-6">
        <h2 className="font-semibold mb-4">Order Summary</h2>
        <div className="space-y-3 mb-4">
          {items.map((item) => (
            <div key={item.id} className="flex justify-between text-sm gap-3">
              <span>
                {item.name} x{item.quantity}
                {item.extras ? <span className="block text-xs text-gray-500 dark:text-slate-400">Extras: {item.extras}</span> : null}
              </span>
              <span>€{(item.price * item.quantity).toFixed(2)}</span>
            </div>
          ))}
        </div>
        <div className="border-t pt-4 space-y-2">
          <div className="flex justify-between text-gray-600 dark:text-slate-300">
            <span>Subtotal</span>
            <span>€{getSubtotal().toFixed(2)}</span>
          </div>
          <div className="flex justify-between text-gray-600 dark:text-slate-300">
            <span>{fulfillmentMethod === 'delivery' ? 'Delivery' : 'Collection'}</span>
            <span>{fulfillmentMethod === 'delivery' ? `€${activeDeliveryFee.toFixed(2)}` : 'Free'}</span>
          </div>
          {settings && (
            <div className="flex justify-between text-gray-600 dark:text-slate-300">
              <span>Minimum order</span>
              <span>€{Number(settings.minimum_order_amount).toFixed(2)}</span>
            </div>
          )}
          <div className="flex justify-between text-xl font-bold pt-2 border-t">
            <span>Total</span>
            <span>€{orderTotal.toFixed(2)}</span>
          </div>
        </div>
      </div>

      <div className="bg-white dark:bg-slate-900 rounded-xl shadow-md border border-slate-200 dark:border-slate-700 p-6 mb-6">
        <h2 className="font-semibold mb-4">Payment Method</h2>
        <div className="space-y-3">
          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
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
              <p className="text-sm text-gray-500 dark:text-slate-400">Secure payment via Stripe</p>
            </div>
          </label>

          <label className="flex items-center gap-3 p-4 border rounded-lg cursor-pointer hover:bg-gray-50 dark:hover:bg-slate-800 transition-colors">
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
              <p className="font-medium">Cash</p>
              <p className="text-sm text-gray-500 dark:text-slate-400">
                {fulfillmentMethod === 'delivery' ? 'Pay when your order arrives' : 'Pay when you collect'}
              </p>
            </div>
          </label>
        </div>
      </div>

      <button
        onClick={handleCheckout}
        disabled={
          loading ||
          (settings ? !settings.is_accepting_orders || settings.temporary_closed : false)
        }
        className="w-full bg-amber-500 hover:bg-amber-600 text-white py-4 rounded-xl font-semibold text-lg transition-colors disabled:opacity-50"
      >
        {loading
          ? 'Processing...'
          : paymentMethod === 'cash'
            ? `Place order for €${orderTotal.toFixed(2)}`
            : `Pay €${orderTotal.toFixed(2)}`}
      </button>
    </div>
  );
}
