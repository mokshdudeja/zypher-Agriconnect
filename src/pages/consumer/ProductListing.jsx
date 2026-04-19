import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Search, SlidersHorizontal, Star, Leaf, ShoppingCart, Loader2 } from 'lucide-react'
import { db } from '../../lib/firebase'
import { collection, query, getDocs, orderBy } from 'firebase/firestore'
import { useEffect } from 'react'

export default function ProductListing() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true)
        // 1. Fetch crops
        const cropsSnap = await getDocs(query(collection(db, 'crops'), orderBy('created_at', 'desc')))
        const cropsData = cropsSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))

        // 2. Fetch profiles
        const profilesSnap = await getDocs(collection(db, 'profiles'))
        const profilesMap = {}
        profilesSnap.docs.forEach(doc => {
          profilesMap[doc.id] = doc.data()
        })
        
        // Map fields to component expectations
        const mappedData = cropsData.map(item => ({
          ...item,
          farmer: profilesMap[item.farmer_id]?.name || 'Local Farmer',
          image: item.name.toLowerCase().includes('wheat') ? '🌾' : 
                 item.name.toLowerCase().includes('rice') ? '🍚' : 
                 item.name.toLowerCase().includes('corn') ? '🌽' : '🥦',
          rating: (4.5 + Math.random() * 0.5).toFixed(1), // Mock rating for UI
          reviews: Math.floor(Math.random() * 100) + 10,  // Mock reviews for UI
          originalPrice: (item.price * 1.2).toFixed(0),   // Mock original price
          organic: true
        }))

        setProducts(mappedData)
      } catch (err) {
        console.error('Fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchProducts()
  }, [])

  const categories = ['All', 'Grains', 'Vegetables', 'Fruits', 'Spices', 'Other']
  const filtered = products.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(search.toLowerCase())
    const matchCat = category === 'All' // Add real category mapping later if needed
    return matchSearch && matchCat
  })

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="animate-fade-in-up">
          <h1 className="font-display text-3xl font-bold text-slate-800">Fresh Produce</h1>
          <p className="text-slate-500 mt-1">{filtered.length} products available</p>
        </div>

        {/* Search + Filter */}
        <div className="flex flex-col sm:flex-row gap-3 animate-fade-in-up delay-1">
          <div className="relative flex-1">
            <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
            <input
              type="text"
              value={search}
              onChange={e => setSearch(e.target.value)}
              placeholder="Search products..."
              className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-sm"
            />
          </div>
          <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
            {categories.map(cat => (
              <button
                key={cat}
                onClick={() => setCategory(cat)}
                className={`shrink-0 px-4 py-2.5 rounded-xl text-sm font-semibold transition-all ${
                  category === cat
                    ? 'bg-sky-600 text-white shadow-md'
                    : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
                }`}
              >
                {cat}
              </button>
            ))}
          </div>
        </div>

        {/* Product Grid */}
        {loading ? (
          <div className="flex justify-center py-20">
            <Loader2 className="w-10 h-10 text-sky-600 animate-spin" />
          </div>
        ) : filtered.length > 0 ? (
          <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-4 gap-4">
            {filtered.map((product, i) => (
              <Link
                key={product.id}
                to={`/consumer/products/${product.id}`}
                className={`bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 overflow-hidden group animate-fade-in-up`}
              >
                <div className="relative h-44 bg-gradient-to-br from-slate-50 to-leaf-50/30 flex items-center justify-center text-5xl group-hover:scale-105 transition-transform duration-500">
                  {product.image}
                  {product.organic && (
                    <span className="absolute top-2 left-2 inline-flex items-center gap-1 px-2 py-0.5 bg-leaf-600 text-white rounded-full text-xs font-semibold">
                      <Leaf className="w-3 h-3" /> Organic
                    </span>
                  )}
                  <span className="absolute top-2 right-2 px-2 py-0.5 bg-white/90 text-xs font-semibold text-slate-600 rounded-full shadow-sm">
                    {product.unit}
                  </span>
                </div>
                <div className="p-4">
                  <h3 className="font-semibold text-slate-800 text-sm leading-tight line-clamp-2">{product.name}</h3>
                  <p className="text-xs text-slate-400 mt-1">{product.farmer} · {product.location}</p>
                  <div className="flex items-center gap-1 mt-2">
                    <Star className="w-3.5 h-3.5 fill-amber-400 text-amber-400" />
                    <span className="text-xs font-semibold text-slate-600">{product.rating}</span>
                    <span className="text-xs text-slate-400">({product.reviews})</span>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <div>
                      <span className="text-lg font-bold text-slate-800">₹{product.price}</span>
                      <span className="text-sm text-slate-400 line-through ml-1.5">₹{product.originalPrice}</span>
                    </div>
                    <div className="w-9 h-9 rounded-xl bg-sky-50 flex items-center justify-center text-sky-600 group-hover:bg-sky-600 group-hover:text-white transition-colors">
                      <ShoppingCart className="w-4 h-4" />
                    </div>
                  </div>
                </div>
              </Link>
            ))}
          </div>
        ) : (
          <div className="bg-white rounded-3xl p-12 text-center border-2 border-dashed border-slate-200">
            <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
              <Search className="w-8 h-8 text-slate-300" />
            </div>
            <h3 className="font-display text-xl font-bold text-slate-800">No products found</h3>
            <p className="text-slate-500 max-w-xs mx-auto mt-2">Try adjusting your search or filters to find what you're looking for.</p>
          </div>
        )}
      </div>
    </div>
  )
}
