/* Reusable UI components */

export function StatCard({ icon, label, value, trend, color = 'bg-white', delay = 0 }) {
  return (
    <div className={`${color} rounded-2xl p-5 shadow-card hover:shadow-card-hover transition-all duration-300 animate-fade-in-up delay-${delay}`}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm text-slate-500 font-medium">{label}</p>
          <p className="text-2xl font-display font-bold mt-1 text-slate-800">{value}</p>
          {trend && (
            <p className={`text-xs mt-1 font-semibold ${trend > 0 ? 'text-leaf-600' : 'text-red-500'}`}>
              {trend > 0 ? '↑' : '↓'} {Math.abs(trend)}% from last month
            </p>
          )}
        </div>
        {icon && (
          <div className="w-11 h-11 rounded-xl bg-slate-50 flex items-center justify-center text-slate-600">
            {icon}
          </div>
        )}
      </div>
    </div>
  )
}

export function Badge({ children, variant = 'default' }) {
  const variants = {
    default: 'bg-slate-100 text-slate-700',
    success: 'bg-leaf-100 text-leaf-700',
    warning: 'bg-harvest-100 text-harvest-700',
    danger: 'bg-red-100 text-red-700',
    info: 'bg-sky-100 text-sky-700',
    pending: 'bg-amber-100 text-amber-700',
  }
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-semibold ${variants[variant]}`}>
      {children}
    </span>
  )
}

export function EmptyState({ icon, title, description, action }) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-4 text-center animate-fade-in">
      {icon && <div className="text-slate-300 mb-4">{icon}</div>}
      <h3 className="font-display text-lg font-semibold text-slate-700">{title}</h3>
      <p className="text-sm text-slate-500 mt-1 max-w-sm">{description}</p>
      {action && <div className="mt-4">{action}</div>}
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="bg-white rounded-2xl p-5 shadow-card">
      <div className="skeleton h-4 w-24 mb-3" />
      <div className="skeleton h-8 w-32 mb-2" />
      <div className="skeleton h-3 w-20" />
    </div>
  )
}

export function SkeletonRow() {
  return (
    <div className="flex items-center gap-4 p-4 border-b border-slate-100">
      <div className="skeleton h-10 w-10 rounded-full" />
      <div className="flex-1 space-y-2">
        <div className="skeleton h-4 w-40" />
        <div className="skeleton h-3 w-24" />
      </div>
      <div className="skeleton h-6 w-20 rounded-full" />
    </div>
  )
}

export function Button({ children, variant = 'primary', size = 'md', className = '', ...props }) {
  const base = 'inline-flex items-center justify-center gap-2 font-semibold rounded-xl transition-all duration-200 active:scale-[0.97] disabled:opacity-50 disabled:cursor-not-allowed'
  const variants = {
    primary: 'bg-leaf-600 text-white hover:bg-leaf-700 shadow-sm hover:shadow-md',
    secondary: 'bg-white text-slate-700 border border-slate-200 hover:bg-slate-50 shadow-sm',
    danger: 'bg-red-600 text-white hover:bg-red-700 shadow-sm',
    ghost: 'text-slate-600 hover:bg-slate-100',
    harvest: 'bg-harvest-600 text-white hover:bg-harvest-700 shadow-sm hover:shadow-md',
    sky: 'bg-sky-600 text-white hover:bg-sky-700 shadow-sm hover:shadow-md',
  }
  const sizes = {
    sm: 'px-3 py-1.5 text-xs',
    md: 'px-4 py-2.5 text-sm',
    lg: 'px-6 py-3 text-base',
    xl: 'px-8 py-4 text-lg',
  }
  return (
    <button className={`${base} ${variants[variant]} ${sizes[size]} ${className}`} {...props}>
      {children}
    </button>
  )
}

export function Card({ children, className = '', hover = true }) {
  return (
    <div className={`bg-white rounded-2xl shadow-card ${hover ? 'hover:shadow-card-hover' : ''} transition-all duration-300 ${className}`}>
      {children}
    </div>
  )
}
