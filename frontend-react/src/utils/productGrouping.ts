import type { Product } from '../types';

const GROUPABLE_PIZZA_CATEGORIES = new Set(['Pizzas', 'Gourmet Pizzas']);
const EXCLUDED_NAME_PATTERN = /\b(meal|deal)\b/i;
const SIZE_PATTERN = /\s*(?:-\s*)?(09|9|12|16)\s*"\s*$/i;
const SIZE_ORDER: Record<string, number> = {
  '9"': 0,
  '12"': 1,
  '16"': 2,
};

export type PizzaSizeOption = {
  size: string;
  product: Product;
};

export type PizzaGroup = {
  key: string;
  category: string;
  name: string;
  sizes: PizzaSizeOption[];
  displayProduct: Product;
  fromPrice: number;
  isAvailable: boolean;
};

export type MenuItem =
  | { type: 'product'; product: Product }
  | { type: 'pizza-group'; group: PizzaGroup };

function normalizeSize(size: string) {
  return size === '09' ? '9"' : `${Number(size)}"`;
}

export function parsePizzaSize(product: Product): { baseName: string; size: string } | null {
  if (!GROUPABLE_PIZZA_CATEGORIES.has(product.category)) return null;
  if (EXCLUDED_NAME_PATTERN.test(product.name)) return null;

  const match = product.name.match(SIZE_PATTERN);
  if (!match) return null;

  const baseName = product.name.slice(0, match.index).trim();
  if (!baseName) return null;

  return {
    baseName,
    size: normalizeSize(match[1]),
  };
}

function chooseDisplayProduct(options: PizzaSizeOption[]) {
  return options.find((option) => option.product.is_available)?.product ?? options[0].product;
}

function getFromPrice(options: PizzaSizeOption[]) {
  const available = options.filter((option) => option.product.is_available);
  const source = available.length ? available : options;
  return Math.min(...source.map((option) => Number(option.product.price)));
}

function shouldReplaceDuplicate(current: Product, candidate: Product) {
  if (candidate.is_available !== current.is_available) {
    return candidate.is_available;
  }
  return candidate.id < current.id;
}

export function buildPublicMenuItems(products: Product[]): MenuItem[] {
  const groups = new Map<
    string,
    { firstIndex: number; baseName: string; category: string; sizes: Map<string, Product> }
  >();
  const normalItems: Array<{ index: number; item: MenuItem }> = [];

  products.forEach((product, index) => {
    const parsed = parsePizzaSize(product);
    if (!parsed) {
      normalItems.push({ index, item: { type: 'product', product } });
      return;
    }

    const key = `${product.category}::${parsed.baseName.toLowerCase()}`;
    const group = groups.get(key);
    if (!group) {
      groups.set(key, {
        firstIndex: index,
        baseName: parsed.baseName,
        category: product.category,
        sizes: new Map([[parsed.size, product]]),
      });
      return;
    }

    const existing = group.sizes.get(parsed.size);
    if (!existing || shouldReplaceDuplicate(existing, product)) {
      group.sizes.set(parsed.size, product);
    }
  });

  const groupItems = Array.from(groups.entries()).map(([key, group]) => {
    const sizes = Array.from(group.sizes.entries())
      .map(([size, product]) => ({ size, product }))
      .sort((a, b) => {
        const orderDiff = (SIZE_ORDER[a.size] ?? 99) - (SIZE_ORDER[b.size] ?? 99);
        return orderDiff || a.product.id - b.product.id;
      });
    const displayProduct = chooseDisplayProduct(sizes);

    return {
      index: group.firstIndex,
      item: {
        type: 'pizza-group' as const,
        group: {
          key,
          category: group.category,
          name: group.baseName,
          sizes,
          displayProduct,
          fromPrice: getFromPrice(sizes),
          isAvailable: sizes.some((option) => option.product.is_available),
        },
      },
    };
  });

  return [...normalItems, ...groupItems]
    .sort((a, b) => a.index - b.index)
    .map(({ item }) => item);
}

export function menuItemMatchesQuery(item: MenuItem, query: string) {
  const normalized = query.toLowerCase().trim();
  if (!normalized) return true;

  if (item.type === 'product') {
    const product = item.product;
    return (
      product.name.toLowerCase().includes(normalized) ||
      product.description?.toLowerCase().includes(normalized) ||
      product.category.toLowerCase().includes(normalized)
    );
  }

  const group = item.group;
  return (
    group.name.toLowerCase().includes(normalized) ||
    group.category.toLowerCase().includes(normalized) ||
    group.displayProduct.description?.toLowerCase().includes(normalized) ||
    group.sizes.some((option) => option.size.toLowerCase().includes(normalized))
  );
}
