import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sprout, Mail, Lock, Eye, EyeOff, ArrowRight, Tractor, Store, ShoppingBag, Shield } from 'lucide-react'
import { useAuth } from '../context/AuthContext'
import { toast } from 'react-hot-toast'



export default function Login() {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { login, resendVerification } = useAuth()
  const navigate = useNavigate()
  const [resending, setResending] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!email || !password) {
      setError('Please fill in all fields')
      return
    }

    setIsSubmitting(true)

    const result = await login(email, password)
    
    if (result.success) {
      const rolePath = `/${result.user.role}`
      navigate(rolePath)
    } else if (result.error === 'verification_required') {
      setError('verification_required')
    } else {
      setError(result.error)
    }
    
    setIsSubmitting(false)
  }

  const handleResend = async () => {
    setResending(true)
    const result = await resendVerification(email, password)
    if (result.success) {
      toast.success('Verification email sent!')
    } else {
      toast.error(result.error)
    }
    setResending(false)
  }



  return (
    <div className="min-h-screen bg-gradient-to-br from-earth-50 via-white to-leaf-50 flex">
      {/* Left Panel - Decorative */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-leaf-600 via-leaf-700 to-leaf-800 relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute -top-20 -right-20 w-96 h-96 rounded-full bg-white/5" />
          <div className="absolute -bottom-32 -left-32 w-[500px] h-[500px] rounded-full bg-white/5" />
          <div className="absolute top-1/3 right-1/4 w-60 h-60 rounded-full bg-leaf-500/20" />
        </div>
        <div className="relative z-10 flex flex-col justify-center px-16 text-white">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center">
              <Sprout className="w-8 h-8" />
            </div>
            <span className="font-display text-3xl font-bold">AgriConnect</span>
          </div>
          <h1 className="font-display text-4xl font-bold leading-tight">
            Farm to Table<br />
            <span className="text-leaf-200">Marketplace</span>
          </h1>
          <p className="text-leaf-200 mt-4 text-lg leading-relaxed max-w-md">
            Connect with local farmers, access fresh produce, and build a sustainable food ecosystem — all from one platform.
          </p>

          {/* Trust indicators */}
          <div className="flex gap-8 mt-12">
            <div>
              <p className="text-3xl font-display font-bold">12K+</p>
              <p className="text-sm text-leaf-200">Active Users</p>
            </div>
            <div>
              <p className="text-3xl font-display font-bold">3.2K</p>
              <p className="text-sm text-leaf-200">Farmers</p>
            </div>
            <div>
              <p className="text-3xl font-display font-bold">₹2.4Cr</p>
              <p className="text-sm text-leaf-200">Traded</p>
            </div>
          </div>
        </div>
      </div>

      {/* Right Panel - Login Form */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-8 py-12">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-leaf-500 to-leaf-700 flex items-center justify-center shadow-lg">
              <Sprout className="w-7 h-7 text-white" />
            </div>
            <span className="font-display text-2xl font-bold text-slate-800">AgriConnect</span>
          </div>

          <div className="animate-fade-in-up">
            <h2 className="font-display text-3xl font-bold text-slate-800">Welcome back</h2>
            <p className="text-slate-500 mt-2">Sign in to your account to continue</p>
          </div>

          {/* Login Form */}
          <form onSubmit={handleSubmit} className="mt-8 space-y-4 animate-fade-in-up delay-1">
            {error && error !== 'verification_required' && (
              <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600 font-medium animate-scale-in">
                {error}
              </div>
            )}

            {error === 'verification_required' && (
              <div className="px-5 py-4 bg-amber-50 border border-amber-200 rounded-2xl animate-scale-in">
                <div className="flex items-start gap-3">
                  <Mail className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
                  <div>
                    <p className="text-sm font-bold text-amber-900">Email not verified</p>
                    <p className="text-xs text-amber-700 mt-1 leading-relaxed">
                      Please check your inbox and click the verification link to proceed.
                    </p>
                    <button
                      type="button"
                      onClick={handleResend}
                      disabled={resending}
                      className="mt-3 text-xs font-bold text-amber-900 underline underline-offset-2 hover:text-amber-800 disabled:opacity-50"
                    >
                      {resending ? 'Sending...' : 'Resend verification link'}
                    </button>
                  </div>
                </div>
              </div>
            )}

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email</label>
              <div className="relative">
                <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  placeholder="Enter your email"
                  className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-transparent shadow-sm transition-all"
                  autoComplete="email"
                />
              </div>
            </div>

            <div>
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Password</label>
              <div className="relative">
                <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                <input
                  type={showPassword ? 'text' : 'password'}
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="Enter your password"
                  className="w-full pl-11 pr-12 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-transparent shadow-sm transition-all"
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 transition-colors"
                >
                  {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                </button>
              </div>
            </div>

            <div className="flex items-center justify-between pt-1">
              <label className="flex items-center gap-2 cursor-pointer">
                <input type="checkbox" className="w-4 h-4 rounded border-slate-300 text-leaf-600 focus:ring-leaf-500" />
                <span className="text-sm text-slate-600">Remember me</span>
              </label>
              <button type="button" className="text-sm font-semibold text-leaf-600 hover:text-leaf-700">
                Forgot password?
              </button>
            </div>

            <button
              type="submit"
              disabled={isSubmitting}
              className="w-full flex items-center justify-center gap-2 py-3.5 bg-leaf-600 hover:bg-leaf-700 text-white font-bold rounded-xl shadow-md hover:shadow-lg transition-all duration-200 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
            >
              {isSubmitting ? (
                <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
              ) : (
                <>Sign In <ArrowRight className="w-5 h-5" /></>
              )}
            </button>
          </form>

          <p className="text-center text-sm text-slate-500 mt-6 animate-fade-in-up delay-3">
            Don't have an account?{' '}
            <Link to="/register" className="text-leaf-600 font-semibold hover:text-leaf-700">
              Create Account
            </Link>
          </p>
        </div>
      </div>
    </div>
  )
}
