import { Link } from 'react-router-dom'
import { Sprout, Tractor, Store, ShoppingBag, Shield } from 'lucide-react'

const roles = [
  {
    id: 'farmer',
    title: 'Farmer',
    description: 'List your crops, manage harvests, and connect directly with buyers.',
    icon: Tractor,
    path: '/farmer',
    gradient: 'from-leaf-500 to-leaf-700',
    bgLight: 'bg-leaf-50',
    borderColor: 'border-leaf-200',
    iconColor: 'text-leaf-600',
  },
  {
    id: 'wholesaler',
    title: 'Wholesaler / Retailer',
    description: 'Browse fresh produce, place bids, and manage your bulk inventory.',
    icon: Store,
    path: '/wholesaler',
    gradient: 'from-harvest-500 to-harvest-700',
    bgLight: 'bg-harvest-50',
    borderColor: 'border-harvest-200',
    iconColor: 'text-harvest-600',
  },
  {
    id: 'consumer',
    title: 'Consumer',
    description: 'Shop farm-fresh produce delivered directly to your doorstep.',
    icon: ShoppingBag,
    path: '/consumer',
    gradient: 'from-sky-500 to-sky-700',
    bgLight: 'bg-sky-50',
    borderColor: 'border-sky-200',
    iconColor: 'text-sky-600',
  },
  {
    id: 'admin',
    title: 'Admin',
    description: 'Monitor platform activity, manage users, and review analytics.',
    icon: Shield,
    path: '/admin',
    gradient: 'from-slate-700 to-slate-900',
    bgLight: 'bg-slate-50',
    borderColor: 'border-slate-200',
    iconColor: 'text-slate-600',
  },
]

export default function RoleSelection() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-earth-50 via-white to-leaf-50 flex flex-col">
      {/* Hero */}
      <div className="flex-1 flex flex-col items-center justify-center px-4 py-12">
        {/* Logo */}
        <div className="animate-fade-in-up flex items-center gap-3 mb-2">
          <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-leaf-500 to-leaf-700 flex items-center justify-center shadow-lg">
            <Sprout className="w-8 h-8 text-white" />
          </div>
        </div>
        <h1 className="animate-fade-in-up delay-1 font-display text-4xl sm:text-5xl font-bold text-slate-900 text-center mt-4">
          AgriConnect
        </h1>
        <p className="animate-fade-in-up delay-2 text-lg text-slate-500 mt-3 text-center max-w-md font-medium">
          Farm to table marketplace — connecting growers, traders, and consumers.
        </p>

        {/* Role Cards */}
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 mt-12 w-full max-w-2xl">
          {roles.map((role, i) => (
            <Link
              key={role.id}
              to={role.path}
              className={`animate-fade-in-up delay-${i + 3} group relative overflow-hidden rounded-2xl border-2 ${role.borderColor} ${role.bgLight} p-6 transition-all duration-300 hover:shadow-elevated hover:-translate-y-1`}
            >
              {/* Glow Effect */}
              <div className={`absolute -top-12 -right-12 w-32 h-32 rounded-full bg-gradient-to-br ${role.gradient} opacity-5 group-hover:opacity-10 transition-opacity duration-500`} />

              <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${role.gradient} flex items-center justify-center mb-4 shadow-md group-hover:scale-105 transition-transform duration-300`}>
                <role.icon className="w-6 h-6 text-white" />
              </div>
              <h2 className="font-display text-xl font-bold text-slate-800 group-hover:text-slate-900">
                {role.title}
              </h2>
              <p className="text-sm text-slate-500 mt-1.5 leading-relaxed">
                {role.description}
              </p>
              <div className={`mt-4 text-sm font-semibold ${role.iconColor} flex items-center gap-1 group-hover:gap-2 transition-all`}>
                Enter Dashboard
                <span className="transition-transform group-hover:translate-x-1">→</span>
              </div>
            </Link>
          ))}
        </div>
      </div>

      {/* Footer */}
      <footer className="text-center py-6 text-xs text-slate-400">
        © 2026 AgriConnect by Zypher — Farm to Table Marketplace
      </footer>
    </div>
  )
}
