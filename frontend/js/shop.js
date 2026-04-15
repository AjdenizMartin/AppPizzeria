import { API_URL, apiRequest } from "./api.js";

const CATEGORY_ORDER = [
  "Highlights", "Gourmet Pizzas", "Family Deals", "Meal Deals",
  "Burger Meals", "Pizzas", "Garlic Bread", "Burgers",
  "Chips", "Extras", "Sauces", "Desserts", "Soft Drinks",
];

const menu = document.getElementById("menu");
const categoriesContainer = document.getElementById("categories");
const featuredGrid = document.getElementById("featured-grid");
const cartContainer = document.getElementById("cart-items");
const totalEl = document.getElementById("cart-total");
const countEl = document.getElementById("cart-count");
const floatingCartCountEl = document.getElementById("floating-cart-count");
const grandTotalEl = document.getElementById("cart-grand-total");
const cartEl = document.getElementById("cart");
const overlay = document.getElementById("overlay");
const searchInput = document.getElementById("search-input");
const heroProductCount = document.getElementById("hero-product-count");
const searchState = document.getElementById("search-state");

let products = [];
let cart = JSON.parse(localStorage.getItem("cart")) || [];
let selectedCategory = null;
let searchTerm = "";

function saveCart() {
  localStorage.setItem("cart", JSON.stringify(cart));
}

function getCategoryDescription(category) {
  const descriptions = {
    Highlights: "The fastest yes on the page: promos, hot items and visual best-sellers.",
    "Gourmet Pizzas": "Premium combinations with richer toppings and a higher perceived value.",
    "Family Deals": "Bundle-led picks for bigger groups and stronger average order value.",
    "Meal Deals": "Simple all-in combos designed for quick decisions.",
    "Burger Meals": "Comfort-food combos with a delivery-first feel.",
    Pizzas: "Classic crowd-pleasers that users expect to see instantly.",
    "Garlic Bread": "Easy add-ons that grow basket size with little friction.",
    Burgers: "Fast-moving handheld options for mixed-group orders.",
    Chips: "Side dishes that complete the order in one tap.",
    Extras: "Small boosters, sauces and side choices.",
    Sauces: "Quick add-ons right before checkout.",
    Desserts: "Sweet finishers that convert well at the end of the flow.",
    "Soft Drinks": "Low-friction extras for better cart completion.",
  };

  return descriptions[category] || "Freshly prepared items for tonight's service.";
}

function getProductBadge(category, index) {
  const categoryBadges = {
    Highlights: "Hot right now",
    "Family Deals": "Best value",
    Desserts: "Late-night treat",
    "Soft Drinks": "Easy add-on",
    "Gourmet Pizzas": "Premium pick",
  };

  return categoryBadges[category] || (index % 2 === 0 ? "Popular choice" : "Quick add");
}

function getProductMeta(category, price) {
  const eta = price >= 15 ? "25-30 min" : "20-25 min";
  const vibe = category === "Family Deals" || category === "Meal Deals" ? "Group order" : "Solo favourite";
  return { eta, vibe };
}

function getVisibleProducts() {
  return products.filter((product) => {
    const matchesCategory = !selectedCategory || product.category === selectedCategory;
    const normalizedSearch = searchTerm.trim().toLowerCase();
    const haystack = `${product.name} ${product.description || ""} ${product.category}`.toLowerCase();
    const matchesSearch = !normalizedSearch || haystack.includes(normalizedSearch);
    return matchesCategory && matchesSearch;
  });
}

function renderCategories() {
  const visibleCategories = CATEGORY_ORDER.filter((category) =>
    products.some((product) => product.category === category)
  );

  categoriesContainer.innerHTML = "";

  const allButton = document.createElement("button");
  allButton.textContent = "All";
  allButton.className = `category-chip ${selectedCategory === null ? "active" : ""}`;
  allButton.onclick = () => {
    selectedCategory = null;
    renderCategories();
    renderFeatured();
    renderMenu();
  };

  categoriesContainer.appendChild(allButton);

  visibleCategories.forEach((category) => {
    const button = document.createElement("button");
    button.textContent = category;
    button.className = `category-chip ${selectedCategory === category ? "active" : ""}`;
    button.onclick = () => {
      selectedCategory = selectedCategory === category ? null : category;
      renderCategories();
      renderFeatured();
      renderMenu();
      document.getElementById("menu-section").scrollIntoView({ behavior: "smooth", block: "start" });
    };

    categoriesContainer.appendChild(button);
  });
}

