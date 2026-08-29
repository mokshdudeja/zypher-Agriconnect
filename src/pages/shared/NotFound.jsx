import { Link } from 'react-router-dom'
import { Sprout, ArrowLeft } from 'lucide-react'

export default function NotFound() {
  return (
    <div className="min-h-screen bg-gradient-to-br from-earth-50 via-white to-leaf-50 flex items-center justify-center px-4">
      <div className="text-center animate-fade-in-up">
        <div className="w-16 h-16 bg-gradient-to-br from-leaf-500 to-leaf-700 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
          <Sprout className="w-9 h-9 text-white" />
        </div>
        <p className="font-display text-sm font-bold text-leaf-600 mb-2 tracking-wide uppercase">AgriConnect</p>
        <div className="text-7xl mb-4">🌾</div>
        <h1 className="font-display text-6xl font-bold text-slate-800">404</h1>
        <p className="text-slate-500 mt-3 text-lg">This page doesn't exist in our fields.</p>
        <div className="mt-8 flex gap-3 justify-center">
          <button
            onClick={() => window.history.back()}
            className="flex items-center gap-2 px-5 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" /> Go Back
          </button>
          <Link
            to="/"
            className="flex items-center gap-2 px-5 py-2.5 bg-leaf-600 text-white rounded-xl text-sm font-bold hover:bg-leaf-700 transition-colors"
          >
            <Sprout className="w-4 h-4" /> Home
          </Link>
        </div>
      </div>
    </div>
  )
}
