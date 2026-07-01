import { useState } from 'react';
import type { SyntheticEvent } from 'react';
import { buildApiUrl } from '../services/api';
import { getPlaceholderForCategory } from '../utils/productImages';

type ProductImageProps = {
  src?: string | null;
  alt: string;
  category?: string | null;
  className?: string;
  loading?: 'eager' | 'lazy';
  onImageError?: (event: SyntheticEvent<HTMLImageElement>) => void;
};

export function ProductImage({
  src,
  alt,
  category,
  className,
  loading = 'lazy',
  onImageError,
}: ProductImageProps) {
  const fallbackSrc = getPlaceholderForCategory(category);
  const productSrc = src ? buildApiUrl(src) : null;
  const [failedProductSrc, setFailedProductSrc] = useState<string | null>(null);
  const imageSrc =
    productSrc && failedProductSrc !== productSrc ? productSrc : fallbackSrc;

  const handleError = (event: SyntheticEvent<HTMLImageElement>) => {
    if (imageSrc === fallbackSrc) return;

    setFailedProductSrc(productSrc);
    onImageError?.(event);
  };

  return (
    <img
      src={imageSrc}
      alt={alt}
      className={className}
      loading={loading}
      onError={handleError}
    />
  );
}
