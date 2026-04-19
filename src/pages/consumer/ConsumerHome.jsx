import { Link } from 'react-router-dom'
import { ArrowRight, Leaf, Truck, Shield, Star, Camera } from 'lucide-react'
import { consumerProducts } from '../../data/mockData'

const categories = [
  { name: 'Grains', emoji: '🌾', color: 'bg-amber-50 border-amber-200' },
  { name: 'Vegetables', emoji: '🥬', color: 'bg-green-50 border-green-200' },
  { name: 'Fruits', emoji: '🍎', color: 'bg-red-50 border-red-200' },
  { name: 'Spices', emoji: '🌶️', color: 'bg-orange-50 border-orange-200' },
  { name: 'Other', emoji: '📦', color: 'bg-slate-50 border-slate-200' },
]

const features = [
  { icon: Leaf, title: 'Farm Fresh', desc: 'Direct from verified farmers', color: 'text-leaf-600 bg-leaf-50' },
  { icon: Truck, title: 'Fast Delivery', desc: 'Delivered within 24 hours', color: 'text-sky-600 bg-sky-50' },
  { icon: Shield, title: 'Quality Assured', desc: '100% certified organic options', color: 'text-harvest-600 bg-harvest-50' },
]

export default function ConsumerHome() {
  const featured = consumerProducts.slice(0, 4)

  return (
    <div>
      {/* Hero */}
      <section className="relative bg-gradient-to-br from-leaf-600 via-leaf-700 to-leaf-800 text-white overflow-hidden">
        <div className="absolute inset-0 opacity-10">
          <div className="absolute -top-20 -right-20 w-80 h-80 rounded-full bg-white/20" />
          <div className="absolute -bottom-10 -left-10 w-60 h-60 rounded-full bg-white/10" />
        </div>
        <div className="relative max-w-7xl mx-auto px-4 sm:px-6 py-16 sm:py-24">
          <div className="max-w-2xl animate-fade-in-up">
            <span className="inline-flex items-center gap-1.5 px-3 py-1 bg-white/15 rounded-full text-sm font-medium mb-4 backdrop-blur-sm">
              <Leaf className="w-4 h-4" /> Farm to Table
            </span>
            <h1 className="font-display text-4xl sm:text-5xl lg:text-6xl font-bold leading-tight">
              Fresh from the <br />
              <span className="text-leaf-200">Farm to Your Door</span>
            </h1>
            <p className="mt-4 text-lg text-leaf-100 max-w-lg leading-relaxed">
              Shop farm-fresh produce sourced directly from verified local farmers. Pure, organic, and delivered to your doorstep.
            </p>
            <div className="flex flex-wrap gap-3 mt-8">
              <Link
                to="/consumer/products"
                className="inline-flex items-center gap-2 px-6 py-3.5 bg-white text-leaf-700 rounded-xl font-bold shadow-lg hover:shadow-xl hover:-translate-y-0.5 transition-all duration-300"
              >
                Shop Now <ArrowRight className="w-5 h-5" />
              </Link>
              <button className="px-6 py-3.5 border-2 border-white/30 text-white rounded-xl font-bold hover:bg-white/10 transition-all">
                Explore Categories
              </button>
            </div>
          </div>
        </div>
      </section>

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {features.map((f, i) => (
            <div key={f.title} className={`flex items-center gap-4 p-5 rounded-2xl bg-white shadow-card hover:shadow-card-hover transition-all duration-300 animate-fade-in-up delay-${i + 1}`}>
              <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${f.color}`}>
                <f.icon className="w-6 h-6" />
              </div>
              <div>
                <p className="font-semibold text-slate-800">{f.title}</p>
                <p className="text-sm text-slate-500">{f.desc}</p>
              </div>
            </div>
          ))}
        </div>
      </section>

      {/* Categories */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
        <h2 className="font-display text-2xl font-bold text-slate-800 mb-5 animate-fade-in-up">Shop by Category</h2>
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none animate-fade-in-up delay-1">
          {categories.map((cat) => (
            <Link
              key={cat.name}
              to="/consumer/products"
              className={`shrink-0 flex flex-col items-center gap-2 px-6 py-4 rounded-2xl border-2 ${cat.color} hover:shadow-card-hover transition-all duration-300 hover:-translate-y-0.5`}
            >
              <span className="text-3xl">{cat.emoji}</span>
              <span className="text-sm font-semibold text-slate-700">{cat.name}</span>
            </Link>
          ))}
        </div>
      </section>

      {/* Featured Products */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8 pb-16">
        <div className="flex items-center justify-between mb-5 animate-fade-in-up">
          <h2 className="font-display text-2xl font-bold text-slate-800">Featured Products</h2>
          <Link to="/consumer/products" className="text-sm font-semibold text-leaf-600 hover:text-leaf-700 flex items-center gap-1">
            View All <ArrowRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
          {featured.map((product, i) => (
            <Link
              key={product.id}
              to={`/consumer/products/${product.id}`}
              className={`bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 overflow-hidden group animate-fade-in-up delay-${i + 2}`}
            >
              {/* Image Placeholder */}
              <div className="h-40 bg-gradient-to-br from-leaf-50 to-earth-50 flex items-center justify-center text-5xl group-hover:scale-105 transition-transform duration-500">
                {product.image}
              </div>
              <div className="p-4">
                {product.organic && (
                  <span className="inline-flex items-center gap-1 px-2 py-0.5 bg-leaf-100 text-leaf-700 rounded-full text-xs font-semibold mb-2">
                    <Leaf className="w-3 h-3" /> Organic
                  </span>
                )}
                <h3 className="font-semibold text-slate-800 text-sm leading-tight">{product.name}</h3>
                <p className="text-xs text-slate-400 mt-0.5">{product.farmer}</p>
                <div className="flex items-center gap-1 mt-2">
                  <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                  <span className="text-xs font-semibold text-slate-600">{product.rating}</span>
                  <span className="text-xs text-slate-400">({product.reviews})</span>
                </div>
                <div className="flex items-center gap-2 mt-2">
                  <span className="text-lg font-bold text-slate-800">₹{product.price}</span>
                  <span className="text-sm text-slate-400 line-through">₹{product.originalPrice}</span>
                </div>
              </div>
            </Link>
          ))}
        </div>
      </section>
      {/* Floating Action Button for QR Scanner */}
      <Link 
        to="/scan"
        className="fixed bottom-6 right-6 w-16 h-16 bg-leaf-600 text-white rounded-full shadow-2xl flex items-center justify-center hover:bg-leaf-700 hover:scale-110 active:scale-95 transition-all z-40 group"
      >
        <Camera className="w-7 h-7" />
        <span className="absolute right-full mr-3 px-3 py-1.5 bg-slate-800 text-white text-xs font-bold rounded-lg opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap pointer-events-none">
          Scan Crop QR
        </span>
      </Link>
    </div>
  )
}
