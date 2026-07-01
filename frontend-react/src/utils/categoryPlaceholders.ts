type PlaceholderInput = {
  name: string;
  category: string;
};

type PlaceholderStyle = {
  from: string;
  to: string;
  accent: string;
  label: string;
};

const FALLBACK_STYLE: PlaceholderStyle = {
  from: '#5f4336',
  to: '#c26b15',
  accent: '#f4ede2',
  label: 'Freshly Made',
};

const CATEGORY_STYLES: Array<{ pattern: RegExp; style: PlaceholderStyle }> = [
  {
    pattern: /gourmet|pizza/i,
    style: { from: '#8f2d17', to: '#f59e0b', accent: '#fff3c4', label: 'Fresh Pizza' },
  },
  {
    pattern: /burger/i,
    style: { from: '#7c2d12', to: '#ea580c', accent: '#ffedd5', label: 'Fresh Burger' },
  },
  {
    pattern: /chip|side|garlic|extra/i,
    style: { from: '#854d0e', to: '#eab308', accent: '#fef3c7', label: 'Fresh Sides' },
  },
  {
    pattern: /drink|soft|coke|fanta|water|7\s*-?\s*up/i,
    style: { from: '#0f766e', to: '#38bdf8', accent: '#ccfbf1', label: 'Cold Drinks' },
  },
  {
    pattern: /meal|deal|combo/i,
    style: { from: '#991b1b', to: '#f97316', accent: '#fee2e2', label: 'Meal Deal' },
  },
  {
    pattern: /sauce/i,
    style: { from: '#7f1d1d', to: '#dc2626', accent: '#fee2e2', label: 'Sauces' },
  },
  {
    pattern: /dessert|sweet|cake|cookie/i,
    style: { from: '#7e22ce', to: '#ec4899', accent: '#fce7f3', label: 'Desserts' },
  },
];

function escapeSvgText(value: string) {
  return value
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;');
}

function getStyle(category: string) {
  return CATEGORY_STYLES.find((entry) => entry.pattern.test(category))?.style ?? FALLBACK_STYLE;
}

function getInitials(name: string) {
  const words = name.trim().split(/\s+/).filter(Boolean);
  const initials = words.slice(0, 2).map((word) => word[0]?.toUpperCase()).join('');
  return initials || 'PB';
}

export function buildCategoryPlaceholderImage({ name, category }: PlaceholderInput) {
  const style = getStyle(category);
  const safeName = escapeSvgText(name || style.label);
  const safeLabel = escapeSvgText(style.label);
  const initials = escapeSvgText(getInitials(name));

  const svg = `
    <svg xmlns="http://www.w3.org/2000/svg" width="640" height="420" viewBox="0 0 640 420">
      <defs>
        <linearGradient id="bg" x1="0" x2="1" y1="0" y2="1">
          <stop offset="0" stop-color="${style.from}"/>
          <stop offset="1" stop-color="${style.to}"/>
        </linearGradient>
        <radialGradient id="glow" cx="50%" cy="35%" r="65%">
          <stop offset="0" stop-color="${style.accent}" stop-opacity="0.95"/>
          <stop offset="1" stop-color="${style.accent}" stop-opacity="0"/>
        </radialGradient>
      </defs>
      <rect width="640" height="420" fill="url(#bg)"/>
      <circle cx="500" cy="60" r="160" fill="url(#glow)" opacity="0.55"/>
      <circle cx="98" cy="340" r="135" fill="${style.accent}" opacity="0.16"/>
      <rect x="46" y="44" width="548" height="332" rx="34" fill="#fffaf3" opacity="0.14"/>
      <circle cx="320" cy="168" r="82" fill="#fffaf3" opacity="0.9"/>
      <text x="320" y="190" text-anchor="middle" font-family="Arial, sans-serif" font-size="52" font-weight="800" fill="${style.from}">${initials}</text>
      <text x="320" y="286" text-anchor="middle" font-family="Arial, sans-serif" font-size="30" font-weight="800" fill="#fffaf3">${safeName}</text>
      <text x="320" y="324" text-anchor="middle" font-family="Arial, sans-serif" font-size="18" font-weight="700" letter-spacing="3" fill="#fffaf3" opacity="0.82">${safeLabel}</text>
    </svg>
  `;

  return `data:image/svg+xml;charset=UTF-8,${encodeURIComponent(svg)}`;
}
