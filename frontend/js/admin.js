import { API_URL, apiRequest, clearAuthToken, setAuthToken } from "./api.js";

const authPanel = document.getElementById("auth-panel");
const adminPanel = document.getElementById("admin-panel");
const authMessage = document.getElementById("auth-message");
const sessionInfo = document.getElementById("session-info");
const productsContainer = document.getElementById("products");
const ordersContainer = document.getElementById("orders");

const registerForm = document.getElementById("register-form");
const loginForm = document.getElementById("login-form");
const productForm = document.getElementById("product-form");
const refreshButton = document.getElementById("refresh-products");
const refreshOrdersButton = document.getElementById("refresh-orders");
const logoutButton = document.getElementById("logout-button");
const productSearchInput = document.getElementById("product-search");
const editModalOverlay = document.getElementById("edit-modal-overlay");
const editProductForm = document.getElementById("edit-product-form");
const closeEditModalButton = document.getElementById("close-edit-modal");
const cancelEditModalButton = document.getElementById("cancel-edit-modal");

const totalProductsStat = document.getElementById("stat-total-products");
const totalCategoriesStat = document.getElementById("stat-total-categories");
const sessionModeStat = document.getElementById("stat-session-mode");

let currentUser = null;
let products = [];
let orders = [];
let searchTerm = "";
let editingProductId = null;

const ORDER_STATUS_OPTIONS = [
  "created",
  "paid",
  "accepted",
  "printing",
  "printed",
  "ready",
  "delivered",
  "failed",
  "cancelled",
];

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
          <div class="product-actions">
            <button
              type="button"
              data-product-id="${product.id}"
              class="edit-product ghost-button"
            >
              Edit
            </button>
            <button
              type="button"
              data-product-id="${product.id}"
              class="delete-product"
            >
              Delete
            </button>
          </div>
        </div>
      </div>
    `;

    productsContainer.appendChild(element);
  });
}

function getLatestPrintJob(order) {
  if (!Array.isArray(order.print_jobs) || !order.print_jobs.length) {
    return null;
  }

  return [...order.print_jobs].sort((a, b) => b.id - a.id)[0];
}

function renderOrders() {
  ordersContainer.innerHTML = "";

  if (!orders.length) {
    ordersContainer.innerHTML = `
      <div class="empty-state order-empty-state">
        No orders yet. New paid orders will appear here so you can accept and print them.
      </div>
    `;
    return;
  }

  orders.forEach((order) => {
    const latestJob = getLatestPrintJob(order);
    const statusOptions = ORDER_STATUS_OPTIONS.map((status) => `
      <option value="${status}" ${order.status === status ? "selected" : ""}>${status}</option>
    `).join("");

    const itemsSummary = order.items
      .map((item) => `#${item.product_id} x${item.quantity}`)
      .join(" · ");

    const printText = latestJob
      ? `Print job #${latestJob.id} · ${latestJob.status} · attempt ${latestJob.attempt_count}/${latestJob.max_attempts}`
      : "No print job yet";

    const printError = latestJob?.last_error
      ? `<p class="order-print-error">Last print error: ${latestJob.last_error}</p>`
      : "";

    const card = document.createElement("article");
    card.className = "order-card";
    card.innerHTML = `
      <div class="order-head">
        <div>
          <p class="eyebrow">Order #${order.id}</p>
          <h5>${order.status}</h5>
        </div>
        <strong class="order-total">€${Number(order.total_price).toFixed(2)}</strong>
      </div>

      <p class="order-items">${itemsSummary || "No items found"}</p>
      <p class="order-print">${printText}</p>
      ${printError}

      <div class="order-actions">
        <label class="order-status-field">
          <span>Next status</span>
          <select class="order-status-select" data-order-id="${order.id}">
            ${statusOptions}
          </select>
        </label>
        <button type="button" class="ghost-button save-order-status" data-order-id="${order.id}">Update status</button>
        <button type="button" class="ghost-button order-reprint" data-order-id="${order.id}">Reprint</button>
      </div>
    `;

    ordersContainer.appendChild(card);
  });
}

function openEditModal(product) {
  editingProductId = product.id;
  document.getElementById("edit-name").value = product.name;
  document.getElementById("edit-price").value = String(product.price);
  document.getElementById("edit-category").value = product.category;
  document.getElementById("edit-description").value = product.description || "";
  document.getElementById("edit-image").value = "";
  editModalOverlay.classList.remove("hidden");
  document.body.classList.add("modal-open");
}

function closeEditModal() {
  editingProductId = null;
  editProductForm.reset();
  editModalOverlay.classList.add("hidden");
  document.body.classList.remove("modal-open");
}

