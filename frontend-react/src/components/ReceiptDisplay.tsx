import type { Order } from '../types';

interface ReceiptDisplayProps {
  order: Order;
  businessName?: string;
}

export function ReceiptDisplay({ order, businessName = 'Pizzeria App' }: ReceiptDisplayProps) {
  const subtotal = order.items.reduce((sum, item) => sum + Number(item.price) * item.quantity, 0);

  return (
    <section className="bg-white rounded-xl shadow-sm p-6 space-y-4 print:shadow-none print:rounded-none print:p-2">
      <div className="flex items-center justify-between border-b pb-3">
        <div>
          <h3 className="text-xl font-bold">{businessName}</h3>
          <p className="text-xs text-gray-500">Order receipt</p>
        </div>
        <button
          onClick={() => window.print()}
          className="rounded-lg border px-3 py-2 text-sm font-semibold hover:bg-gray-50 print:hidden"
        >
          Print receipt
        </button>
      </div>

      <div className="text-sm grid grid-cols-1 md:grid-cols-2 gap-2">
        <p><span className="font-semibold">Order ID:</span> #{order.id}</p>
        <p><span className="font-semibold">Date:</span> {new Date(order.created_at).toLocaleString()}</p>
        <p><span className="font-semibold">Status:</span> {order.status}</p>
        <p><span className="font-semibold">Payment:</span> {order.payment_method}</p>
      </div>

      <div className="text-sm space-y-1 border-t pt-3">
        <p><span className="font-semibold">Customer:</span> {order.customer_name}</p>
        <p><span className="font-semibold">Email:</span> {order.customer_email || '-'}</p>
        <p><span className="font-semibold">Phone:</span> {order.customer_phone}</p>
        <p>
          <span className="font-semibold">Address:</span> {order.delivery_address}, {order.delivery_city}{' '}
          {order.delivery_postal_code}
        </p>
      </div>

      <div className="border-t pt-3 space-y-2 text-sm">
        {order.items.map((item) => (
          <div key={item.id} className="flex justify-between gap-3">
            <span>
              {item.quantity}x {item.product_name}
              {item.extras ? <span className="block text-xs text-gray-500">Extras: {item.extras}</span> : null}
            </span>
            <span>EUR {(Number(item.price) * item.quantity).toFixed(2)}</span>
          </div>
        ))}
      </div>

      <div className="border-t pt-3 text-sm space-y-1">
        <div className="flex justify-between"><span>Subtotal</span><span>EUR {subtotal.toFixed(2)}</span></div>
        <div className="flex justify-between"><span>Delivery fee</span><span>EUR {Number(order.delivery_fee).toFixed(2)}</span></div>
        <div className="flex justify-between font-bold text-base border-t pt-2"><span>Total</span><span>EUR {Number(order.total_price).toFixed(2)}</span></div>
      </div>

      {order.delivery_notes ? (
        <p className="text-sm border-t pt-3"><span className="font-semibold">Delivery notes:</span> {order.delivery_notes}</p>
      ) : null}
    </section>
  );
}
