import { Route, Routes } from "react-router-dom";

import AdminRoute from "./components/AdminRoute.jsx";
import ProtectedRoute from "./components/ProtectedRoute.jsx";
import AdminLayout from "./layouts/AdminLayout.jsx";
import StoreLayout from "./layouts/StoreLayout.jsx";
import AccountLayout from "./pages/account/AccountLayout.jsx";
import Addresses from "./pages/account/Addresses.jsx";
import ChangePassword from "./pages/account/ChangePassword.jsx";
import OrderDetail from "./pages/account/OrderDetail.jsx";
import Orders from "./pages/account/Orders.jsx";
import Profile from "./pages/account/Profile.jsx";
import WishlistAccount from "./pages/account/Wishlist.jsx";
import AdminCategories from "./pages/admin/Categories.jsx";
import AdminDashboard from "./pages/admin/Dashboard.jsx";
import AdminCustomerDetail from "./pages/admin/CustomerDetail.jsx";
import AdminCustomers from "./pages/admin/Customers.jsx";
import AdminOrderDetail from "./pages/admin/OrderDetail.jsx";
import AdminOrders from "./pages/admin/Orders.jsx";
import AdminProducts from "./pages/admin/Products.jsx";
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
 * Phase 5: /account/* (profile, addresses, orders, wishlist, password)
 * Phase 6: /admin/* (dashboard, products, categories, orders, customers)
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

      {/* Admin area (auth + admin role required) */}
      <Route
        path="/admin"
        element={
          <AdminRoute>
            <AdminLayout />
          </AdminRoute>
        }
      >
        <Route index element={<AdminDashboard />} />
        <Route path="products" element={<AdminProducts />} />
        <Route path="categories" element={<AdminCategories />} />
        <Route path="orders" element={<AdminOrders />} />
        <Route path="orders/:orderId" element={<AdminOrderDetail />} />
        <Route path="customers" element={<AdminCustomers />} />
        <Route path="customers/:customerId" element={<AdminCustomerDetail />} />
      </Route>

      <Route path="*" element={<NotFound />} />
    </Routes>
  );
}