function buildProductFormData({
  nameId,
  priceId,
  categoryId,
  descriptionId,
  imageId,
}) {
  const formData = new FormData();
  formData.append("name", document.getElementById(nameId).value.trim());
  formData.append("price", document.getElementById(priceId).value);
  formData.append("category", document.getElementById(categoryId).value);
  formData.append("description", document.getElementById(descriptionId).value.trim());

  const imageFile = document.getElementById(imageId).files[0];
  if (imageFile) {
    formData.append("file", imageFile);
  }

  return formData;
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

async function loadOrders() {
  if (!currentUser?.is_admin) {
    orders = [];
    renderOrders();
    return;
  }

  const { response, data } = await apiRequest("/admin/orders?limit=80");

  if (!response.ok) {
    setMessage(formatApiError(data, "Could not load orders"), "error");
    return;
  }

  orders = data;
  renderOrders();
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
  await loadOrders();
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
  await loadOrders();
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

  const formData = buildProductFormData({
    nameId: "name",
    priceId: "price",
    categoryId: "category",
    descriptionId: "description",
    imageId: "image",
  });

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

refreshOrdersButton.addEventListener("click", async () => {
  await loadOrders();
  setMessage("Orders refreshed", "neutral");
});

logoutButton.addEventListener("click", () => {
  clearAuthToken();
  currentUser = null;
  orders = [];
  renderOrders();
  closeEditModal();
  renderSession();
  setMessage("Session closed", "neutral");
});

closeEditModalButton.addEventListener("click", () => {
  closeEditModal();
  setMessage("Edit closed", "neutral");
});

cancelEditModalButton.addEventListener("click", () => {
  closeEditModal();
  setMessage("Edit cancelled", "neutral");
});

editModalOverlay.addEventListener("click", (event) => {
  if (event.target === editModalOverlay) {
    closeEditModal();
  }
});

productSearchInput.addEventListener("input", (event) => {
  searchTerm = event.target.value;
  renderProducts();
});

productsContainer.addEventListener("click", async (event) => {
  const editButton = event.target.closest(".edit-product");

  if (editButton) {
    const productId = Number(editButton.dataset.productId);
    const product = products.find((item) => item.id === productId);

    if (!product) {
      setMessage("Product not found in current list", "error");
      return;
    }

    openEditModal(product);
    setMessage(`Editing "${product.name}"`, "neutral");
    return;
  }

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

  if (editingProductId === Number(productId)) {
    closeEditModal();
  }

  setMessage("Product deleted", "success");
  await loadProducts();
});

ordersContainer.addEventListener("click", async (event) => {
  const saveStatusButton = event.target.closest(".save-order-status");

  if (saveStatusButton) {
    const orderId = Number(saveStatusButton.dataset.orderId);
    const select = ordersContainer.querySelector(`.order-status-select[data-order-id="${orderId}"]`);

    if (!select) {
      setMessage("Could not read selected status", "error");
      return;
    }

    const { response, data } = await apiRequest(`/admin/orders/${orderId}/status`, {
      method: "PATCH",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ status: select.value }),
    });

    if (!response.ok) {
      setMessage(formatApiError(data, "Could not update order status"), "error");
      return;
    }

    setMessage(`Order #${orderId} updated to ${data.status}`, "success");
    await loadOrders();
    return;
  }

  const reprintButton = event.target.closest(".order-reprint");

  if (!reprintButton) {
    return;
  }

  const orderId = Number(reprintButton.dataset.orderId);
  const { response, data } = await apiRequest(`/admin/orders/${orderId}/reprint`, {
    method: "POST",
  });

  if (!response.ok) {
    setMessage(formatApiError(data, "Could not request reprint"), "error");
    return;
  }

  setMessage(`Order #${orderId} moved to print queue`, "success");
  await loadOrders();
});

editProductForm.addEventListener("submit", async (event) => {
  event.preventDefault();

  if (editingProductId === null) {
    setMessage("No product selected for edit", "error");
    return;
  }

  const formData = buildProductFormData({
    nameId: "edit-name",
    priceId: "edit-price",
    categoryId: "edit-category",
    descriptionId: "edit-description",
    imageId: "edit-image",
  });

  const { response, data } = await apiRequest(`/admin/products/${editingProductId}`, {
    method: "PUT",
    body: formData,
  });

  if (!response.ok) {
    setMessage(formatApiError(data, "Could not update product"), "error");
    return;
  }

  closeEditModal();
  setMessage(`Product "${data.name}" updated`, "success");
  await loadProducts();
});

renderSession();
loadProducts();
renderOrders();
restoreSession();
