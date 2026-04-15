import {
  API_URL,
  apiRequest,
  clearAuthToken,
  getAuthToken,
  setAuthToken,
} from "./api.js";

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
const checkoutCardButton = document.getElementById("checkout-card-button");
const checkoutCashButton = document.getElementById("checkout-cash-button");
const searchInput = document.getElementById("search-input");
const heroProductCount = document.getElementById("hero-product-count");
const searchState = document.getElementById("search-state");

const authCtaButton = document.getElementById("auth-cta-button");
const authLabel = document.getElementById("auth-label");
const authStatus = document.getElementById("auth-status");
const authPanel = document.getElementById("auth-panel");
const authPanelOverlay = document.getElementById("auth-panel-overlay");
const closeAuthPanelButton = document.getElementById("close-auth-panel");
const authMessage = document.getElementById("auth-message");
const registerForm = document.getElementById("register-form");
const loginForm = document.getElementById("login-form");
const profilePanel = document.getElementById("profile-panel");
const profileForm = document.getElementById("profile-form");
const profileFullName = document.getElementById("profile-full-name");
const profileAddressLine = document.getElementById("profile-address-line");
const profileCity = document.getElementById("profile-city");
const profilePostalCode = document.getElementById("profile-postal-code");
const profilePhone = document.getElementById("profile-phone");
const profileLogoutButton = document.getElementById("profile-logout-button");

let products = [];
let cart = JSON.parse(localStorage.getItem("cart")) || [];
let selectedCategory = null;
let searchTerm = "";
let currentUser = null;

function saveCart() {
  localStorage.setItem("cart", JSON.stringify(cart));
}

function formatApiError(data, fallbackMessage) {
  if (typeof data === "string" && data.trim()) {
    return data.trim();
  }

  if (Array.isArray(data?.detail)) {
    return data.detail
      .map((item) => item.msg || item.message || JSON.stringify(item))
      .join(" | ");
  }

  if (typeof data?.detail === "string") {
    return data.detail;
  }

  return fallbackMessage;
}

function setAuthMessage(message, tone = "neutral") {
  authMessage.textContent = message;
  authMessage.className = `auth-message ${tone}`;
}

function renderSession() {
  if (!currentUser) {
    authLabel.textContent = "Sign in";
    authStatus.textContent = "Guest checkout mode";
    checkoutCardButton.textContent = "Pay by card as guest";
    checkoutCashButton.textContent = "Cash on delivery";
    if (profilePanel) {
      profilePanel.classList.add("hidden");
    }
    if (profileForm) {
      profileForm.reset();
    }
    return;
  }

  authLabel.textContent = "My account";
  authStatus.textContent = currentUser.full_name
    ? `${currentUser.full_name} · signed in`
    : `Signed in as ${currentUser.email}`;
  checkoutCardButton.textContent = "Pay by card";
  checkoutCashButton.textContent = "Cash on delivery";
  if (profilePanel) {
    profilePanel.classList.remove("hidden");
  }
  if (profileFullName) {
    profileFullName.value = currentUser.full_name || "";
  }
  if (profileAddressLine) {
    profileAddressLine.value = currentUser.address_line || "";
  }
  if (profileCity) {
    profileCity.value = currentUser.city || "";
  }
  if (profilePostalCode) {
    profilePostalCode.value = currentUser.postal_code || "";
  }
  if (profilePhone) {
    profilePhone.value = currentUser.phone || "";
  }
}

function openAuthPanel() {
  authPanel.classList.remove("hidden");
  authPanelOverlay.classList.remove("hidden");
  document.body.classList.add("modal-open");
}

function closeAuthPanel() {
  authPanel.classList.add("hidden");
  authPanelOverlay.classList.add("hidden");
  document.body.classList.remove("modal-open");
}

async function restoreSession() {
  if (!getAuthToken()) {
    currentUser = null;
    renderSession();
    return;
  }

  const { response, data } = await apiRequest("/auth/me");

  if (!response.ok) {
    clearAuthToken();
    currentUser = null;
    renderSession();
    return;
  }

  currentUser = data;
  renderSession();
  setAuthMessage("Session restored. You are ready to order.", "success");
}

