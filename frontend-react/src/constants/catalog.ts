export const MENU_CATEGORIES = [
  'Highlights',
  'Gourmet Pizzas',
  'Family Deals',
  'Meal Deals',
  'Burger Meals',
  'Pizzas',
  'Garlic Bread',
  'Burgers',
  'Chips',
  'Extras',
  'Sauces',
  'Desserts',
  'Soft Drinks',
];

export const ORDER_STATUS_TRANSITIONS: Record<string, string[]> = {
  created: ['paid', 'cancelled'],
  pending: ['paid', 'cancelled'],
  paid: ['accepted', 'cancelled'],
  accepted: ['printing', 'failed', 'cancelled'],
  printing: ['printed', 'failed', 'accepted'],
  printed: ['ready', 'delivered'],
  ready: ['delivered'],
  failed: ['accepted', 'cancelled'],
  cancelled: [],
  delivered: [],
};
