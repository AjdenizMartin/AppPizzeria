import { useState, useCallback, useEffect } from 'react';
import type { SyntheticEvent } from 'react';
import { useProducts } from '../hooks/useProducts';
import { useCart } from '../hooks/useCart';
import { ProductCard } from '../components/ProductCard';
import { PizzaGroupCard } from '../components/PizzaGroupCard';
import { PizzaSizeModal } from '../components/PizzaSizeModal';
import { CategoryFilter } from '../components/CategoryFilter';
import { restaurantService } from '../services/api';
import type { Product, RestaurantSettings } from '../types';
import {
  buildPublicMenuItems,
  menuItemMatchesQuery,
  type PizzaGroup,
} from '../utils/productGrouping';

interface HomePageProps {
  onImageError?: (e: SyntheticEvent<HTMLImageElement>) => void;
}

export function HomePage({ onImageError }: HomePageProps) {
  const { products, loading, error, getCategories } = useProducts();
  const { addItem } = useCart();
  const availableCount = products.filter((product) => product.is_available).length;
  const [selectedCategory, setSelectedCategory] = useState<string | null>(null);
  const [searchQuery, setSearchQuery] = useState('');
  const [settings, setSettings] = useState<RestaurantSettings | null>(null);
  const [selectedPizzaGroup, setSelectedPizzaGroup] = useState<PizzaGroup | null>(null);

  const categories = getCategories();
  const menuItems = buildPublicMenuItems(products);
  const filteredMenuItems = menuItems.filter((item) => {
    const matchesCategory =
      !selectedCategory ||
      (item.type === 'product'
        ? item.product.category === selectedCategory
        : item.group.category === selectedCategory);

    return matchesCategory && menuItemMatchesQuery(item, searchQuery);
  });

  const handleCategorySelect = useCallback((category: string | null) => {
    setSelectedCategory(category);
    setSearchQuery('');
  }, []);

  const handleSearch = useCallback((query: string) => {
    setSearchQuery(query);
    if (query) {
      setSelectedCategory(null);
    }
  }, []);

  const handleAddPizza = useCallback(
    (product: Product, quantity: number) => {
      addItem(product, quantity);
    },
    [addItem]
  );

  useEffect(() => {
    restaurantService.getPublicSettings().then(setSettings).catch(() => {});
  }, []);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-[400px]">
        <div className="text-center">
          <div className="animate-spin text-4xl mb-4">🍕</div>
          <p className="text-gray-600 dark:text-slate-300">Loading menu...</p>
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="text-center py-8">
        <p className="text-red-500 mb-4">{error}</p>
        <button
          onClick={() => window.location.reload()}
          className="text-amber-600 hover:text-amber-700"
        >
          Try again
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-6">
      <section className="rounded-2xl overflow-hidden shadow-lg border border-[#e6d9c7] dark:border-slate-700 bg-[#fdfaf5] dark:bg-slate-900">
        <div className="relative min-h-[220px] md:min-h-[300px]">
          <img
            src="/static/images/peperonni.jpg"
            alt="Pizzeria cover"
            className="absolute inset-0 h-full w-full object-cover"
          />
          <div className="absolute inset-0 bg-gradient-to-t from-black/75 via-black/35 to-transparent" />
          <div className="relative z-10 p-6 md:p-8 flex flex-col h-full justify-end">
            <div className="inline-flex items-center gap-2 self-start rounded-full bg-[#fff7eb]/95 px-3 py-1 text-sm text-[#a35f14] border border-[#f2e4cf] mb-3">
              <span>⭐ 4.7</span>
              <span>•</span>
              <span>{availableCount} items</span>
            </div>
            <h1 className="text-3xl md:text-5xl font-black text-white tracking-tight leading-tight [text-shadow:0_2px_14px_rgba(0,0,0,0.45)]">
              {settings?.restaurant_name || 'Pizzeria il Basilico'}
            </h1>
            <div className="mt-2 text-white/95 text-sm md:text-base flex flex-wrap items-center gap-x-3 gap-y-1 [text-shadow:0_1px_6px_rgba(0,0,0,0.4)]">
              <span>Min. €{Number(settings?.minimum_order_amount ?? 10).toFixed(2)}</span>
              <span>•</span>
              <span>Delivery €{Number(settings?.delivery_fee ?? 6).toFixed(2)}</span>
              <span>•</span>
              <span>{settings?.estimated_delivery_minutes ?? 35} min</span>
            </div>
          </div>
        </div>
      </section>

      <div className="flex flex-col md:flex-row gap-4">
        <div className="flex-1">
          <input
            type="search"
            placeholder="Search menu..."
            value={searchQuery}
            onChange={(e) => handleSearch(e.target.value)}
            className="w-full px-4 py-3 border border-[#d7c8b5] dark:border-slate-600 bg-[#fefcf9] dark:bg-[#0f172a] text-slate-900 dark:text-slate-100 rounded-xl focus:ring-2 focus:ring-amber-500 focus:border-amber-500 outline-none placeholder:text-slate-400 dark:placeholder:text-slate-500 shadow-sm"
          />
        </div>
      </div>

      <CategoryFilter
        categories={categories}
        selected={selectedCategory}
        onSelect={handleCategorySelect}
      />

      {filteredMenuItems.length === 0 ? (
        <div className="text-center py-12 text-gray-500 dark:text-slate-400">
          <p className="text-4xl mb-4">🔍</p>
          <p>No products found</p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-6">
          {filteredMenuItems.map((item) =>
            item.type === 'product' ? (
              <ProductCard
                key={item.product.id}
                product={item.product}
                onImageError={onImageError}
              />
            ) : (
              <PizzaGroupCard
                key={item.group.key}
                group={item.group}
                onAdd={setSelectedPizzaGroup}
                onImageError={onImageError}
              />
            )
          )}
        </div>
      )}

      {selectedPizzaGroup && (
        <PizzaSizeModal
          key={selectedPizzaGroup.key}
          group={selectedPizzaGroup}
          open
          onClose={() => setSelectedPizzaGroup(null)}
          onAddToCart={handleAddPizza}
        />
      )}
    </div>
  );
}
