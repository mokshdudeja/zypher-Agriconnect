import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sprout, User, Mail, Lock, Eye, EyeOff, Phone, ArrowRight, Tractor, Store, ShoppingBag, Check, CheckCircle2 } from 'lucide-react'
import { useAuth } from '../context/AuthContext'

const roles = [
  { id: 'farmer', label: 'Farmer', desc: 'List & sell your crops', icon: Tractor, color: 'leaf', gradient: 'from-leaf-500 to-leaf-700' },
  { id: 'wholesaler', label: 'Wholesaler', desc: 'Buy in bulk & resell', icon: Store, color: 'harvest', gradient: 'from-harvest-500 to-harvest-700' },
  { id: 'consumer', label: 'Consumer', desc: 'Shop fresh produce', icon: ShoppingBag, color: 'sky', gradient: 'from-sky-500 to-sky-700' },
]

export default function Register() {
  const [step, setStep] = useState(1) // 1 = role selection, 2 = details
  const [selectedRole, setSelectedRole] = useState('')
  const [name, setName] = useState('')
  const [email, setEmail] = useState('')
  const [phone, setPhone] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [isSubmitting, setIsSubmitting] = useState(false)
  const { register } = useAuth()
  const navigate = useNavigate()

  const handleRoleSelect = (role) => {
    setSelectedRole(role)
    setStep(2)
    setError('')
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')

    if (!name || !email || !password) {
      setError('Please fill in all required fields')
      return
    }
    if (password.length < 6) {
      setError('Password must be at least 6 characters')
      return
    }
    if (password !== confirmPassword) {
      setError('Passwords do not match')
      return
    }

    setIsSubmitting(true)

    const result = await register({ name, email, password, role: selectedRole, phone })
    
    if (result.success) {
      if (result.needsVerification) {
        setStep(3) // New step for "Check Email"
      } else {
        navigate(`/${result.user.role}`)
      }
    } else {
      setError(result.error)
    }
    
    setIsSubmitting(false)
  }

  return (
    <div className="min-h-screen bg-gradient-to-br from-earth-50 via-white to-leaf-50 flex">
      {/* Left Panel */}
      <div className="hidden lg:flex lg:w-1/2 bg-gradient-to-br from-leaf-600 via-leaf-700 to-leaf-800 relative overflow-hidden">
        <div className="absolute inset-0">
          <div className="absolute -top-20 -right-20 w-96 h-96 rounded-full bg-white/5" />
          <div className="absolute -bottom-32 -left-32 w-[500px] h-[500px] rounded-full bg-white/5" />
        </div>
        <div className="relative z-10 flex flex-col justify-center px-16 text-white">
          <div className="flex items-center gap-3 mb-8">
            <div className="w-14 h-14 rounded-2xl bg-white/15 backdrop-blur-sm flex items-center justify-center">
              <Sprout className="w-8 h-8" />
            </div>
            <span className="font-display text-3xl font-bold">AgriConnect</span>
          </div>
          <h1 className="font-display text-4xl font-bold leading-tight">
            Join the Future of<br />
            <span className="text-leaf-200">Agriculture</span>
          </h1>
          <p className="text-leaf-200 mt-4 text-lg leading-relaxed max-w-md">
            Create your account and start connecting with the agricultural community today.
          </p>

          {/* Benefits */}
          <div className="mt-10 space-y-4">
            {[
              'Direct access to verified farmers & buyers',
              'Real-time market prices & analytics',
              'Secure transactions with quality guarantee'
            ].map((benefit, i) => (
              <div key={i} className="flex items-center gap-3">
                <div className="w-6 h-6 rounded-full bg-leaf-400/30 flex items-center justify-center shrink-0">
                  <Check className="w-3.5 h-3.5 text-leaf-200" />
                </div>
                <p className="text-sm text-leaf-100">{benefit}</p>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Right Panel */}
      <div className="flex-1 flex items-center justify-center px-4 sm:px-8 py-12 overflow-y-auto">
        <div className="w-full max-w-md">
          {/* Mobile Logo */}
          <div className="lg:hidden flex items-center gap-2 mb-8 justify-center">
            <div className="w-12 h-12 rounded-2xl bg-gradient-to-br from-leaf-500 to-leaf-700 flex items-center justify-center shadow-lg">
              <Sprout className="w-7 h-7 text-white" />
            </div>
            <span className="font-display text-2xl font-bold text-slate-800">AgriConnect</span>
          </div>

          {/* Step 1: Role Selection */}
          {step === 1 && (
            <div className="animate-fade-in-up">
              <h2 className="font-display text-3xl font-bold text-slate-800">Create Account</h2>
              <p className="text-slate-500 mt-2">Choose your role to get started</p>

              <div className="mt-8 space-y-3">
                {roles.map((role) => (
                  <button
                    key={role.id}
                    onClick={() => handleRoleSelect(role.id)}
                    className={`w-full flex items-center gap-4 p-5 rounded-2xl border-2 transition-all duration-300 hover:-translate-y-0.5 hover:shadow-card-hover text-left ${
                      `border-${role.color}-200 bg-${role.color}-50/50 hover:border-${role.color}-400`
                    }`}
                  >
                    <div className={`w-12 h-12 rounded-xl bg-gradient-to-br ${role.gradient} flex items-center justify-center shadow-md`}>
                      <role.icon className="w-6 h-6 text-white" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800 text-lg">{role.label}</p>
                      <p className="text-sm text-slate-500">{role.desc}</p>
                    </div>
                    <ArrowRight className="w-5 h-5 text-slate-400 ml-auto" />
                  </button>
                ))}
              </div>

              <p className="text-center text-sm text-slate-500 mt-8">
                Already have an account?{' '}
                <Link to="/login" className="text-leaf-600 font-semibold hover:text-leaf-700">
                  Sign In
                </Link>
              </p>
            </div>
          )}

          {/* Step 2: Registration Form */}
          {step === 2 && (
            <div className="animate-fade-in-up">
              <button
                onClick={() => { setStep(1); setError('') }}
                className="text-sm text-slate-500 hover:text-slate-800 mb-4 flex items-center gap-1 transition-colors"
              >
                ← Change Role
              </button>

              <h2 className="font-display text-3xl font-bold text-slate-800">
                Register as {selectedRole.charAt(0).toUpperCase() + selectedRole.slice(1)}
              </h2>
              <p className="text-slate-500 mt-1">Fill in your details to create your account</p>

              <form onSubmit={handleSubmit} className="mt-6 space-y-4">
                {error && (
                  <div className="px-4 py-3 bg-red-50 border border-red-200 rounded-xl text-sm text-red-600 font-medium animate-scale-in">
                    {error}
                  </div>
                )}

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Full Name *</label>
                  <div className="relative">
                    <User className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                      type="text"
                      value={name}
                      onChange={e => setName(e.target.value)}
                      placeholder="Enter your full name"
                      className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-transparent shadow-sm"
                      autoComplete="name"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Email *</label>
                  <div className="relative">
                    <Mail className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                      type="email"
                      value={email}
                      onChange={e => setEmail(e.target.value)}
                      placeholder="Enter your email"
                      className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-transparent shadow-sm"
                      autoComplete="email"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Phone <span className="text-slate-400 font-normal">(optional)</span></label>
                  <div className="relative">
                    <Phone className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                      type="tel"
                      value={phone}
                      onChange={e => setPhone(e.target.value)}
                      placeholder="Enter phone number"
                      className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-transparent shadow-sm"
                      autoComplete="tel"
                    />
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Password *</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={password}
                      onChange={e => setPassword(e.target.value)}
                      placeholder="Min 6 characters"
                      className="w-full pl-11 pr-12 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-transparent shadow-sm"
                      autoComplete="new-password"
                    />
                    <button
                      type="button"
                      onClick={() => setShowPassword(!showPassword)}
                      className="absolute right-3.5 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600"
                    >
                      {showPassword ? <EyeOff className="w-5 h-5" /> : <Eye className="w-5 h-5" />}
                    </button>
                  </div>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Confirm Password *</label>
                  <div className="relative">
                    <Lock className="absolute left-3.5 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
                    <input
                      type={showPassword ? 'text' : 'password'}
                      value={confirmPassword}
                      onChange={e => setConfirmPassword(e.target.value)}
                      placeholder="Re-enter your password"
                      className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-transparent shadow-sm"
                      autoComplete="new-password"
                    />
                  </div>
                  {confirmPassword && password !== confirmPassword && (
                    <p className="text-xs text-red-500 mt-1">Passwords don't match</p>
                  )}
                </div>

                <div className="pt-1">
                  <label className="flex items-start gap-2 cursor-pointer">
                    <input type="checkbox" className="w-4 h-4 mt-0.5 rounded border-slate-300 text-leaf-600 focus:ring-leaf-500" />
                    <span className="text-sm text-slate-500">
                      I agree to the <span className="text-leaf-600 font-semibold">Terms of Service</span> and <span className="text-leaf-600 font-semibold">Privacy Policy</span>
                    </span>
                  </label>
                </div>

                <button
                  type="submit"
                  disabled={isSubmitting}
                  className="w-full flex items-center justify-center gap-2 py-3.5 bg-leaf-600 hover:bg-leaf-700 text-white font-bold rounded-xl shadow-md hover:shadow-lg transition-all duration-200 active:scale-[0.98] disabled:opacity-60 disabled:cursor-not-allowed"
                >
                  {isSubmitting ? (
                    <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  ) : (
                    <>Create Account <ArrowRight className="w-5 h-5" /></>
                  )}
                </button>
              </form>

              <p className="text-center text-sm text-slate-500 mt-6">
                Already have an account?{' '}
                <Link to="/login" className="text-leaf-600 font-semibold hover:text-leaf-700">
                  Sign In
                </Link>
              </p>
            </div>
          )}
          {/* Step 3: Verification Sent */}
          {step === 3 && (
            <div className="animate-fade-in-up text-center">
              <div className="w-20 h-20 bg-leaf-50 rounded-3xl flex items-center justify-center mx-auto mb-6 text-leaf-600">
                <Mail className="w-10 h-10" />
              </div>
              <h2 className="font-display text-3xl font-bold text-slate-800">Check your Email</h2>
              <p className="text-slate-500 mt-4 leading-relaxed">
                We've sent a verification link to <span className="font-semibold text-slate-800">{email}</span>. 
                Please click the link to activate your account.
              </p>
              <p className="text-xs text-amber-600 font-medium mt-2 bg-amber-50 py-2 px-4 rounded-lg inline-block">
                Tip: If you don't see it, please check your <span className="font-bold uppercase tracking-wider">spam folder</span>.
              </p>
              
              <div className="mt-10 space-y-4">
                <Link
                  to="/login"
                  className="w-full flex items-center justify-center gap-2 py-3.5 bg-leaf-600 hover:bg-leaf-700 text-white font-bold rounded-xl shadow-md transition-all duration-200"
                >
                  Back to Login
                </Link>
                <button
                  onClick={() => setStep(1)}
                  className="text-sm font-semibold text-slate-500 hover:text-slate-800 transition-colors"
                >
                  Didn't get the email? Try again
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
