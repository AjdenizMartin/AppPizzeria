import { Link } from 'react-router-dom';
import { useCart } from '../hooks/useCart';
import { useAuth } from '../hooks/useAuth';

interface NavbarProps {
  onCartClick: () => void;
  onAuthClick: () => void;
  onAdminClick: () => void;
}

export function Navbar({ onCartClick, onAuthClick, onAdminClick }: NavbarProps) {
  const { itemCount } = useCart();
  const { isAuthenticated, isAdmin, user } = useAuth();

  return (
    <nav className="bg-white shadow-md sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link to="/" className="flex items-center gap-2">
            <span className="text-2xl">🍕</span>
            <span className="text-xl font-bold text-amber-600">Pizzeria</span>
          </Link>

          <div className="flex items-center gap-4">
            {isAdmin && (
              <button
                onClick={onAdminClick}
                className="hidden sm:inline-flex items-center gap-2 px-4 py-2 rounded-lg bg-gray-900 text-white hover:bg-gray-800 transition-colors"
              >
                <span>Control Room</span>
              </button>
            )}

            <button
              onClick={onAuthClick}
              className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <span className="text-lg">👤</span>
              <span className="hidden sm:inline">
                {isAuthenticated ? (user?.full_name || user?.email) : 'Sign in'}
              </span>
            </button>

            <button
              onClick={onCartClick}
              className="relative p-2 rounded-lg hover:bg-gray-100 transition-colors"
            >
              <span className="text-xl">🛒</span>
              {itemCount > 0 && (
                <span className="absolute -top-1 -right-1 bg-amber-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
                  {itemCount}
                </span>
              )}
            </button>
          </div>
        </div>
      </div>
    </nav>
  );
}
