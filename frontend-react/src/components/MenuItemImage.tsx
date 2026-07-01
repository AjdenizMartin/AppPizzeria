import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { buildApiUrl } from '../services/api';
import { buildCategoryPlaceholderImage } from '../utils/categoryPlaceholders';

interface MenuItemImageProps {
  imageUrl: string | null;
  name: string;
  category: string;
  className: string;
  onImageError?: (event: SyntheticEvent<HTMLImageElement>) => void;
  loading?: 'eager' | 'lazy';
}

export function MenuItemImage({
  imageUrl,
  name,
  category,
  className,
  onImageError,
  loading = 'lazy',
}: MenuItemImageProps) {
  const [failedImageUrl, setFailedImageUrl] = useState<string | null>(null);
  const shouldUseProductImage = Boolean(imageUrl && failedImageUrl !== imageUrl);
  const src = shouldUseProductImage
    ? buildApiUrl(imageUrl as string)
    : buildCategoryPlaceholderImage({ name, category });

  const handleError = (event: SyntheticEvent<HTMLImageElement>) => {
    if (imageUrl) {
      setFailedImageUrl(imageUrl);
    }
    onImageError?.(event);
  };

  return (
    <img
      src={src}
      alt={name}
      className={className}
      loading={loading}
      onError={shouldUseProductImage ? handleError : undefined}
    />
  );
}
