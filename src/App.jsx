import { Routes, Route, Navigate } from 'react-router-dom'
import { useAuth } from './context/AuthContext'
import ProtectedRoute from './components/ProtectedRoute'
import { Toaster } from 'react-hot-toast'

// Layouts
import { FarmerLayout, WholesalerLayout, ConsumerLayout, AdminLayout } from './layouts/Layouts'

// Auth Pages
import Login from './pages/Login'
import Register from './pages/Register'

// Farmer Pages
import FarmerDashboard from './pages/farmer/FarmerDashboard'
import AddCrop from './pages/farmer/AddCrop'
import FarmerListings from './pages/farmer/FarmerListings'

// Wholesaler Pages
import WholesalerDashboard from './pages/wholesaler/WholesalerDashboard'
import BrowseListings from './pages/wholesaler/BrowseListings'
import Inventory from './pages/wholesaler/Inventory'
import OrderHistory from './pages/wholesaler/OrderHistory'

// Consumer Pages
import ConsumerHome from './pages/consumer/ConsumerHome'
import ProductListing from './pages/consumer/ProductListing'
import ProductDetails from './pages/consumer/ProductDetails'
import Cart from './pages/consumer/Cart'
import ConsumerOrders from './pages/consumer/ConsumerOrders'

// Admin Pages
import AdminDashboard from './pages/admin/AdminDashboard'
import UserManagement from './pages/admin/UserManagement'
import Verification from './pages/admin/Verification'
import Transactions from './pages/admin/Transactions'
import Reports from './pages/admin/Reports'

// Shared Pages
import QRScannerPage from './pages/shared/QRScannerPage'

/* Smart redirect: logged in → dashboard, logged out → login */
function AuthRedirect() {
  const { user } = useAuth()
  return <Navigate to={user ? `/${user.role}` : '/login'} replace />
}

/* Guard: if already logged in, skip auth pages */
function GuestOnly({ children }) {
  const { user } = useAuth()
  if (user) return <Navigate to={`/${user.role}`} replace />
  return children
}

/* Global loading screen */
function AppLoading() {
  return (
    <div className="min-h-screen flex items-center justify-center bg-earth-50">
      <div className="flex flex-col items-center gap-3 animate-fade-in">
        <div className="w-12 h-12 border-4 border-leaf-200 border-t-leaf-600 rounded-full animate-spin" />
        <p className="text-sm text-slate-500 font-medium">Loading AgriConnect...</p>
      </div>
    </div>
  )
}

export default function App() {
  const { loading } = useAuth()

  if (loading) return <AppLoading />

  return (
    <>
      <Routes>
        {/* Public Routes */}
        <Route path="/login" element={<GuestOnly><Login /></GuestOnly>} />
        <Route path="/register" element={<GuestOnly><Register /></GuestOnly>} />

        {/* Root → redirect intelligently */}
        <Route path="/" element={<AuthRedirect />} />

        {/* Farmer Routes (protected) */}
        <Route path="/farmer" element={
          <ProtectedRoute allowedRoles={['farmer']}>
            <FarmerLayout />
          </ProtectedRoute>
        }>
          <Route index element={<FarmerDashboard />} />
          <Route path="add-crop" element={<AddCrop />} />
          <Route path="listings" element={<FarmerListings />} />
        </Route>

        {/* Wholesaler Routes (protected) */}
        <Route path="/wholesaler" element={
          <ProtectedRoute allowedRoles={['wholesaler']}>
            <WholesalerLayout />
          </ProtectedRoute>
        }>
          <Route index element={<WholesalerDashboard />} />
          <Route path="browse" element={<BrowseListings />} />
          <Route path="inventory" element={<Inventory />} />
          <Route path="orders" element={<OrderHistory />} />
        </Route>

        {/* Consumer Routes (protected) */}
        <Route path="/consumer" element={
          <ProtectedRoute allowedRoles={['consumer']}>
            <ConsumerLayout />
          </ProtectedRoute>
        }>
          <Route index element={<ConsumerHome />} />
          <Route path="products" element={<ProductListing />} />
          <Route path="products/:id" element={<ProductDetails />} />
          <Route path="cart" element={<Cart />} />
          <Route path="orders" element={<ConsumerOrders />} />
        </Route>

        {/* Admin Routes (protected) */}
        <Route path="/admin" element={
          <ProtectedRoute allowedRoles={['admin']}>
            <AdminLayout />
          </ProtectedRoute>
        }>
          <Route index element={<AdminDashboard />} />
          <Route path="users" element={<UserManagement />} />
          <Route path="verify" element={<Verification />} />
          <Route path="transactions" element={<Transactions />} />
          <Route path="reports" element={<Reports />} />
        </Route>

        {/* Shared QR Scanner Route */}
        <Route path="/scan" element={
          <ProtectedRoute allowedRoles={['consumer', 'wholesaler', 'farmer']}>
            <QRScannerPage />
          </ProtectedRoute>
        } />

        {/* Catch-all */}
        <Route path="*" element={<AuthRedirect />} />
      </Routes>
      <Toaster position="top-right" />
    </>
  )
}
