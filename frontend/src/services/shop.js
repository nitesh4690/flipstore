import api from "./api.js";

/**
 * Phase 5 API layer: cart, wishlist, addresses, orders, account.
 * Every function returns the envelope's `data`.
 */

async function request(method, url, body) {
  const response = body !== undefined ? await api[method](url, body) : await api[method](url);
  return response.data.data;
}

// --- Cart (server-side; requires auth) -------------------------------------
export const getCart = () => request("get", "/cart");
export const addToCart = (payload) => request("post", "/cart/items", payload);
export const updateCartQuantity = (itemId, quantity) =>
  request("put", `/cart/items/${itemId}`, { quantity });
export const removeCartItem = (itemId) => request("delete", `/cart/items/${itemId}`);
export const clearServerCart = () => request("delete", "/cart");
export const applyCoupon = (code) => request("put", "/cart/coupon", { code });

// --- Wishlist ----------------------------------------------------------------
export const getWishlist = () => request("get", "/wishlist");
export const addWishlistItem = (productId) =>
  request("post", "/wishlist/items", { product_id: productId });
export const removeWishlistItem = (productId) =>
  request("delete", `/wishlist/items/${productId}`);

// --- Addresses ---------------------------------------------------------------
export const getAddresses = async () => (await request("get", "/addresses")).items;
export const createAddress = (payload) => request("post", "/addresses", payload);
export const updateAddress = (addressId, payload) =>
  request("put", `/addresses/${addressId}`, payload);
export const deleteAddress = (addressId) => request("delete", `/addresses/${addressId}`);

// --- Orders / checkout --------------------------------------------------------
export const placeOrder = (payload) => request("post", "/orders", payload);
export const getOrders = async (page = 1, limit = 10) =>
  request("get", `/orders?page=${page}&limit=${limit}`);
export const getOrder = (orderId) => request("get", `/orders/${orderId}`);

// --- Account ------------------------------------------------------------------
export const updateProfile = (payload) => request("put", "/users/me", payload);
export const changePassword = (payload) => request("put", "/auth/change-password", payload);
