import api from "./api.js";

/** Thin catalog API layer — every function returns the envelope's `data`. */

function cleanParams(params) {
  // Keep booleans (including false) — drop only empty/nullish values.
  return Object.fromEntries(
    Object.entries(params).filter(
      ([, value]) => value !== "" && value !== null && value !== undefined,
    ),
  );
}

async function get(url, params = {}) {
  const response = await api.get(url, { params: cleanParams(params) });
  return response.data.data;
}

export const fetchProducts = (params = {}) => get("/products", params);
export const fetchProduct = (identifier) => get(`/products/${encodeURIComponent(identifier)}`);
export const fetchRelated = (identifier) => get(`/products/${encodeURIComponent(identifier)}/related`);
export const fetchFeatured = (limit = 8) => get("/products/featured", { limit });
export const fetchNewArrivals = (limit = 8) => get("/products/new-arrivals", { limit });
export const fetchBestSellers = (limit = 8) => get("/products/best-sellers", { limit });
export const fetchCategories = (tree = false) => get("/categories", { tree });
export const fetchBrands = () => get("/brands");

// --- Reviews (Phase 7) -------------------------------------------------------
export const fetchReviews = (productId, params = {}) =>
  get(`/products/${productId}/reviews`, params);
export const createReview = async (productId, payload) =>
  (await api.post(`/products/${productId}/reviews`, payload)).data;
export const updateReview = async (reviewId, payload) =>
  (await api.patch(`/reviews/${reviewId}`, payload)).data;
export const deleteReview = async (reviewId) =>
  (await api.delete(`/reviews/${reviewId}`)).data;
