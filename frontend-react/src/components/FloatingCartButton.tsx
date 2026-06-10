import { useCart } from '../hooks/useCart';

interface FloatingCartButtonProps {
  onClick: () => void;
}

export function FloatingCartButton({ onClick }: FloatingCartButtonProps) {
  const { itemCount, getTotal } = useCart();

  return (
    <button
      type="button"
      onClick={onClick}
      className="fixed bottom-4 right-4 z-30 inline-flex items-center gap-2 rounded-2xl border border-amber-200/70 bg-slate-950/90 px-3.5 py-2.5 text-white shadow-xl shadow-black/25 backdrop-blur transition-transform hover:-translate-y-0.5 hover:bg-slate-900 focus:outline-none focus:ring-4 focus:ring-amber-300 dark:border-amber-400/30 sm:bottom-5 sm:right-5"
      aria-label={`Open basket${itemCount ? ` with ${itemCount} items` : ''}`}
    >
      <span className="relative grid h-8 w-8 place-items-center rounded-xl bg-amber-500 text-lg shadow-inner shadow-amber-200/20" aria-hidden="true">
        🛒
        {itemCount > 0 && (
          <span className="absolute -right-2 -top-2 flex h-5 min-w-5 items-center justify-center rounded-full bg-red-600 px-1 text-[10px] font-bold text-white ring-2 ring-slate-950">
            {itemCount}
          </span>
        )}
      </span>
      <span className="hidden leading-tight sm:block">
        <span className="block text-[11px] font-semibold uppercase tracking-wide text-amber-200">Basket</span>
        <span className="block text-sm font-bold">
          {itemCount > 0 ? `€${getTotal().toFixed(2)}` : 'Empty'}
        </span>
      </span>
      <span className="sr-only">{itemCount > 0 ? `Total €${getTotal().toFixed(2)}` : 'Basket empty'}</span>
    </button>
  );
}