function renderFeatured() {
  const featuredProducts = getVisibleProducts().slice(0, 3);
  featuredGrid.innerHTML = "";

  if (!featuredProducts.length) {
    featuredGrid.innerHTML = `
      <div class="empty-state">
        No featured products match this search yet. Try another keyword or clear the category filter.
      </div>
    `;
    return;
  }

  featuredProducts.forEach((product, index) => {
    const { eta, vibe } = getProductMeta(product.category, product.price);
    const card = document.createElement("article");
    card.className = "featured-card";
    card.innerHTML = `
      <img src="${product.image_url ? `${API_URL}${product.image_url}` : "https://via.placeholder.com/600x400/f4ede2/5f4336?text=Pizzeria"}"
        alt="${product.name}">

      <div class="featured-card-body">
        <div class="featured-card-topline">
          <span class="badge">${getProductBadge(product.category, index)}</span>
          <span class="rating-pill">★ 4.${8 - (index % 2)}</span>
        </div>

        <h4>${product.name}</h4>
        <p>${product.description || "A strong visual seller built for fast food-delivery browsing."}</p>

        <div class="featured-card-footer">
          <div class="price-block">
            <strong>€${Number(product.price).toFixed(2)}</strong>
            <span>${eta} · ${vibe}</span>
          </div>
          <button data-product-id="${product.id}" class="add-to-cart">Add to basket</button>
        </div>
      </div>
    `;

    featuredGrid.appendChild(card);
  });
}

function renderMenu() {
  const visibleProducts = getVisibleProducts();
  menu.innerHTML = "";

  CATEGORY_ORDER.forEach((category) => {
    const filteredProducts = visibleProducts.filter((product) => product.category === category);

    if (!filteredProducts.length) {
      return;
    }

    const section = document.createElement("section");
    section.id = category;
    section.className = "menu-section-card";
    section.innerHTML = `
      <div class="menu-section-head">
        <div>
          <p class="eyebrow">${filteredProducts.length} items</p>
          <h3>${category}</h3>
          <p>${getCategoryDescription(category)}</p>
        </div>
        <span class="badge">${selectedCategory === category ? "Filtered" : "Open section"}</span>
      </div>
      <div class="menu-grid"></div>
    `;

    const grid = section.querySelector(".menu-grid");

    filteredProducts.forEach((product, index) => {
      const { eta, vibe } = getProductMeta(product.category, product.price);
      const card = document.createElement("article");
      card.className = "menu-card";
      card.innerHTML = `
        <img src="${product.image_url ? `${API_URL}${product.image_url}` : "https://via.placeholder.com/600x400/f4ede2/5f4336?text=Pizzeria"}"
          class="w-full h-40 object-cover" alt="${product.name}">

        <div class="menu-card-body">
          <div class="menu-card-topline">
            <span class="badge">${getProductBadge(product.category, index)}</span>
            <span class="rating-pill">${eta}</span>
          </div>

          <h4>${product.name}</h4>
          <p>${product.description || "Freshly prepared and positioned for a cleaner delivery-app style browsing flow."}</p>

          <div class="menu-card-footer">
            <div class="price-block">
              <strong>€${Number(product.price).toFixed(2)}</strong>
              <span>${vibe}</span>
            </div>
            <button data-product-id="${product.id}" class="add-to-cart">Add</button>
          </div>
        </div>
      `;

      grid.appendChild(card);
    });

    menu.appendChild(section);
  });

  if (!visibleProducts.length) {
    menu.innerHTML = `
      <div class="empty-state">
        No products match your current search. Try a broader term or switch category.
      </div>
    `;
  }

  if (selectedCategory) {
    searchState.textContent = `Showing ${visibleProducts.length} result(s) inside ${selectedCategory}.`;
  } else if (searchTerm.trim()) {
    searchState.textContent = `Showing ${visibleProducts.length} result(s) for "${searchTerm.trim()}".`;
  } else {
    searchState.textContent = "Choose a category or search to narrow the menu instantly.";
  }
}

