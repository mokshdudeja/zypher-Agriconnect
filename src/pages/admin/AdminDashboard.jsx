import { useState, useEffect } from 'react'
import { Link } from 'react-router-dom'
import { Users, TrendingUp, ShoppingCart, Sprout, ArrowUpRight, AlertCircle, Package, Loader2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { StatCard, Card, Badge } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, getDocs, query, orderBy, limit } from 'firebase/firestore'

const COLORS = ['#2d8f2d', '#f97316', '#0ea5e9', '#f43f5e', '#8b5cf6']

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalFarmers: 0,
    totalWholesalers: 0,
    totalConsumers: 0,
    totalTransactions: 0,
    totalRevenue: '₹0',
    pendingVerifications: 0,
    monthlyGrowth: 0,
  })
  const [categoryData, setCategoryData] = useState([])
  const [recentTransactions, setRecentTransactions] = useState([])

  useEffect(() => {
    const fetchAdminData = async () => {
      try {
        setLoading(true)

        const [profilesSnap, ordersSnap, cropsSnap] = await Promise.all([
          getDocs(collection(db, 'profiles')),
          getDocs(collection(db, 'orders')),
          getDocs(collection(db, 'crops')),
        ])

        // --- Profile stats ---
        const profiles = profilesSnap.docs.map(d => d.data())
        const farmers = profiles.filter(p => p.role === 'farmer').length
        const wholesalers = profiles.filter(p => p.role === 'wholesaler').length
        const consumers = profiles.filter(p => p.role === 'consumer').length
        const pendingVerifications = profiles.filter(p => p.status === 'Pending' || p.verified === false).length

        // --- Order stats ---
        const orders = ordersSnap.docs.map(d => ({ id: d.id, ...d.data() }))
        const totalRevenue = orders.reduce((sum, o) => sum + (o.total_price || 0), 0)

        // --- Category breakdown from crops ---
        const crops = cropsSnap.docs.map(d => d.data())
        const catCounts = {}
        crops.forEach(c => {
          const cat = c.category || 'Other'
          catCounts[cat] = (catCounts[cat] || 0) + 1
        })
        const pieData = Object.entries(catCounts).map(([name, value]) => ({ name, value }))

        // --- Recent transactions (most recent 5 orders) ---
        const recentOrders = orders
          .sort((a, b) => {
            const ta = a.created_at?.seconds || 0
            const tb = b.created_at?.seconds || 0
            return tb - ta
          })
          .slice(0, 5)

        // --- Build a simple monthly revenue bar chart from orders ---
        const monthlyRevenue = {}
        orders.forEach(o => {
          const date = o.created_at?.toDate?.() || (o.created_at ? new Date(o.created_at) : null)
          if (date) {
            const month = date.toLocaleString('en-IN', { month: 'short' })
            if (!monthlyRevenue[month]) monthlyRevenue[month] = { month, revenue: 0, orders: 0 }
            monthlyRevenue[month].revenue += o.total_price || 0
            monthlyRevenue[month].orders += 1
          }
        })
        // If no orders have dates, provide a placeholder
        const revenueData = Object.values(monthlyRevenue).length > 0
          ? Object.values(monthlyRevenue)
          : [{ month: 'No data', revenue: 0, orders: 0 }]

        setStats({
          totalUsers: profiles.length,
          totalFarmers: farmers,
          totalWholesalers: wholesalers,
          totalConsumers: consumers,
          totalTransactions: orders.length,
          totalRevenue: `₹${totalRevenue.toLocaleString('en-IN')}`,
          pendingVerifications,
          monthlyGrowth: 0,
        })
        setCategoryData(pieData.length > 0 ? pieData : [
          { name: 'Grains', value: 35 },
          { name: 'Vegetables', value: 30 },
          { name: 'Fruits', value: 25 },
          { name: 'Spices', value: 10 },
        ])
        setRecentTransactions(recentOrders)
      } catch (err) {
        console.error('Admin dashboard fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchAdminData()
  }, [])

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-sky-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl sm:text-3xl font-bold text-slate-800">Dashboard Overview</h1>
        <p className="text-slate-500 mt-1">Welcome back, Admin. Here's your platform summary.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<Users className="w-5 h-5" />} label="Total Users" value={stats.totalUsers.toLocaleString()} trend={stats.monthlyGrowth || undefined} delay={1} />
        <StatCard icon={<TrendingUp className="w-5 h-5" />} label="Revenue" value={stats.totalRevenue} delay={2} />
        <StatCard icon={<ShoppingCart className="w-5 h-5" />} label="Transactions" value={stats.totalTransactions.toLocaleString()} delay={3} />
        <StatCard
          icon={<AlertCircle className="w-5 h-5" />}
          label="Pending Verify"
          value={stats.pendingVerifications}
          delay={4}
          color="bg-amber-50"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Category Pie */}
        <Card className="p-5 animate-fade-in-up delay-5">
          <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Crop Categories</h3>
          <div className="h-48">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie
                  data={categoryData}
                  cx="50%"
                  cy="50%"
                  innerRadius={50}
                  outerRadius={80}
                  paddingAngle={3}
                  dataKey="value"
                >
                  {categoryData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap gap-2 mt-2">
            {categoryData.map((cat, i) => (
              <div key={cat.name} className="flex items-center gap-1.5 text-xs text-slate-600">
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                {cat.name} ({cat.value})
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* User Breakdown */}
      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 animate-fade-in-up delay-5">
        <div className="bg-leaf-50 border border-leaf-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 text-leaf-700">
            <Sprout className="w-5 h-5" />
            <span className="text-sm font-semibold">Farmers</span>
          </div>
          <p className="text-3xl font-display font-bold text-slate-800 mt-2">{stats.totalFarmers.toLocaleString()}</p>
        </div>
        <div className="bg-harvest-50 border border-harvest-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 text-harvest-700">
            <Package className="w-5 h-5" />
            <span className="text-sm font-semibold">Wholesalers</span>
          </div>
          <p className="text-3xl font-display font-bold text-slate-800 mt-2">{stats.totalWholesalers.toLocaleString()}</p>
        </div>
        <div className="bg-sky-50 border border-sky-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 text-sky-700">
            <Users className="w-5 h-5" />
            <span className="text-sm font-semibold">Consumers</span>
          </div>
          <p className="text-3xl font-display font-bold text-slate-800 mt-2">{stats.totalConsumers.toLocaleString()}</p>
        </div>
      </div>

      {/* Recent Transactions */}
      <Card className="animate-fade-in-up delay-6">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <h3 className="font-display text-lg font-bold text-slate-800">Recent Transactions</h3>
          <Link to="/admin/transactions" className="text-sm text-sky-600 font-semibold hover:text-sky-700 flex items-center gap-1">
            View All <ArrowUpRight className="w-4 h-4" />
          </Link>
        </div>
        <div className="overflow-x-auto">
          {recentTransactions.length > 0 ? (
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b border-slate-100">
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Crop</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Buyer</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase hidden md:table-cell">Seller</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Amount</th>
                  <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Status</th>
                </tr>
              </thead>
              <tbody>
                {recentTransactions.map((txn) => (
                  <tr key={txn.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 text-slate-800 font-medium">{txn.crop_name || '—'}</td>
                    <td className="px-5 py-3 text-slate-600">{txn.wholesaler_name || txn.consumer_name || '—'}</td>
                    <td className="px-5 py-3 text-slate-600 hidden md:table-cell">{txn.farmer_name || '—'}</td>
                    <td className="px-5 py-3 font-bold text-slate-800">₹{(txn.total_price || 0).toLocaleString('en-IN')}</td>
                    <td className="px-5 py-3">
                      <Badge variant={txn.status === 'Completed' || txn.status === 'Delivered' ? 'success' : txn.status === 'Processing' ? 'info' : 'warning'}>
                        {txn.status || 'Pending'}
                      </Badge>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : (
            <div className="p-8 text-center text-sm text-slate-400">No transactions yet</div>
          )}
        </div>
      </Card>
    </div>
  )
}
