import { Navigate } from 'react-router-dom'
import { useAuth } from '../context/AuthContext'

/**
 * ProtectedRoute - wraps routes that require authentication.
 * Redirects to /login if not authenticated.
 * Optionally checks allowed roles.
 */
export default function ProtectedRoute({ children, allowedRoles }) {
  const { user, loading } = useAuth()

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-earth-50">
        <div className="flex flex-col items-center gap-3">
          <div className="w-10 h-10 border-3 border-leaf-200 border-t-leaf-600 rounded-full animate-spin" />
          <p className="text-sm text-slate-500 font-medium">Loading...</p>
        </div>
      </div>
    )
  }

  if (!user) {
    return <Navigate to="/login" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    // Redirect to user's own dashboard if they try to access another role
    return <Navigate to={`/${user.role}`} replace />
  }

  return children
}
