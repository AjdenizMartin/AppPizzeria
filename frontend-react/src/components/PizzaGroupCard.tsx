import type { SyntheticEvent } from 'react';
import { buildApiUrl } from '../services/api';
import type { PizzaGroup } from '../utils/productGrouping';

interface PizzaGroupCardProps {
  group: PizzaGroup;
  onAdd: (group: PizzaGroup) => void;
  onImageError?: (e: SyntheticEvent<HTMLImageElement>) => void;
}

const PLACEHOLDER_IMAGE = 'data:image/svg+xml;charset=UTF-8,' + encodeURIComponent(
  '<svg xmlns="http://www.w3.org/2000/svg" width="400" height="300" fill="%23f4ede2"><rect width="400" height="300"/><text x="50%" y="50%" font-family="Arial" font-size="24" fill="%235f4336" text-anchor="middle" dy=".3em">Pizzeria</text></svg>'
);

export function PizzaGroupCard({ group, onAdd, onImageError }: PizzaGroupCardProps) {
  const { displayProduct } = group;

  return (
    <div className="bg-[#fffaf3] dark:bg-slate-900 rounded-xl shadow-md overflow-hidden hover:shadow-lg transition-shadow border border-[#e8dbc8] dark:border-slate-700">
      <img
        src={displayProduct.image_url ? buildApiUrl(displayProduct.image_url) : PLACEHOLDER_IMAGE}
        alt={group.name}
        className="w-full h-40 object-cover"
        onError={onImageError}
      />
      <div className="p-4">
        <h3 className="font-semibold text-lg text-gray-900 dark:text-slate-100">{group.name}</h3>
        <p className="text-gray-600 dark:text-slate-300 text-sm mt-1 line-clamp-2">
          {displayProduct.description || 'Delicious dish prepared with fresh ingredients.'}
        </p>
        <div className="flex items-center justify-between mt-4">
          <div>
            <span className="text-xl font-bold text-[#c26b15]">
              from €{group.fromPrice.toFixed(2)}
            </span>
            <p className="text-xs text-gray-500 dark:text-slate-400 mt-1">{group.category}</p>
          </div>
          <button
            onClick={() => onAdd(group)}
            disabled={!group.isAvailable}
            className="bg-amber-500 hover:bg-amber-600 disabled:bg-gray-300 dark:disabled:bg-slate-700 disabled:cursor-not-allowed text-white px-4 py-2 rounded-lg font-medium transition-colors"
          >
            {group.isAvailable ? 'Add' : 'Sold out'}
          </button>
        </div>
      </div>
    </div>
  );
}
