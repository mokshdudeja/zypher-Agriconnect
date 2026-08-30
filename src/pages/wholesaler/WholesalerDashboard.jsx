import { useState, useEffect } from 'react'
import { TrendingUp, Package, ShoppingCart, Clock, ArrowUpRight, QrCode, Loader2 } from 'lucide-react'
import { Link } from 'react-router-dom'
import { StatCard, Badge, Card } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, where, orderBy, getDocs, limit, getDoc, doc } from 'firebase/firestore'
import { useAuth } from '../../context/AuthContext'
import { toast } from 'react-hot-toast'

export default function WholesalerDashboard() {
  const { user } = useAuth()
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({ activeDeals: 0, totalPurchased: '₹0', pendingBids: 0, inventoryItems: 0 })
  const [recentDeals, setRecentDeals] = useState([])

  useEffect(() => {
    if (!user) return

    const fetchDashboard = async () => {
      try {
        setLoading(true)

        // Fetch orders where this wholesaler is the buyer
        let ordersSnap
        try {
          ordersSnap = await getDocs(query(collection(db, 'orders'), where('wholesaler_id', '==', user.id), orderBy('created_at', 'desc')))
        } catch (e) {
          ordersSnap = await getDocs(query(collection(db, 'orders'), where('wholesaler_id', '==', user.id)))
        }
        const orders = ordersSnap.docs.map(d => ({ id: d.id, ...d.data() }))

        const activeDeals = orders.filter(o => o.status === 'Pending' || o.status === 'Processing').length
        const totalPurchased = orders
          .filter(o => o.status === 'Delivered')
          .reduce((sum, o) => sum + (o.total_price || 0), 0)

        // Fetch bids
        const bidsQuery = query(
          collection(db, 'bids'),
          where('wholesaler_id', '==', user.id),
          where('status', '==', 'pending')
        )
        const bidsSnap = await getDocs(bidsQuery)

        // Fetch crops to get inventory count for this wholesaler's purchases
        const inventoryQuery = query(
          collection(db, 'orders'),
          where('wholesaler_id', '==', user.id),
          where('status', '==', 'Delivered')
        )
        const inventorySnap = await getDocs(inventoryQuery)

        setStats({
          activeDeals,
          totalPurchased: `₹${totalPurchased.toLocaleString()}`,
          pendingBids: bidsSnap.size,
          inventoryItems: inventorySnap.size,
        })

        // Map recent orders to deals format
        const deals = orders.slice(0, 5).map(order => {
          const date = order.created_at?.toDate ? order.created_at.toDate() : new Date(order.created_at)
          return {
            id: order.id,
            farmer: order.farmer_name || 'Farmer',
            crop: order.crop_name || 'Unknown',
            qty: `${order.quantity} ${order.unit}`,
            total: `₹${(order.total_price || 0).toLocaleString()}`,
            status: order.status,
            date: date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short' }),
          }
        })
        setRecentDeals(deals)

      } catch (err) {
        console.error('Dashboard fetch error:', err)
        toast.error('Failed to load dashboard')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboard()
  }, [user])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-10 h-10 text-harvest-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl sm:text-3xl font-bold text-slate-800">
          Wholesaler Dashboard
        </h1>
        <p className="text-slate-500 mt-1">Manage your deals and inventory</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<ShoppingCart className="w-5 h-5" />} label="Active Deals" value={stats.activeDeals} delay={1} />
        <StatCard icon={<TrendingUp className="w-5 h-5" />} label="Total Purchased" value={stats.totalPurchased} delay={2} />
        <StatCard icon={<Clock className="w-5 h-5" />} label="Pending Bids" value={stats.pendingBids} delay={3} />
        <StatCard icon={<Package className="w-5 h-5" />} label="Inventory Items" value={stats.inventoryItems} delay={4} />
      </div>

      {/* Recent Deals Table */}
      <Card className="animate-fade-in-up delay-5">
        <div className="p-5 border-b border-slate-100">
          <h2 className="font-display text-lg font-bold text-slate-800">Recent Deals</h2>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Farmer</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Crop</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden sm:table-cell">Quantity</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Total</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {recentDeals.length > 0 ? (
                recentDeals.map((deal) => (
                  <tr key={deal.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-4">
                      <p className="font-medium text-slate-800">{deal.farmer}</p>
                      <p className="text-xs text-slate-400">{deal.date}</p>
                    </td>
                    <td className="px-5 py-4 text-slate-600">{deal.crop}</td>
                    <td className="px-5 py-4 text-slate-600 hidden sm:table-cell">{deal.qty}</td>
                    <td className="px-5 py-4 font-semibold text-slate-800">{deal.total}</td>
                    <td className="px-5 py-4">
                      <Badge variant={
                        deal.status === 'Delivered' ? 'success' :
                        deal.status === 'Processing' ? 'info' : 'warning'
                      }>
                        {deal.status}
                      </Badge>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-5 py-8 text-center text-slate-400">
                    No deals yet. Start by browsing farmer listings!
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Quick Actions */}
      <div className="grid grid-cols-1 sm:grid-cols-2 gap-4 animate-fade-in-up delay-6">
        <Link 
          to="/wholesaler/browse"
          className="flex items-center gap-3 p-4 bg-harvest-50 border border-harvest-200 rounded-xl hover:bg-harvest-100 transition-colors text-left group"
        >
          <ArrowUpRight className="w-5 h-5 text-harvest-600" />
          <div>
            <p className="font-semibold text-slate-800">Browse Farmer Listings</p>
            <p className="text-xs text-slate-500">Find fresh produce</p>
          </div>
        </Link>
        <Link 
          to="/scan"
          className="flex items-center gap-3 p-4 bg-leaf-50 border border-leaf-200 rounded-xl hover:bg-leaf-100 transition-colors text-left group"
        >
          <QrCode className="w-5 h-5 text-leaf-600" />
          <div>
            <p className="font-semibold text-slate-800">Scan Crop Token</p>
            <p className="text-xs text-slate-500">Trace origin via QR</p>
          </div>
        </Link>
        <Link 
          to="/wholesaler/inventory"
          className="flex items-center gap-3 p-4 bg-sky-50 border border-sky-200 rounded-xl hover:bg-sky-100 transition-colors text-left group"
        >
          <Package className="w-5 h-5 text-sky-600" />
          <div>
            <p className="font-semibold text-slate-800">View Inventory</p>
            <p className="text-xs text-slate-500">Manage stock levels</p>
          </div>
        </Link>
      </div>
    </div>
  )
}
