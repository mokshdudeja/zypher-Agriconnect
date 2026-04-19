import { useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Star, Leaf, MapPin, Truck, ShieldCheck, Minus, Plus, ShoppingCart, Heart } from 'lucide-react'
import { Button } from '../../components/ui'
import { consumerProducts } from '../../data/mockData'

export default function ProductDetails() {
  const { id } = useParams()
  const product = consumerProducts.find(p => p.id === parseInt(id))
  const [qty, setQty] = useState(1)
  const [addedToCart, setAddedToCart] = useState(false)
  const [liked, setLiked] = useState(false)

  if (!product) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-20 text-center">
        <p className="text-slate-500">Product not found</p>
        <Link to="/consumer/products" className="text-sky-600 font-semibold mt-2 inline-block">← Back to products</Link>
      </div>
    )
  }

  const discount = Math.round(((product.originalPrice - product.price) / product.originalPrice) * 100)

  const handleAddToCart = () => {
    setAddedToCart(true)
    setTimeout(() => setAddedToCart(false), 2000)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      {/* Back */}
      <Link to="/consumer/products" className="inline-flex items-center gap-2 text-sm text-slate-500 hover:text-slate-800 mb-6 transition-colors">
        <ArrowLeft className="w-4 h-4" /> Back to Products
      </Link>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-8 animate-fade-in-up">
        {/* Product Image */}
        <div className="relative">
          <div className="aspect-square bg-gradient-to-br from-leaf-50 via-earth-50 to-sky-50 rounded-3xl flex items-center justify-center text-[120px] shadow-card">
            {product.image}
          </div>
          <button
            onClick={() => setLiked(!liked)}
            className={`absolute top-4 right-4 w-12 h-12 rounded-2xl flex items-center justify-center shadow-lg transition-all duration-300 ${
              liked ? 'bg-red-500 text-white scale-110' : 'bg-white/90 text-slate-400 hover:text-red-500'
            }`}
          >
            <Heart className={`w-6 h-6 ${liked ? 'fill-current' : ''}`} />
          </button>
          {product.organic && (
            <div className="absolute top-4 left-4 inline-flex items-center gap-1.5 px-3 py-1.5 bg-leaf-600 text-white rounded-xl text-sm font-semibold shadow-lg">
              <Leaf className="w-4 h-4" /> Organic
            </div>
          )}
        </div>

        {/* Product Info */}
        <div className="space-y-5">
          <div>
            <span className="text-sm text-sky-600 font-semibold uppercase tracking-wider">{product.category}</span>
            <h1 className="font-display text-3xl sm:text-4xl font-bold text-slate-800 mt-1">{product.name}</h1>
          </div>

          {/* Rating */}
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-0.5">
              {[1,2,3,4,5].map(s => (
                <Star key={s} className={`w-5 h-5 ${s <= Math.floor(product.rating) ? 'fill-amber-400 text-amber-400' : 'text-slate-200'}`} />
              ))}
            </div>
            <span className="text-sm font-semibold text-slate-600">{product.rating}</span>
            <span className="text-sm text-slate-400">({product.reviews} reviews)</span>
          </div>

          {/* Price */}
          <div className="flex items-end gap-3">
            <span className="text-4xl font-bold text-slate-800">₹{product.price}</span>
            <span className="text-xl text-slate-400 line-through">₹{product.originalPrice}</span>
            <span className="px-2.5 py-1 bg-leaf-100 text-leaf-700 rounded-lg text-sm font-bold">{discount}% off</span>
          </div>
          <p className="text-sm text-slate-500">per {product.unit}</p>

          {/* Farmer Info */}
          <div className="flex items-center gap-3 p-4 bg-earth-50 rounded-xl border border-earth-200">
            <div className="w-10 h-10 rounded-full bg-earth-200 flex items-center justify-center text-earth-700 font-bold">
              {product.farmer[0]}
            </div>
            <div>
              <p className="text-sm font-semibold text-slate-800">{product.farmer}</p>
              <p className="text-xs text-slate-500 flex items-center gap-1"><MapPin className="w-3 h-3" /> {product.location}</p>
            </div>
          </div>

          {/* Quantity */}
          <div>
            <p className="text-sm font-semibold text-slate-700 mb-2">Quantity</p>
            <div className="flex items-center gap-3">
              <button
                onClick={() => setQty(Math.max(1, qty - 1))}
                className="w-10 h-10 rounded-xl border border-slate-200 flex items-center justify-center hover:bg-slate-50 transition-colors"
              >
                <Minus className="w-4 h-4" />
              </button>
              <span className="text-lg font-bold w-8 text-center text-slate-800">{qty}</span>
              <button
                onClick={() => setQty(qty + 1)}
                className="w-10 h-10 rounded-xl border border-slate-200 flex items-center justify-center hover:bg-slate-50 transition-colors"
              >
                <Plus className="w-4 h-4" />
              </button>
              <span className="text-sm text-slate-400 ml-2">Total: ₹{product.price * qty}</span>
            </div>
          </div>

          {/* CTA Buttons */}
          <div className="flex gap-3 pt-2">
            <Button
              variant="sky"
              size="lg"
              className="flex-1"
              onClick={handleAddToCart}
            >
              <ShoppingCart className="w-5 h-5" />
              {addedToCart ? '✓ Added!' : 'Add to Cart'}
            </Button>
            <Button variant="primary" size="lg" className="flex-1">
              Buy Now
            </Button>
          </div>

          {/* Trust badges */}
          <div className="flex flex-wrap gap-4 pt-4 border-t border-slate-100">
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <Truck className="w-4 h-4 text-leaf-600" /> Free delivery over ₹499
            </div>
            <div className="flex items-center gap-2 text-sm text-slate-500">
              <ShieldCheck className="w-4 h-4 text-leaf-600" /> Quality guaranteed
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
