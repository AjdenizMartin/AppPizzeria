interface CategoryFilterProps {
  categories: string[];
  selected: string | null;
  onSelect: (category: string | null) => void;
}

const CATEGORY_ICONS: Record<string, string> = {
  Pizzas: '🍕',
  Burgers: '🍔',
  'Burger Meals': '🍔',
  'Garlic Bread': '🥖',
  Chips: '🍟',
  Desserts: '🍰',
  'Soft Drinks': '🥤',
  Extras: '➕',
  Sauces: '🫙',
  Highlights: '⭐',
  'Gourmet Pizzas': '👨‍🍳',
  'Family Deals': '👨‍👩‍👧‍👦',
  'Meal Deals': '🎁',
};

export function CategoryFilter({ categories, selected, onSelect }: CategoryFilterProps) {
  return (
    <div className="flex gap-2 overflow-x-auto pb-2 scrollbar-hide">
      <button
        onClick={() => onSelect(null)}
        className={`px-4 py-2 rounded-full whitespace-nowrap transition-colors ${
          selected === null
            ? 'bg-amber-500 text-white'
            : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
        }`}
      >
        All
      </button>
      {categories.map((category) => (
        <button
          key={category}
          onClick={() => onSelect(category === selected ? null : category)}
          className={`px-4 py-2 rounded-full whitespace-nowrap transition-colors flex items-center gap-1 ${
            selected === category
              ? 'bg-amber-500 text-white'
              : 'bg-gray-100 text-gray-700 hover:bg-gray-200'
          }`}
        >
          <span>{CATEGORY_ICONS[category] || '🍽️'}</span>
          <span>{category}</span>
        </button>
      ))}
    </div>
  );
}
