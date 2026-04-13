import { API_URL, apiRequest, clearAuthToken, setAuthToken } from "./api.js";

const authPanel = document.getElementById("auth-panel");
const adminPanel = document.getElementById("admin-panel");
const authMessage = document.getElementById("auth-message");
const sessionInfo = document.getElementById("session-info");
const productsContainer = document.getElementById("products");

const registerForm = document.getElementById("register-form");
const loginForm = document.getElementById("login-form");
const productForm = document.getElementById("product-form");
const refreshButton = document.getElementById("refresh-products");
const logoutButton = document.getElementById("logout-button");
const productSearchInput = document.getElementById("product-search");

const totalProductsStat = document.getElementById("stat-total-products");
const totalCategoriesStat = document.getElementById("stat-total-categories");
const sessionModeStat = document.getElementById("stat-session-mode");

let currentUser = null;
let products = [];
let searchTerm = "";

function formatApiError(data, fallbackMessage) {
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

function setMessage(message, tone = "neutral") {
  authMessage.textContent = message;
  authMessage.className = `message-banner ${tone}`;
}

function updateStats() {
  totalProductsStat.textContent = String(products.length);
  totalCategoriesStat.textContent = String(new Set(products.map((product) => product.category)).size);

  if (!currentUser) {
    sessionModeStat.textContent = "Guest";
  } else if (currentUser.is_admin) {
    sessionModeStat.textContent = "Admin";
  } else {
    sessionModeStat.textContent = "User";
  }
}

function renderSession() {
  if (!currentUser) {
    authPanel.classList.remove("hidden");
    adminPanel.classList.add("hidden");
    sessionInfo.textContent = "No active admin session";
    updateStats();
    return;
  }

  if (!currentUser.is_admin) {
    authPanel.classList.remove("hidden");
    adminPanel.classList.add("hidden");
    sessionInfo.textContent = `${currentUser.email} · no admin access`;
    setMessage("This account does not have admin permissions", "error");
    updateStats();
    return;
  }

  authPanel.classList.add("hidden");
  adminPanel.classList.remove("hidden");
  sessionInfo.textContent = `${currentUser.email} · admin session active`;
  updateStats();
}

function getVisibleProducts() {
  const normalized = searchTerm.trim().toLowerCase();

  if (!normalized) {
    return products;
  }

  return products.filter((product) => {
    const haystack = `${product.name} ${product.description || ""} ${product.category}`.toLowerCase();
    return haystack.includes(normalized);
  });
}

function renderProducts() {
  const visibleProducts = getVisibleProducts();
  productsContainer.innerHTML = "";

  if (!visibleProducts.length) {
    productsContainer.innerHTML = `
      <div class="empty-state">
        No products match your current search. Try another keyword or clear the filter.
      </div>
    `;
    return;
  }

  visibleProducts.forEach((product) => {
    const element = document.createElement("article");
    element.className = "product-card";

    element.innerHTML = `
      <img
        src="${product.image_url ? `${API_URL}${product.image_url}` : "https://via.placeholder.com/640x420/f1e7dc/644336?text=Pizzeria"}"
        alt="${product.name}"
        class="product-card-image"
      />

      <div class="product-card-body">
        <div class="product-card-head">
          <div>
            <h5>${product.name}</h5>
            <p class="product-price">€${Number(product.price).toFixed(2)}</p>
          </div>
          <span class="category-chip">${product.category}</span>
        </div>

        <p class="product-meta">${product.description || "No description added yet."}</p>

        <div class="product-card-footer">
          <span class="badge">Product ID ${product.id}</span>
          <button
            type="button"
            data-product-id="${product.id}"
            class="delete-product"
          >
            Delete
          </button>
        </div>
      </div>
    `;

    productsContainer.appendChild(element);
  });
}

async function loadProducts() {
  const { response, data } = await apiRequest("/products", { auth: false });

  if (!response.ok) {
    setMessage("Could not load products", "error");
    return;
  }

  products = data;
  updateStats();
  renderProducts();
}

async function restoreSession() {
  const { response, data } = await apiRequest("/auth/me");

  if (!response.ok) {
    clearAuthToken();
    currentUser = null;
    renderSession();
    return;
  }

  currentUser = data;
  renderSession();
  setMessage("Admin session restored", "success");
  await loadProducts();
}

async function handleAuthSubmit(path, payload, successMessage) {
  const { response, data } = await apiRequest(path, {
    method: "POST",
    auth: false,
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify(payload),
  });

  if (!response.ok) {
    setMessage(formatApiError(data, "Authentication failed"), "error");
    return false;
  }

  setAuthToken(data.access_token);
  currentUser = data.user;
  renderSession();
  setMessage(successMessage, "success");
  await loadProducts();
  return true;
}

registerForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const email = document.getElementById("register-email").value.trim();
  const password = document.getElementById("register-password").value;

  const success = await handleAuthSubmit(
    "/auth/register",
    { email, password },
    "Account created and logged in",
  );

  if (success) {
    registerForm.reset();
  }
});

loginForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const email = document.getElementById("login-email").value.trim();
  const password = document.getElementById("login-password").value;

  const success = await handleAuthSubmit(
    "/auth/login",
    { email, password },
    "Login successful",
  );

  if (success) {
    loginForm.reset();
  }
});

productForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  const formData = new FormData(productForm);

  const { response, data } = await apiRequest("/admin/products", {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    setMessage(formatApiError(data, "Could not create product"), "error");
    return;
  }

  productForm.reset();
  setMessage(`Product "${data.name}" created`, "success");
  await loadProducts();
});

refreshButton.addEventListener("click", async () => {
  await loadProducts();
  setMessage("Products refreshed", "neutral");
});

logoutButton.addEventListener("click", () => {
  clearAuthToken();
  currentUser = null;
  renderSession();
  setMessage("Session closed", "neutral");
});

productSearchInput.addEventListener("input", (event) => {
  searchTerm = event.target.value;
  renderProducts();
});

productsContainer.addEventListener("click", async (event) => {
  const deleteButton = event.target.closest(".delete-product");

  if (!deleteButton) {
    return;
  }

  const productId = deleteButton.dataset.productId;

  const { response, data } = await apiRequest(`/admin/products/${productId}`, {
    method: "DELETE",
  });

  if (!response.ok) {
    setMessage(formatApiError(data, "Could not delete product"), "error");
    return;
  }

  setMessage("Product deleted", "success");
  await loadProducts();
});

renderSession();
loadProducts();
restoreSession();
