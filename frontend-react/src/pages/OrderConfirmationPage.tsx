import { useParams, useSearchParams, useNavigate } from 'react-router-dom';

export function OrderConfirmationPage() {
  const { orderId } = useParams();
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const paymentMethod = searchParams.get('method') || 'card';

  return (
    <div className="max-w-md mx-auto text-center py-12">
      <div className="text-6xl mb-6">🎉</div>
      <h1 className="text-2xl font-bold mb-2">Order Confirmed!</h1>
      <p className="text-gray-600 mb-4">Order #{orderId}</p>
      
      <div className="bg-green-50 border border-green-200 rounded-lg p-4 mb-6">
        <p className="text-green-800">
          {paymentMethod === 'cash'
            ? 'Your cash order has been placed and is being prepared!'
            : 'Payment successful! Your order is being prepared.'}
        </p>
      </div>

      <div className="text-gray-600 mb-6">
        <p>You will receive an email confirmation shortly.</p>
        <p className="mt-2">Estimated delivery: 25-35 minutes</p>
      </div>

      <button
        onClick={() => navigate('/')}
        className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
      >
        Back to Menu
      </button>
    </div>
  );
}
