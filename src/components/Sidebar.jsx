import { NavLink, useLocation, useNavigate } from 'react-router-dom'
import { LayoutDashboard, Users, ShieldCheck, ArrowLeftRight, FileBarChart, Sprout, X, LogOut } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const sidebarItems = [
  { path: '/admin', label: 'Dashboard', icon: LayoutDashboard },
  { path: '/admin/users', label: 'Users', icon: Users },
  { path: '/admin/verify', label: 'Verification', icon: ShieldCheck },
  { path: '/admin/transactions', label: 'Transactions', icon: ArrowLeftRight },
  { path: '/admin/reports', label: 'Reports', icon: FileBarChart },
]

export default function Sidebar({ open, onClose }) {
  const location = useLocation()
  const navigate = useNavigate()
  const { user, logout } = useAuth()

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <>
      {/* Overlay for mobile */}
      {open && (
        <div
          className="fixed inset-0 bg-black/40 z-40 lg:hidden"
          onClick={onClose}
        />
      )}

      <aside
        className={`fixed top-0 left-0 h-screen w-64 bg-slate-900 text-white z-50 transform transition-transform duration-300 ease-out lg:translate-x-0 ${
          open ? 'translate-x-0' : '-translate-x-full'
        }`}
      >
        {/* Logo */}
        <div className="flex items-center justify-between h-16 px-5 border-b border-slate-700/50">
          <div className="flex items-center gap-2 font-display text-lg font-bold">
            <Sprout className="w-6 h-6 text-leaf-400" />
            <span>AgriConnect</span>
          </div>
          <button onClick={onClose} className="lg:hidden p-1 hover:bg-slate-700 rounded-lg">
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Admin badge */}
        <div className="px-5 py-4">
          <div className="flex items-center gap-3 px-3 py-2.5 bg-slate-800 rounded-xl">
            <div className="w-9 h-9 rounded-full bg-gradient-to-br from-leaf-400 to-leaf-600 flex items-center justify-center text-sm font-bold">
              {user?.avatar || 'A'}
            </div>
            <div className="min-w-0">
              <p className="text-sm font-semibold truncate">{user?.name || 'Admin'}</p>
              <p className="text-xs text-slate-400 truncate">{user?.email || 'admin@demo.com'}</p>
            </div>
          </div>
        </div>

        {/* Nav items */}
        <nav className="px-3 space-y-1">
          {sidebarItems.map((item) => {
            const active = location.pathname === item.path
            return (
              <NavLink
                key={item.path}
                to={item.path}
                onClick={onClose}
                className={`flex items-center gap-3 px-4 py-3 rounded-xl text-sm font-medium transition-all duration-200 ${
                  active
                    ? 'bg-leaf-600/20 text-leaf-400'
                    : 'text-slate-300 hover:bg-slate-800 hover:text-white'
                }`}
              >
                <item.icon className={`w-5 h-5 ${active ? 'text-leaf-400' : ''}`} />
                {item.label}
                {active && (
                  <div className="ml-auto w-1.5 h-1.5 rounded-full bg-leaf-400" />
                )}
              </NavLink>
            )
          })}
        </nav>

        {/* Bottom - Logout */}
        <div className="absolute bottom-0 left-0 right-0 p-4 border-t border-slate-700/50 space-y-2">
          <button
            onClick={handleLogout}
            className="w-full flex items-center justify-center gap-2 px-4 py-2.5 bg-red-600/20 hover:bg-red-600/30 rounded-xl text-sm text-red-400 transition-colors font-medium"
          >
            <LogOut className="w-4 h-4" />
            Sign Out
          </button>
        </div>
      </aside>
    </>
  )
}
