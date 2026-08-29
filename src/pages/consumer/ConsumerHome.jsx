import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { ArrowRight, Leaf, Truck, Shield, Star, Camera, Cloud, Thermometer, Droplets, Wind, Sprout } from 'lucide-react'
import { db } from '../../lib/firebase'
import { collection, query, getDocs, orderBy, limit } from 'firebase/firestore'
import { getCropImageUrl, getCropEmoji } from '../../data/cropImages'

const categories = [
  { name: 'Grains', emoji: '🌾', color: 'bg-harvest-50 border-harvest-200' },
  { name: 'Vegetables', emoji: '🥬', color: 'bg-leaf-50 border-leaf-200' },
  { name: 'Fruits', emoji: '🍎', color: 'bg-red-50 border-red-200' },
  { name: 'Spices', emoji: '🌶️', color: 'bg-earth-50 border-earth-200' },
  { name: 'Other', emoji: '📦', color: 'bg-slate-50 border-slate-200' },
]

const features = [
  { icon: Leaf, title: 'Farm Fresh', desc: 'Direct from verified farmers', color: 'text-leaf-600 bg-leaf-50' },
  { icon: Truck, title: 'Fast Delivery', desc: 'Delivered within 24 hours', color: 'text-sky-600 bg-sky-50' },
  { icon: Shield, title: 'Quality Assured', desc: '100% certified organic options', color: 'text-harvest-600 bg-harvest-50' },
]



