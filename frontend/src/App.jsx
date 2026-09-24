import { Route, Routes } from "react-router-dom";

import ProtectedRoute from "./components/ProtectedRoute.jsx";
import StoreLayout from "./layouts/StoreLayout.jsx";
import AccountLayout from "./pages/account/AccountLayout.jsx";
import Addresses from "./pages/account/Addresses.jsx";
import ChangePassword from "./pages/account/ChangePassword.jsx";
import OrderDetail from "./pages/account/OrderDetail.jsx";
import Orders from "./pages/account/Orders.jsx";
import Profile from "./pages/account/Profile.jsx";
import WishlistAccount from "./pages/account/Wishlist.jsx";
import Cart from "./pages/Cart.jsx";
import Checkout from "./pages/Checkout.jsx";
import Home from "./pages/Home.jsx";
import Login from "./pages/Login.jsx";
import NotFound from "./pages/NotFound.jsx";
import ProductDetail from "./pages/ProductDetail.jsx";
import Products from "./pages/Products.jsx";
import Register from "./pages/Register.jsx";

/**
 * Route tree.
 * Phase 5 adds: /account/* (profile, addresses, orders, wishlist, password)
 * Phase 6 adds: /admin/* (dashboard, products, categories, orders, customers)
 */
export default function App() {
  return (
    <Routes>
      <Route element={<StoreLayout />}>
        <Route path="/" element={<Home />} />
        <Route path="/products" element={<Products />} />
        <Route path="/products/:slug" element={<ProductDetail />} />
        <Route path="/cart" element={<Cart />} />
        <Route
          path="/checkout"
          element={
            <ProtectedRoute>
              <Checkout />
            </ProtectedRoute>
          }
        />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />

        {/* Account area (auth required) */}
        <Route
          path="/account"
          element={
            <ProtectedRoute>
              <AccountLayout />
            </ProtectedRoute>
          }
        >
          <Route index element={<Profile />} />
          <Route path="addresses" element={<Addresses />} />
          <Route path="orders" element={<Orders />} />
          <Route path="orders/:orderId" element={<OrderDetail />} />
          <Route path="wishlist" element={<WishlistAccount />} />
          <Route path="change-password" element={<ChangePassword />} />
        </Route>
      </Route>
      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
