import { useState } from 'react';
import { MenuItemImage } from './MenuItemImage';
import type { Product } from '../types';
import type { PizzaGroup } from '../utils/productGrouping';

interface PizzaSizeModalProps {
  group: PizzaGroup | null;
  open: boolean;
  onClose: () => void;
  onAddToCart: (product: Product, quantity: number) => void;
}

export function PizzaSizeModal({ group, open, onClose, onAddToCart }: PizzaSizeModalProps) {
  const [selectedProductId, setSelectedProductId] = useState<number | null>(null);
  const [quantity, setQuantity] = useState(1);

  if (!open || !group) return null;

  const selectedOption = group.sizes.find((option) => option.product.id === selectedProductId);
  const addTotal = selectedOption ? Number(selectedOption.product.price) * quantity : 0;

  const handleAdd = () => {
    if (!selectedOption || !selectedOption.product.is_available) return;
    onAddToCart(selectedOption.product, quantity);
    onClose();
  };

  return (
    <div className="fixed inset-0 z-50 flex items-end justify-center bg-black/50 px-0 sm:items-center sm:px-4">
      <button
        type="button"
        className="absolute inset-0 cursor-default"
        aria-label="Close pizza size selector"
        onClick={onClose}
      />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="pizza-size-title"
        className="relative w-full max-h-[92vh] overflow-y-auto rounded-t-3xl bg-[#fffaf3] shadow-2xl dark:bg-slate-900 sm:max-w-lg sm:rounded-2xl border border-[#e8dbc8] dark:border-slate-700"
      >
        <div className="relative">
          <MenuItemImage
            imageUrl={group.displayProduct.image_url}
            name={group.name}
            category={group.category}
            className="h-48 w-full object-cover"
            loading="eager"
          />
          <button
            type="button"
            onClick={onClose}
            className="absolute right-3 top-3 grid h-9 w-9 place-items-center rounded-full bg-black/65 text-xl leading-none text-white transition-colors hover:bg-black/80 focus:outline-none focus:ring-2 focus:ring-white"
            aria-label="Close"
          >
            x
          </button>
        </div>

        <div className="space-y-5 p-5">
          <div>
            <p className="text-sm font-semibold text-[#c26b15]">from €{group.fromPrice.toFixed(2)}</p>
            <h2 id="pizza-size-title" className="mt-1 text-2xl font-black text-gray-900 dark:text-slate-100">
              {group.name}
            </h2>
            <p className="mt-2 text-sm text-gray-600 dark:text-slate-300">
              {group.displayProduct.description || 'Delicious pizza prepared with fresh ingredients.'}
            </p>
          </div>

          <div>
            <div className="mb-3 flex items-center justify-between">
              <h3 className="font-semibold text-gray-900 dark:text-slate-100">Choose size</h3>
              <span className="rounded-full bg-amber-100 px-2.5 py-1 text-xs font-bold text-amber-800 dark:bg-amber-500/20 dark:text-amber-200">
                1 Required
              </span>
            </div>

            <div className="space-y-2">
              {group.sizes.map((option) => {
                const disabled = !option.product.is_available;
                return (
                  <label
                    key={`${group.key}-${option.size}`}
                    className={`flex items-center justify-between rounded-xl border p-3 transition-colors ${
                      disabled
                        ? 'border-gray-200 bg-gray-100 text-gray-400 dark:border-slate-700 dark:bg-slate-800/60 dark:text-slate-500'
                        : 'cursor-pointer border-[#e0cfba] bg-[#fffdf9] text-gray-900 hover:border-amber-400 dark:border-slate-700 dark:bg-slate-950 dark:text-slate-100'
                    }`}
                  >
                    <span className="flex items-center gap-3">
                      <input
                        type="radio"
                        name="pizza-size"
                        value={option.product.id}
                        checked={selectedProductId === option.product.id}
                        disabled={disabled}
                        onChange={() => setSelectedProductId(option.product.id)}
                        className="h-4 w-4 accent-amber-500"
                      />
                      <span className="font-semibold">{option.size}</span>
                      {disabled && <span className="text-xs font-semibold">Sold out</span>}
                    </span>
                    <span className="font-bold">€{Number(option.product.price).toFixed(2)}</span>
                  </label>
                );
              })}
            </div>
          </div>

          <div className="flex items-center justify-between rounded-xl border border-[#e0cfba] bg-[#fffdf9] p-3 dark:border-slate-700 dark:bg-slate-950">
            <span className="font-semibold text-gray-900 dark:text-slate-100">Quantity</span>
            <div className="flex items-center gap-3">
              <button
                type="button"
                onClick={() => setQuantity((current) => Math.max(1, current - 1))}
                className="grid h-9 w-9 place-items-center rounded-full border border-[#dec9ac] text-lg font-bold text-[#9a5b15] transition-colors hover:bg-[#efe1ce] dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-800"
                aria-label="Decrease quantity"
              >
                -
              </button>
              <span className="w-8 text-center font-bold text-gray-900 dark:text-slate-100">{quantity}</span>
              <button
                type="button"
                onClick={() => setQuantity((current) => current + 1)}
                className="grid h-9 w-9 place-items-center rounded-full border border-[#dec9ac] text-lg font-bold text-[#9a5b15] transition-colors hover:bg-[#efe1ce] dark:border-slate-600 dark:text-slate-100 dark:hover:bg-slate-800"
                aria-label="Increase quantity"
              >
                +
              </button>
            </div>
          </div>

          <button
            type="button"
            onClick={handleAdd}
            disabled={!selectedOption || !selectedOption.product.is_available}
            className="w-full rounded-xl bg-amber-500 px-5 py-3 font-bold text-white transition-colors hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-gray-300 dark:disabled:bg-slate-700"
          >
            {selectedOption ? `Add €${addTotal.toFixed(2)}` : 'Choose a size'}
          </button>
        </div>
      </div>
    </div>
  );
}