export default function ConsumerHome() {
  const [featured, setFeatured] = useState([])
  const [loading, setLoading] = useState(true)
  const [weather, setWeather] = useState(null)
  const [weatherLoading, setWeatherLoading] = useState(true)

  useEffect(() => {
    const fetchFeatured = async () => {
      try {
        const cropsSnap = await getDocs(query(collection(db, 'crops'), orderBy('created_at', 'desc'), limit(4)))
        const cropsData = cropsSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))

        const profilesSnap = await getDocs(collection(db, 'profiles'))
        const profilesMap = {}
        profilesSnap.docs.forEach(doc => { profilesMap[doc.id] = doc.data() })

        const mapped = cropsData.map(item => ({
          ...item,
          farmer: profilesMap[item.farmer_id]?.name || 'Local Farmer',
          image: getCropImageUrl(item.name),
          emoji: getCropEmoji(item.name),
          rating: (4.0 + Math.random() * 0.9).toFixed(1),
          reviews: Math.floor(Math.random() * 100) + 10,
          originalPrice: Math.round((item.price || 0) * 1.2),
          organic: true,
        }))
        setFeatured(mapped)
      } catch (err) {
        console.error('Fetch error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchFeatured()
  }, [])

  // Live weather from OpenMeteo (Mumbai default)
  useEffect(() => {
    const fetchWeather = async () => {
      try {
        const res = await fetch(
          'https://api.open-meteo.com/v1/forecast?latitude=19.0760&longitude=72.8777&current=temperature_2m,relative_humidity_2m,wind_speed_10m,weather_code&daily=temperature_2m_max,temperature_2m_min,precipitation_sum&timezone=Asia%2FKolkata&forecast_days=3'
        )
        const data = await res.json()
        setWeather(data)
      } catch (err) {
        console.error('Weather fetch error:', err)
      } finally {
        setWeatherLoading(false)
      }
    }
    fetchWeather()
  }, [])

  const getWeatherIcon = (code) => {
    if (code <= 1) return '☀️'
    if (code <= 3) return '⛅'
    if (code <= 49) return '🌫️'
    if (code <= 69) return '🌧️'
    if (code <= 79) return '❄️'
    if (code <= 99) return '⛈️'
    return '🌤️'
  }

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
            <div className="flex items-center gap-2 mb-6">
              <div className="w-10 h-10 bg-white/15 rounded-xl flex items-center justify-center backdrop-blur-sm">
                <Sprout className="w-6 h-6" />
              </div>
              <span className="font-display text-lg font-bold">AgriConnect</span>
            </div>
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
              <Link
                to="/predictions"
                className="px-6 py-3.5 border-2 border-white/30 text-white rounded-xl font-bold hover:bg-white/10 transition-all"
              >
                Check Crop Prices
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* Live Weather Widget */}
      {!weatherLoading && weather && (
        <section className="max-w-7xl mx-auto px-4 sm:px-6 -mt-6 relative z-10">
          <div className="bg-white rounded-2xl shadow-lg border border-slate-100 p-5 animate-fade-in-up">
            <div className="flex items-center gap-2 mb-3">
              <Cloud className="w-5 h-5 text-sky-500" />
              <h3 className="font-display text-sm font-bold text-slate-800">Live Weather — Mumbai</h3>
              <span className="text-xs text-slate-400 ml-auto">via OpenMeteo API</span>
            </div>
            <div className="flex items-center gap-6 flex-wrap">
              <div className="flex items-center gap-3">
                <span className="text-4xl">{getWeatherIcon(weather.current?.weather_code || 0)}</span>
                <div>
                  <p className="text-2xl font-bold text-slate-800">{weather.current?.temperature_2m}°C</p>
                  <p className="text-xs text-slate-500">Current</p>
                </div>
              </div>
              <div className="flex gap-4 text-sm">
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Droplets className="w-4 h-4 text-sky-400" />
                  {weather.current?.relative_humidity_2m}% humidity
                </div>
                <div className="flex items-center gap-1.5 text-slate-600">
                  <Wind className="w-4 h-4 text-slate-400" />
                  {weather.current?.wind_speed_10m} km/h
                </div>
              </div>
              {weather.daily && (
                <div className="flex gap-3 ml-auto">
                  {weather.daily.time.slice(0, 3).map((date, i) => (
                    <div key={date} className="text-center px-3 py-1 bg-slate-50 rounded-lg">
                      <p className="text-xs text-slate-500">
                        {i === 0 ? 'Today' : i === 1 ? 'Tomorrow' : new Date(date).toLocaleDateString('en-IN', { weekday: 'short' })}
                      </p>
                      <p className="text-xs font-bold text-slate-700">
                        {weather.daily.temperature_2m_min[i]}° – {weather.daily.temperature_2m_max[i]}°
                      </p>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>
        </section>
      )}

      {/* Features */}
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-12">
        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {features.map((f, i) => (
            <div key={f.title} className={`flex items-center gap-4 p-5 rounded-2xl bg-white shadow-card hover:shadow-card-hover transition-all duration-300 animate-fade-in-up`}>
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
      <section className="max-w-7xl mx-auto px-4 sm:px-6 py-8">            <h2 className="font-display text-2xl font-bold text-slate-800 mb-5 animate-fade-in-up">Shop by Category</h2>
        <div className="flex gap-3 overflow-x-auto pb-2 scrollbar-none animate-fade-in-up">
          {categories.map((cat) => (
            <Link
              key={cat.name}
              to={`/consumer/products?category=${cat.name}`}
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
          {loading ? (
            Array.from({ length: 4 }).map((_, i) => (
              <div key={i} className="bg-white rounded-2xl shadow-card p-4 animate-pulse">
                <div className="h-40 bg-slate-100 rounded-xl mb-3" />
                <div className="h-4 bg-slate-100 rounded w-3/4 mb-2" />
                <div className="h-3 bg-slate-100 rounded w-1/2" />
              </div>
            ))
          ) : featured.length > 0 ? (
            featured.map((product, i) => (
              <Link
                key={product.id}
                to={`/consumer/products/${product.id}`}
                className="bg-white rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 overflow-hidden group animate-fade-in-up"
              >
                <div className="h-40 bg-gradient-to-br from-leaf-50 to-earth-50 overflow-hidden group-hover:scale-105 transition-transform duration-500">
                  <img src={product.image} alt={product.name} className="w-full h-full object-cover" loading="lazy" onError={(e) => { e.target.style.display = 'none'; e.target.nextSibling.style.display = 'flex'; }} />
                  <div className="w-full h-full items-center justify-center text-5xl hidden">
                    {product.emoji}
                  </div>
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
                    {product.originalPrice > product.price && (
                      <span className="text-sm text-slate-400 line-through">₹{product.originalPrice}</span>
                    )}
                  </div>
                </div>
              </Link>
            ))
          ) : (
            <div className="col-span-full text-center py-12 text-slate-400">
              <p>No products listed yet. Be the first farmer to list!</p>
              <Link to="/farmer/add" className="mt-3 inline-block text-leaf-600 font-semibold hover:underline">
                List Your Crop →
              </Link>
            </div>
          )}
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
