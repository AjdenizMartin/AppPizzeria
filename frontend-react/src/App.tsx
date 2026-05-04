import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { BrowserRouter, Routes, Route, useNavigate } from 'react-router-dom';
import { Navbar } from './components/Navbar';
import { CartDrawer } from './components/CartDrawer';
import { AuthModal } from './components/AuthModal';
import { AdminAuthModal } from './components/AdminAuthModal';
import { HomePage } from './pages/HomePage';
import { CheckoutPage } from './pages/CheckoutPage';
import { OrderConfirmationPage } from './pages/OrderConfirmationPage';
import { AdminPage } from './pages/AdminPage';
import { OrderTrackingPage } from './pages/OrderTrackingPage';
import { useAuth } from './hooks/useAuth';
import './index.css';

function AdminAccessRequired({ onAuthClick }: { onAuthClick: () => void }) {
  return (
    <div className="max-w-xl mx-auto text-center py-12">
      <p className="text-5xl mb-4">🔐</p>
      <h1 className="text-2xl font-bold mb-2">Admin access required</h1>
      <p className="text-gray-600 mb-6">
        Sign in with an administrator account to access the control panel.
      </p>
      <button
        onClick={onAuthClick}
        className="bg-amber-500 hover:bg-amber-600 text-white px-6 py-3 rounded-lg font-semibold transition-colors"
      >
        Sign in as admin
      </button>
    </div>
  );
}

function AppContent() {
  const [cartOpen, setCartOpen] = useState(false);
  const [authOpen, setAuthOpen] = useState(false);
  const [adminAuthOpen, setAdminAuthOpen] = useState(false);
  const { isAdmin } = useAuth();
  const navigate = useNavigate();

  const handleImageError = (e: SyntheticEvent<HTMLImageElement>) => {
    e.currentTarget.src = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
      '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" fill="%23f4ede2"><rect width="400" height="300"/><text x="50%" y="50%" font-family="Arial" font-size="24" fill="%235f4336" text-anchor="middle" dy=".3em">Pizzeria</text></svg>'
    );
  };

  return (
    <div className="min-h-screen bg-gray-50">
      <Navbar
        onCartClick={() => setCartOpen(true)}
        onAuthClick={() => setAuthOpen(true)}
        onAdminClick={() => navigate('/admin')}
      />
      <main className="max-w-7xl mx-auto px-4 py-8">
        <Routes>
          <Route path="/" element={<HomePage onImageError={handleImageError} />} />
          <Route path="/checkout" element={<CheckoutPage />} />
          <Route path="/order-confirmation/:orderId" element={<OrderConfirmationPage />} />
          <Route path="/order-tracking" element={<OrderTrackingPage />} />
          <Route
            path="/admin"
            element={
              isAdmin ? (
                <AdminPage />
              ) : (
                <AdminAccessRequired onAuthClick={() => setAdminAuthOpen(true)} />
              )
            }
          />
        </Routes>
      </main>

      <CartDrawer
        isOpen={cartOpen}
        onClose={() => setCartOpen(false)}
        onCheckout={() => navigate('/checkout')}
      />

      <AuthModal isOpen={authOpen} onClose={() => setAuthOpen(false)} />
      <AdminAuthModal isOpen={adminAuthOpen} onClose={() => setAdminAuthOpen(false)} />
    </div>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppContent />
    </BrowserRouter>
  );
}
