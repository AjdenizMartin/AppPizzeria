import { Link } from 'react-router-dom';
import { useCart } from '../hooks/useCart';
import { useAuth } from '../hooks/useAuth';
import { useTheme } from '../hooks/useTheme';

interface NavbarProps {
  onCartClick: () => void;
  onAuthClick: () => void;
  showCart?: boolean;
}

export function Navbar({ onCartClick, onAuthClick, showCart = true }: NavbarProps) {
  const { itemCount } = useCart();
  const { isAuthenticated, user } = useAuth();
  const { theme, toggleTheme } = useTheme();

  return (
    <nav className="bg-[#f6f0e7]/95 dark:bg-slate-900/95 backdrop-blur shadow-md sticky top-0 z-30 border-b border-[#e8dccb] dark:border-slate-700">
      <div className="max-w-7xl mx-auto px-4">
        <div className="flex items-center justify-between h-16">
          <Link
            to="/"
            className="inline-flex items-center gap-2 px-3 py-2 rounded-lg border border-[#dec9ac] dark:border-slate-600 text-[#9a5b15] dark:text-slate-100 hover:bg-[#efe1ce] dark:hover:bg-slate-800 transition-colors font-semibold"
          >
            <span aria-hidden="true">⌂</span>
            <span>Home</span>
          </Link>

          <div className="flex items-center gap-4">
            <div
              className="inline-flex items-center rounded-full border border-[#d6c4ab] dark:border-slate-600 bg-[#efe5d8] dark:bg-slate-800 p-1"
              role="group"
              aria-label="Theme switcher"
            >
              <button
                onClick={() => theme === 'dark' && toggleTheme()}
                className={`px-3 py-1.5 text-xs font-semibold rounded-full transition-colors ${
                  theme === 'light'
                    ? 'bg-[#fffdf9] dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
                aria-pressed={theme === 'light'}
              >
                Light
              </button>
              <button
                onClick={() => theme === 'light' && toggleTheme()}
                className={`px-3 py-1.5 text-xs font-semibold rounded-full transition-colors ${
                  theme === 'dark'
                    ? 'bg-[#fffdf9] dark:bg-slate-700 text-slate-900 dark:text-slate-100 shadow-sm'
                    : 'text-slate-600 dark:text-slate-300 hover:text-slate-900 dark:hover:text-slate-100'
                }`}
                aria-pressed={theme === 'dark'}
              >
                Dark
              </button>
            </div>
            <button
              onClick={onAuthClick}
              className="flex items-center gap-2 px-4 py-2 rounded-lg hover:bg-[#efe1ce] dark:hover:bg-slate-800 text-slate-900 dark:text-slate-100 transition-colors"
            >
              <span className="text-lg">👤</span>
              <span className="hidden sm:inline">
                {isAuthenticated ? (user?.full_name || user?.email) : 'Sign in'}
              </span>
            </button>

            {showCart && (
              <button
                onClick={onCartClick}
                className="relative p-2 rounded-lg hover:bg-[#efe1ce] dark:hover:bg-slate-800 text-slate-900 dark:text-slate-100 transition-colors"
              >
                <span className="text-xl">🛒</span>
                {itemCount > 0 && (
                  <span className="absolute -top-1 -right-1 bg-amber-500 text-white text-xs w-5 h-5 rounded-full flex items-center justify-center">
                    {itemCount}
                  </span>
                )}
              </button>
            )}
          </div>
        </div>
      </div>
    </nav>
  );
}
