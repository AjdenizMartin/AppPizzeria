import pizzaPlaceholder from '../assets/placeholders/pizza-placeholder.png';
import gourmetPizzaPlaceholder from '../assets/placeholders/gourmet-pizza-placeholder.png';
import burgerPlaceholder from '../assets/placeholders/burger-placeholder.png';
import mealDealPlaceholder from '../assets/placeholders/meal-deal-placeholder.png';
import saucesPlaceholder from '../assets/placeholders/sauces-placeholder.png';
import dessertPlaceholder from '../assets/placeholders/dessert-placeholder.png';
import { buildCategoryPlaceholderImage } from './categoryPlaceholders';

export function getPlaceholderForCategory(category?: string | null): string {
  const normalized = category?.toLowerCase().trim() ?? '';

  if (normalized.includes('gourmet') && normalized.includes('pizza')) {
    return gourmetPizzaPlaceholder;
  }

  if (normalized.includes('pizza')) {
    return pizzaPlaceholder;
  }

  if (normalized.includes('burger')) {
    return burgerPlaceholder;
  }

  if (
    normalized.includes('meal') ||
    normalized.includes('deal') ||
    normalized.includes('combo') ||
    normalized.includes('family')
  ) {
    return mealDealPlaceholder;
  }

  if (normalized.includes('sauce') || normalized.includes('dip')) {
    return saucesPlaceholder;
  }

  if (
    normalized.includes('dessert') ||
    normalized.includes('cake') ||
    normalized.includes('sweet') ||
    normalized.includes('brownie')
  ) {
    return dessertPlaceholder;
  }

  return buildCategoryPlaceholderImage({
    name: category?.trim() || 'Menu Item',
    category: category ?? '',
  });
}