function renderCart() {
  cartContainer.innerHTML = "";

  let total = 0;
  let count = 0;

  cart.forEach((item) => {
    total += item.price * item.quantity;
    count += item.quantity;

    const div = document.createElement("article");
    div.className = "cart-item";
    div.innerHTML = `
      <div class="cart-item-top">
        <div>
          <div class="cart-item-name">${item.name}</div>
          <div class="cart-item-price">€${Number(item.price).toFixed(2)} each</div>
        </div>
        <strong>€${(item.price * item.quantity).toFixed(2)}</strong>
      </div>
      <div class="cart-item-actions">
        <div class="qty-pill">
          <span>Qty</span>
          <span>${item.quantity}</span>
        </div>
        <button data-remove-id="${item.id}" class="remove-button">Remove</button>
      </div>
    `;

    cartContainer.appendChild(div);
  });

  if (!cart.length) {
    cartContainer.innerHTML = `
      <div class="empty-state">
        Your basket is empty. Add a few strong visual sellers and the checkout button will be ready.
      </div>
    `;
  }

  const grandTotal = total + 2.5;

  totalEl.textContent = total.toFixed(2);
  grandTotalEl.textContent = grandTotal.toFixed(2);
  countEl.textContent = count;
  floatingCartCountEl.textContent = count;
  heroProductCount.textContent = products.length;
}

function addToCart(id) {
  const product = products.find((item) => item.id === id);
  const existing = cart.find((item) => item.id === id);

  if (!product) {
    return;
  }

  if (existing) {
    existing.quantity += 1;
  } else {
    cart.push({ ...product, quantity: 1 });
  }

  saveCart();
  renderCart();
}

function removeFromCart(id) {
  cart = cart.filter((item) => item.id !== id);
  saveCart();
  renderCart();
}

function toggleCart() {
  const isOpen = cartEl.classList.contains("cart-visible");

  if (isOpen) {
    cartEl.classList.remove("cart-visible");
    cartEl.classList.add("cart-hidden");
    overlay.classList.add("hidden");
  } else {
    cartEl.classList.remove("cart-hidden");
    cartEl.classList.add("cart-visible");
    overlay.classList.remove("hidden");
  }
}

function toggleTheme() {
  document.body.classList.toggle("dark");
}

async function checkout() {
  if (!cart.length) {
    alert("Cart is empty");
    return;
  }

  const orderPayload = {
    items: cart.map((item) => ({
      product_id: item.id,
      quantity: item.quantity,
      extras: "",
    })),
  };

  const { response: orderResponse, data: orderData } = await apiRequest("/orders", {
    method: "POST",
    auth: false,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(orderPayload),
  });

  if (!orderResponse.ok) {
    alert(orderData?.detail || "Could not create order");
    return;
  }

  const checkoutItems = cart.map((item) => ({
    name: item.name,
    price: item.price,
    quantity: item.quantity,
  }));

  const { response, data } = await apiRequest("/create-checkout-session", {
    method: "POST",
    auth: false,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({
      items: checkoutItems,
      order_id: orderData.order_id,
    }),
  });

  if (!response.ok) {
    alert(data?.detail || "Error creating payment");
    return;
  }

  if (data?.url) {
    window.location.href = data.url;
    return;
  }

  alert("Stripe did not return a checkout URL");
}

async function loadProducts() {
  const { response, data } = await apiRequest("/products", { auth: false });

  if (!response.ok) {
    console.error("Could not load products");
    return;
  }

  products = data;
  renderCategories();
  renderMenu();
  renderCart();
}

menu.addEventListener("click", (event) => {
  const button = event.target.closest(".add-to-cart");

  if (!button) {
    return;
  }

  addToCart(Number(button.dataset.productId));
});

featuredGrid.addEventListener("click", (event) => {
  const button = event.target.closest(".add-to-cart");

  if (!button) {
    return;
  }

  addToCart(Number(button.dataset.productId));
});

cartContainer.addEventListener("click", (event) => {
  const button = event.target.closest("[data-remove-id]");

  if (!button) {
    return;
  }

  removeFromCart(Number(button.dataset.removeId));
});

window.toggleCart = toggleCart;
window.toggleTheme = toggleTheme;
window.checkout = checkout;

searchInput.addEventListener("input", (event) => {
  searchTerm = event.target.value;
  renderFeatured();
  renderMenu();
});

loadProducts();
