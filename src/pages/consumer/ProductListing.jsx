import { useState } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Search, Star, Leaf, ShoppingCart, Loader2, Check } from 'lucide-react'
import { db } from '../../lib/firebase'
import { collection, query, getDocs, orderBy, limit, startAfter } from 'firebase/firestore'
import { useEffect } from 'react'
import { useCart } from '../../context/CartContext'
import { toast } from 'react-hot-toast'

export default function ProductListing() {
  const [search, setSearch] = useState('')
  const [category, setCategory] = useState('All')
  const [products, setProducts] = useState([])
  const [loading, setLoading] = useState(true)
  const [loadingMore, setLoadingMore] = useState(false)
  const [lastDoc, setLastDoc] = useState(null)
  const [hasMore, setHasMore] = useState(true)
  const [addedId, setAddedId] = useState(null)
  const PAGE_SIZE = 20
  const { addItem, itemCount } = useCart()
  const navigate = useNavigate()

  useEffect(() => {
    const fetchProducts = async (isLoadMore = false) => {
      try {
        if (isLoadMore) setLoadingMore(true)
        else setLoading(true)

        // Fetch profiles once
        let profilesMap = {}
        if (!isLoadMore) {
          const profilesSnap = await getDocs(collection(db, 'profiles'))
          profilesSnap.docs.forEach(doc => { profilesMap[doc.id] = doc.data() })
        }

        // Paginated crops query
        const constraints = [orderBy('created_at', 'desc'), limit(PAGE_SIZE)]
        if (isLoadMore && lastDoc) constraints.splice(1, 0, startAfter(lastDoc))
        const cropsSnap = await getDocs(query(collection(db, 'crops'), ...constraints))
        
        if (cropsSnap.docs.length < PAGE_SIZE) setHasMore(false)
        if (cropsSnap.docs.length > 0) setLastDoc(cropsSnap.docs[cropsSnap.docs.length - 1])

        const cropsData = cropsSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))

        const mappedData = cropsData.map(item => ({
          ...item,
          farmer: profilesMap[item.farmer_id]?.name || 'Local Farmer',
          image: item.name?.toLowerCase().includes('wheat') ? '🌾' : 
                 item.name?.toLowerCase().includes('rice') ? '🍚' : 
                 item.name?.toLowerCase().includes('corn') ? '🌽' : '🥦',
          rating: (4.5 + Math.random() * 0.5).toFixed(1),
          reviews: Math.floor(Math.random() * 100) + 10,
          originalPrice: (item.price * 1.2).toFixed(0),
          organic: true
        }))

        setProducts(prev => isLoadMore ? [...prev, ...mappedData] : mappedData)
      } catch (err) {
        console.error('Fetch error:', err)
      } finally {
        setLoading(false)
        setLoadingMore(false)
      }
    }

    fetchProducts()
  }, [])

  const categories = ['All', 'Grains', 'Vegetables', 'Fruits', 'Spices', 'Other']
  const filtered = products.filter(p => {
    const matchSearch = p.name.toLowerCase().includes(search.toLowerCase())
    const matchCat = category === 'All' || 
      p.category?.toLowerCase() === category.toLowerCase() ||
      (category === 'Grains' && ['wheat', 'rice', 'corn', 'millet'].some(g => p.name.toLowerCase().includes(g))) ||
      (category === 'Vegetables' && ['tomato', 'potato', 'onion', 'carrot', 'spinach'].some(v => p.name.toLowerCase().includes(v))) ||
      (category === 'Fruits' && ['mango', 'apple', 'banana', 'orange'].some(f => p.name.toLowerCase().includes(f))) ||
      (category === 'Spices' && ['turmeric', 'chilli', 'cumin', 'coriander'].some(s => p.name.toLowerCase().includes(s)))
    return matchSearch && matchCat
  })

  const handleAddToCart = (e, product) => {
    e.preventDefault()
    e.stopPropagation()
    addItem(product)
    setAddedId(product.id)
    toast.success(`${product.name} added to cart!`)
    setTimeout(() => setAddedId(null), 1500)
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="space-y-6">
        {/* Header */}
        <div className="animate-fade-in-up">
          <div className="flex items-center justify-between">
            <div>
              <h1 className="font-display text-3xl font-bold text-slate-800">Fresh Produce</h1>
              <p className="text-slate-500 mt-1">{filtered.length} products available</p>
            </div>
            <button
              onClick={() => navigate('/consumer/cart')}
              className="relative p-3 bg-white border border-slate-200 rounded-xl hover:bg-slate-50 transition-colors"
            >
              <ShoppingCart className="w-5 h-5 text-slate-600" />
              {itemCount > 0 && (
                <span className="absolute -top-1.5 -right-1.5 w-5 h-5 bg-sky-600 text-white text-xs font-bold rounded-full flex items-center justify-center">
                  {itemCount}
                </span>
              )}
            </button>
          </div>
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
            {filtered.map((product) => (
              <div
                key={product.id}
                className="bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 overflow-hidden group animate-fade-in-up cursor-pointer"
                onClick={() => navigate(`/consumer/products/${product.id}`)}
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
                    <button
                      onClick={(e) => handleAddToCart(e, product)}
                      className={`w-9 h-9 rounded-xl flex items-center justify-center transition-all duration-300 ${
                        addedId === product.id
                          ? 'bg-leaf-600 text-white scale-110'
                          : 'bg-sky-50 text-sky-600 group-hover:bg-sky-600 group-hover:text-white'
                      }`}
                      aria-label={`Add ${product.name} to cart`}
                    >
                      {addedId === product.id ? (
                        <Check className="w-4 h-4" />
                      ) : (
                        <ShoppingCart className="w-4 h-4" />
                      )}
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        ) : (
        hasMore && !loading && (
          <div className="flex justify-center py-6">
            <button
              onClick={() => fetchProducts(true)}
              disabled={loadingMore}
              className="px-6 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-semibold text-slate-600 hover:bg-slate-50 transition-colors disabled:opacity-50"
            >
              {loadingMore ? <Loader2 className="w-4 h-4 animate-spin inline mr-2" /> : null}
              Load More
            </button>
          </div>
        )) : (
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
