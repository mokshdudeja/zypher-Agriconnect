import { useState } from 'react'
import { Link, useLocation, useNavigate } from 'react-router-dom'
import { Menu, X, Sprout, LogOut, User } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const roleNavItems = {
  farmer: [
    { path: '/farmer', label: 'Dashboard' },
    { path: '/farmer/add-crop', label: 'Add Crop' },
    { path: '/farmer/listings', label: 'My Listings' },
  ],
  wholesaler: [
    { path: '/wholesaler', label: 'Dashboard' },
    { path: '/wholesaler/browse', label: 'Browse Listings' },
    { path: '/wholesaler/inventory', label: 'Inventory' },
    { path: '/wholesaler/orders', label: 'Order History' },
  ],
  consumer: [
    { path: '/consumer', label: 'Home' },
    { path: '/consumer/products', label: 'Products' },
    { path: '/consumer/cart', label: 'Cart' },
    { path: '/consumer/orders', label: 'Orders' },
  ],
  admin: [
    { path: '/admin', label: 'Dashboard' },
    { path: '/admin/users', label: 'Users' },
    { path: '/admin/verify', label: 'Verification' },
    { path: '/admin/transactions', label: 'Transactions' },
    { path: '/admin/reports', label: 'Reports' },
  ],
}

const roleColors = {
  farmer: 'bg-leaf-600',
  wholesaler: 'bg-harvest-600',
  consumer: 'bg-sky-600',
  admin: 'bg-slate-800',
}

export default function Navbar({ role }) {
  const [open, setOpen] = useState(false)
  const [showProfile, setShowProfile] = useState(false)
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()
  const items = roleNavItems[role] || []
  const color = roleColors[role] || 'bg-slate-800'

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <nav className={`${color} text-white sticky top-0 z-50 shadow-lg`}>
      <div className="max-w-7xl mx-auto px-4 sm:px-6">
        <div className="flex items-center justify-between h-16">
          {/* Logo */}
          <Link to={`/${role}`} className="flex items-center gap-2 font-display text-xl font-bold tracking-tight">
            <Sprout className="w-7 h-7" />
            <span>AgriConnect</span>
          </Link>

          {/* Desktop Nav */}
          <div className="hidden md:flex items-center gap-1">
            {items.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                className={`px-4 py-2 rounded-lg text-sm font-medium transition-all duration-200 ${
                  location.pathname === item.path
                    ? 'bg-white/20 shadow-sm'
                    : 'hover:bg-white/10'
                }`}
              >
                {item.label}
              </Link>
            ))}
          </div>

          {/* User Profile Dropdown */}
          <div className="hidden md:flex items-center gap-3">
            <div className="relative">
              <button
                onClick={() => setShowProfile(!showProfile)}
                className="flex items-center gap-2 px-3 py-1.5 bg-white/15 hover:bg-white/25 rounded-xl transition-colors"
              >
                <div className="w-7 h-7 rounded-full bg-white/20 flex items-center justify-center text-sm">
                  {user?.avatar || <User className="w-4 h-4" />}
                </div>
                <span className="text-sm font-medium max-w-[120px] truncate">
                  {user?.name || 'User'}
                </span>
              </button>

              {/* Dropdown */}
              {showProfile && (
                <>
                  <div className="fixed inset-0 z-40" onClick={() => setShowProfile(false)} />
                  <div className="absolute right-0 top-full mt-2 w-56 bg-white rounded-xl shadow-elevated border border-slate-200 py-2 z-50 animate-scale-in">
                    <div className="px-4 py-3 border-b border-slate-100">
                      <p className="text-sm font-semibold text-slate-800">{user?.name}</p>
                      <p className="text-xs text-slate-400 truncate">{user?.email}</p>
                      <span className="inline-block mt-1 px-2 py-0.5 bg-slate-100 rounded-full text-xs font-semibold text-slate-600 capitalize">
                        {user?.role}
                      </span>
                    </div>
                    <button
                      onClick={handleLogout}
                      className="w-full flex items-center gap-2 px-4 py-2.5 text-sm text-red-600 hover:bg-red-50 transition-colors"
                    >
                      <LogOut className="w-4 h-4" />
                      Sign Out
                    </button>
                  </div>
                </>
              )}
            </div>
          </div>

          {/* Mobile toggle */}
          <button
            onClick={() => setOpen(!open)}
            className="md:hidden p-2 rounded-lg hover:bg-white/10 transition-colors"
            aria-label="Toggle menu"
          >
            {open ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6" />}
          </button>
        </div>
      </div>

      {/* Mobile menu */}
      {open && (
        <div className="md:hidden animate-fade-in border-t border-white/10">
          <div className="px-4 py-3 space-y-1">
            {/* User info */}
            <div className="flex items-center gap-3 px-4 py-3 bg-white/10 rounded-xl mb-2">
              <div className="w-10 h-10 rounded-full bg-white/20 flex items-center justify-center text-lg">
                {user?.avatar || '👤'}
              </div>
              <div>
                <p className="text-sm font-semibold">{user?.name}</p>
                <p className="text-xs opacity-70">{user?.email}</p>
              </div>
            </div>

            {items.map((item) => (
              <Link
                key={item.path}
                to={item.path}
                onClick={() => setOpen(false)}
                className={`block px-4 py-3 rounded-lg text-sm font-medium transition-colors ${
                  location.pathname === item.path
                    ? 'bg-white/20'
                    : 'hover:bg-white/10'
                }`}
              >
                {item.label}
              </Link>
            ))}

            <button
              onClick={handleLogout}
              className="w-full flex items-center gap-2 px-4 py-3 rounded-lg text-sm font-medium bg-red-500/20 hover:bg-red-500/30 transition-colors mt-2 text-red-200"
            >
              <LogOut className="w-4 h-4" />
              Sign Out
            </button>
          </div>
        </div>
      )}
    </nav>
  )
}
