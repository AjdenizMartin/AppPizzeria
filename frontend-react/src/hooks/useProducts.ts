import { useState, useEffect, useCallback } from 'react';
import type { Product } from '../types';
import { productService } from '../services/api';

export function useProducts() {
  const [products, setProducts] = useState<Product[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchProducts = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const data = await productService.getAll();
      setProducts(data);
    } catch (err: unknown) {
      const message = err instanceof Error ? err.message : 'Failed to load products';
      setError(message);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    fetchProducts();
  }, [fetchProducts]);

  const getByCategory = useCallback(
    (category: string) => {
      return products.filter((p) => p.category === category);
    },
    [products]
  );

  const getCategories = useCallback(() => {
    const categories = new Set(products.map((p) => p.category));
    return Array.from(categories).sort();
  }, [products]);

  const search = useCallback(
    (query: string) => {
      const normalized = query.toLowerCase().trim();
      if (!normalized) return products;
      return products.filter(
        (p) =>
          p.name.toLowerCase().includes(normalized) ||
          p.description?.toLowerCase().includes(normalized) ||
          p.category.toLowerCase().includes(normalized)
      );
    },
    [products]
  );

  return {
    products,
    loading,
    error,
    getByCategory,
    getCategories,
    search,
    refresh: fetchProducts,
  };
}
