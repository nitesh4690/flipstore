import api from "./api.js";

/**
 * Phase 6 API layer: admin dashboard, product/order/customer management.
 * Every function returns the envelope's `data`.
 */

async function request(method, url, body) {
  const response = body !== undefined ? await api[method](url, body) : await api[method](url);
  return response.data.data;
}

function cleanParams(params) {
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== "" && value !== null && value !== undefined,
    ),
  );
}

function get(url, params = {}) {
  return api.get(url, { params: cleanParams(params) }).then((response) => response.data.data);
}

// --- Dashboard ---------------------------------------------------------------
export const getStats = () => request("get", "/admin/stats");

// --- Admin product listing (includes inactive) -------------------------------
export const getAdminProducts = (params = {}) => get("/admin/products", params);

// --- Admin orders -------------------------------------------------------------
export const getAdminOrders = (params = {}) => get("/admin/orders", params);
export const getAdminOrder = (orderId) => request("get", `/admin/orders/${orderId}`);
export const updateAdminOrder = (orderId, payload) =>
  request("patch", `/admin/orders/${orderId}`, payload);

// --- Admin customers -----------------------------------------------------------
export const getAdminCustomers = (params = {}) => get("/admin/customers", params);
export const getAdminCustomer = (customerId) =>
  request("get", `/admin/customers/${customerId}`);

// --- Admin writes (products / categories / brands) -----------------------------
export const createProduct = (payload) => request("post", "/products", payload);
export const updateProduct = (productId, payload) =>
  request("put", `/products/${productId}`, payload);
export const deleteProduct = (productId) => request("delete", `/products/${productId}`);

export const createCategory = (payload) => request("post", "/categories", payload);
export const updateCategory = (categoryId, payload) =>
  request("put", `/categories/${categoryId}`, payload);
export const deleteCategory = (categoryId) => request("delete", `/categories/${categoryId}`);

export const createBrand = (payload) => request("post", "/brands", payload);
export const updateBrand = (brandId, payload) =>
  request("put", `/brands/${brandId}`, payload);
export const deleteBrand = (brandId) => request("delete", `/brands/${brandId}`);

/** Categories/brands incl. inactive rows (for admin selects + management). */
export const getAdminCategories = () => get("/categories", { include_inactive: true });
export const getAdminBrands = () => get("/brands", { include_inactive: true });
