import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Mic, Sprout, Package, TrendingUp, Clock, Globe, Loader2 } from 'lucide-react'
import { StatCard } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, where, getDocs, orderBy, limit, getCountFromServer } from 'firebase/firestore'
import { useAuth } from '../../context/AuthContext'
import { useEffect } from 'react'
import { toast } from 'react-hot-toast'

const languages = ['English', 'हिन्दी', 'தமிழ்', 'తెలుగు', 'ಕನ್ನಡ', 'मराठी']

export default function FarmerDashboard() {
  const { user } = useAuth()
  const [lang, setLang] = useState('English')
  const [listening, setListening] = useState(false)
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalListings: 0,
    readyCrops: 0,
    totalRevenue: '₹0',
    pendingOrders: 0
  })
  const [recentCrops, setRecentCrops] = useState([])

  useEffect(() => {
    if (!user) return

    const fetchDashboardData = async () => {
      try {
        setLoading(true)
        
        // 1. Total Listings
        const cropsRef = collection(db, 'crops')
        const totalQuery = query(cropsRef, where('farmer_id', '==', user.id))
        const totalSnap = await getCountFromServer(totalQuery)

        // 2. Ready Crops
        const readyQuery = query(cropsRef, where('farmer_id', '==', user.id), where('status', '==', 'Ready'))
        const readySnap = await getCountFromServer(readyQuery)

        // 3. Recent Crops
        const recentQuery = query(cropsRef, where('farmer_id', '==', user.id), orderBy('created_at', 'desc'), limit(3))
        const recentSnap = await getDocs(recentQuery)
        const recentCropsList = recentSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))

        // 4. Pending Orders (Farmer side)
        // Since Firestore doesn't support easy many-to-many joins, we'll fetch all orders 
        // and filter. In a real app, this would be a cloud function or a more structured query.
        const ordersSnap = await getDocs(collection(db, 'orders'))
        const allOrders = ordersSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))
        
        // Filter orders where the crop belongs to this farmer
        // Note: For this to work efficiently, we'll need to fetch the crops first
        const myCropsSnap = await getDocs(query(cropsRef, where('farmer_id', '==', user.id)))
        const myCropIds = myCropsSnap.docs.map(d => d.id)
        
        const myOrders = allOrders.filter(o => myCropIds.includes(o.listing_id))

        const pendingCount = myOrders.filter(o => o.status === 'Pending').length
        const revenue = myOrders.filter(o => o.status === 'Delivered')
          .reduce((sum, o) => sum + (o.total_price || 0), 0)

        setStats({
          totalListings: totalSnap.data().count,
          readyCrops: readySnap.data().count,
          totalRevenue: `₹${revenue.toLocaleString()}`,
          pendingOrders: pendingCount
        })
        setRecentCrops(recentCropsList)

      } catch (err) {
        console.error('Dashboard fetch error:', err)
        toast.error('Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [user])

  return (
    <div className="space-y-6">
      {/* Header with language + voice */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="font-display text-2xl sm:text-3xl font-bold text-slate-800">
            🌱 Namaste, Farmer!
          </h1>
          <p className="text-slate-500 mt-1">Here's your farm at a glance</p>
        </div>
        <div className="flex items-center gap-3">
          {/* Language Selector */}
          <div className="relative">
            <Globe className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
            <select
              value={lang}
              onChange={(e) => setLang(e.target.value)}
              className="pl-9 pr-4 py-2.5 bg-white border border-slate-200 rounded-xl text-sm font-medium appearance-none cursor-pointer focus:outline-none focus:ring-2 focus:ring-leaf-500 focus:border-leaf-500"
            >
              {languages.map(l => (
                <option key={l} value={l}>{l}</option>
              ))}
            </select>
          </div>

          {/* Voice Button */}
          <button
            onClick={() => setListening(!listening)}
            className={`relative p-4 rounded-full transition-all duration-300 shadow-md ${
              listening
                ? 'bg-red-500 text-white scale-110 mic-pulse'
                : 'bg-leaf-600 text-white hover:bg-leaf-700 hover:scale-105'
            }`}
            aria-label="Voice command"
          >
            <Mic className="w-6 h-6" />
          </button>
        </div>
      </div>

      {/* Voice Listening UI */}
      {listening && (
        <div className="bg-white rounded-2xl p-6 shadow-card animate-scale-in text-center border-2 border-leaf-200">
          <div className="relative w-20 h-20 mx-auto mb-4">
            <div className="absolute inset-0 rounded-full bg-leaf-100 animate-ping opacity-30" />
            <div className="absolute inset-2 rounded-full bg-leaf-200 animate-ping opacity-40" style={{ animationDelay: '0.3s' }} />
            <div className="relative w-20 h-20 rounded-full bg-leaf-600 flex items-center justify-center">
              <Mic className="w-8 h-8 text-white" />
            </div>
          </div>
          <p className="font-display text-lg font-bold text-slate-800">Listening...</p>
          <p className="text-sm text-slate-500 mt-1">Say a command like "Add 100 kg of wheat"</p>
          <button
            onClick={() => setListening(false)}
            className="mt-4 px-6 py-2 bg-red-100 text-red-600 rounded-xl text-sm font-semibold hover:bg-red-200 transition-colors"
          >
            Stop Listening
          </button>
        </div>
      )}

      {/* Stats */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<Sprout className="w-5 h-5" />} label="Total Listings" value={loading ? '...' : stats.totalListings} delay={1} />
        <StatCard icon={<Package className="w-5 h-5" />} label="Ready to Sell" value={loading ? '...' : stats.readyCrops} delay={2} />
        <StatCard icon={<TrendingUp className="w-5 h-5" />} label="Total Revenue" value={loading ? '...' : stats.totalRevenue} delay={3} />
        <StatCard icon={<Clock className="w-5 h-5" />} label="Pending Orders" value={loading ? '...' : stats.pendingOrders} delay={4} />
      </div>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-fade-in-up delay-5">
        <Link
          to="/farmer/add-crop"
          className="flex items-center gap-4 p-5 bg-leaf-600 text-white rounded-2xl shadow-md hover:bg-leaf-700 hover:shadow-lg transition-all duration-300 group"
        >
          <div className="w-12 h-12 rounded-xl bg-white/20 flex items-center justify-center group-hover:scale-105 transition-transform">
            <Sprout className="w-6 h-6" />
          </div>
          <div>
            <p className="text-lg font-bold">Add New Crop</p>
            <p className="text-sm text-leaf-100">List your produce for sale</p>
          </div>
        </Link>
        <Link
          to="/farmer/listings"
          className="flex items-center gap-4 p-5 bg-white border-2 border-earth-200 text-slate-800 rounded-2xl shadow-card hover:shadow-card-hover transition-all duration-300 group"
        >
          <div className="w-12 h-12 rounded-xl bg-earth-100 flex items-center justify-center group-hover:scale-105 transition-transform">
            <Package className="w-6 h-6 text-earth-600" />
          </div>
          <div>
            <p className="text-lg font-bold">My Listings</p>
            <p className="text-sm text-slate-500">Manage your crop listings</p>
          </div>
        </Link>
      </div>

      {/* Recent Crops */}
      <div className="animate-fade-in-up delay-6">
        <h2 className="font-display text-xl font-bold text-slate-800 mb-4">Recent Crops</h2>
        <div className="space-y-3">
          {loading ? (
             <div className="flex justify-center py-10">
               <Loader2 className="w-8 h-8 text-leaf-600 animate-spin" />
             </div>
          ) : recentCrops.length > 0 ? (
            recentCrops.map((crop) => (
              <div key={crop.id} className="flex items-center gap-4 p-4 bg-white rounded-xl shadow-card hover:shadow-card-hover transition-all">
                <div className="w-12 h-12 rounded-xl bg-leaf-50 flex items-center justify-center text-2xl">
                  {crop.name.toLowerCase().includes('wheat') ? '🌾' : 
                   crop.name.toLowerCase().includes('rice') ? '🍚' : 
                   crop.name.toLowerCase().includes('corn') ? '🌽' : '🥦'}
                </div>
                <div className="flex-1 min-w-0">
                  <p className="font-semibold text-slate-800 truncate">{crop.name}</p>
                  <p className="text-sm text-slate-500">{crop.quantity} {crop.unit} · ₹{crop.price}/{crop.unit}</p>
                </div>
                <span className={`px-3 py-1 rounded-full text-xs font-semibold ${
                  crop.status === 'Ready' ? 'bg-leaf-100 text-leaf-700' : 'bg-harvest-100 text-harvest-700'
                }`}>
                  {crop.status}
                </span>
              </div>
            ))
          ) : (
            <div className="bg-white rounded-xl p-8 text-center border-2 border-dashed border-slate-200">
              <Sprout className="w-10 h-10 text-slate-300 mx-auto mb-2" />
              <p className="text-slate-500 text-sm">No crops listed yet. Start by adding your first crop!</p>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