async function handleAuthSubmit(path, payload, successMessage) {
  let response;
  let data;
  try {
    ({ response, data } = await apiRequest(path, {
      method: "POST",
      auth: false,
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    }));
  } catch (_error) {
    setAuthMessage(
      `Could not reach server at ${API_URL}. Check backend availability.`,
      "error",
    );
    return false;
  }

  if (!response.ok) {
    setAuthMessage(formatApiError(data, "Authentication failed"), "error");
    return false;
  }

  setAuthToken(data.access_token);
  currentUser = data.user;
  renderSession();
  setAuthMessage(successMessage, "success");
  closeAuthPanel();
  return true;
}

async function saveProfile() {
  if (!currentUser) {
    setAuthMessage("Sign in before saving profile details.", "error");
    return false;
  }

  const payload = {
    full_name: profileFullName?.value || "",
    address_line: profileAddressLine?.value || "",
    city: profileCity?.value || "",
    postal_code: profilePostalCode?.value || "",
    phone: profilePhone?.value || "",
  };

  const { response, data } = await apiRequest("/auth/me/profile", {
    method: "PATCH",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    setAuthMessage(formatApiError(data, "Could not save profile"), "error");
    return false;
  }

  currentUser = data;
  renderSession();
  setAuthMessage("Profile saved. Your delivery details are up to date.", "success");
  return true;
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

function buildOrderPayload() {
  return {
    items: cart.map((item) => ({
      product_id: item.id,
      quantity: item.quantity,
      extras: "",
    })),
  };
}

async function checkoutCard() {
  if (!cart.length) {
    alert("Cart is empty");
    return;
  }

  const orderPayload = buildOrderPayload();

  const { response: orderResponse, data: orderData } = await apiRequest("/orders", {
    method: "POST",
    auth: Boolean(currentUser),
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
    auth: Boolean(currentUser),
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

async function checkoutCash() {
  if (!cart.length) {
    alert("Cart is empty");
    return;
  }

  const { response, data } = await apiRequest("/orders/cash-checkout", {
    method: "POST",
    auth: Boolean(currentUser),
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(buildOrderPayload()),
  });

  if (!response.ok) {
    alert(data?.detail || "Could not place cash order");
    return;
  }

  cart = [];
  saveCart();
  renderCart();
  toggleCart();
  alert(`Cash order #${data.order_id} placed successfully.`);
}

async function loadProducts() {
  const { response, data } = await apiRequest("/products", { auth: false });

  if (!response.ok) {
    console.error("Could not load products");
    return;
  }

  products = data;
  renderCategories();
  renderFeatured();
  renderMenu();
  renderCart();
}

if (registerForm) {
  registerForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("register-email").value.trim();
    const password = document.getElementById("register-password").value;

    const success = await handleAuthSubmit(
      "/auth/register",
      { email, password },
      "Account created and signed in",
    );

    if (success) {
      registerForm.reset();
    }
  });
}

if (loginForm) {
  loginForm.addEventListener("submit", async (event) => {
    event.preventDefault();

    const email = document.getElementById("login-email").value.trim();
    const password = document.getElementById("login-password").value;

    const success = await handleAuthSubmit(
      "/auth/login",
      { email, password },
      "Welcome back. Session is active",
    );

    if (success) {
      loginForm.reset();
    }
  });
}

authCtaButton.addEventListener("click", () => {
  if (!currentUser) {
    setAuthMessage("Create an account or sign in to continue with your session.", "neutral");
    openAuthPanel();
    return;
  }

  setAuthMessage("Review or update your saved delivery details.", "neutral");
  openAuthPanel();
});

if (profileLogoutButton) {
  profileLogoutButton.addEventListener("click", () => {
    clearAuthToken();
    currentUser = null;
    renderSession();
    closeAuthPanel();
    setAuthMessage("You signed out successfully.", "success");
  });
}

closeAuthPanelButton.addEventListener("click", closeAuthPanel);
authPanelOverlay.addEventListener("click", closeAuthPanel);
if (profileForm) {
  profileForm.addEventListener("submit", async (event) => {
    event.preventDefault();
    await saveProfile();
  });
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
window.checkoutCard = checkoutCard;
window.checkoutCash = checkoutCash;

searchInput.addEventListener("input", (event) => {
  searchTerm = event.target.value;
  renderFeatured();
  renderMenu();
});

await restoreSession();
await loadProducts();
