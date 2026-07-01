import type { Product } from '../types';
import type { SyntheticEvent } from 'react';
import { useCart } from '../hooks/useCart';
import { MenuItemImage } from './MenuItemImage';

interface ProductCardProps {
  product: Product;
  onImageError?: (e: SyntheticEvent<HTMLImageElement>) => void;
}

export function ProductCard({ product, onImageError }: ProductCardProps) {
  const { addItem } = useCart();

  const handleAddToCart = () => {
    if (!product.is_available) return;
    addItem(product);
  };

  return (
    <div className="bg-[#fffaf3] dark:bg-slate-900 rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow border border-[#e8dbc8] dark:border-slate-700">
      <MenuItemImage
        imageUrl={product.image_url}
        name={product.name}
        category={product.category}
        className="w-full h-40 object-cover"
        onImageError={onImageError}
      />
      <div className="p-4">
        <h3 className="font-semibold text-lg text-gray-900 dark:text-slate-100">{product.name}</h3>
        <p className="text-gray-600 dark:text-slate-300 text-sm mt-1 line-clamp-2">
          {product.description || 'Delicious dish prepared with fresh ingredients.'}
        </p>
        <div className="flex items-center justify-between mt-4">
          <div>
            <span className="text-xl font-bold text-[#c26b15]">
              €{Number(product.price).toFixed(2)}
            </span>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{product.category}</p>
          </div>
          <button
            onClick={handleAddToCart}
            disabled={!product.is_available}
            className="bg-amber-500 hover:bg-amber-600 disabled:bg-gray-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {product.is_available ? 'Add' : 'Sold out'}
          </button>
        </div>
      </div>
    </div>
  );
}
