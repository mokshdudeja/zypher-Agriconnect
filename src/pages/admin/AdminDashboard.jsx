import { useState, useEffect } from 'react'
import { Users, TrendingUp, ShoppingCart, Sprout, ArrowUpRight, AlertCircle, Package, Loader2 } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { StatCard, Card, Badge } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, getDocs, orderBy, limit, where, getCountFromServer } from 'firebase/firestore'
import { toast } from 'react-hot-toast'

const COLORS = ['#2d8f2d', '#f97316', '#0ea5e9', '#f43f5e', '#8b5cf6']

export default function AdminDashboard() {
  const [loading, setLoading] = useState(true)
  const [stats, setStats] = useState({
    totalUsers: 0,
    totalFarmers: 0,
    totalWholesalers: 0,
    totalConsumers: 0,
    pendingVerifications: 0,
    totalRevenue: '₹0'
  })
  const [recentTransactions, setRecentTransactions] = useState([])
  const [categoryData, setCategoryData] = useState([])
  const [revenueChartData, setRevenueChartData] = useState([])

  useEffect(() => {
    const fetchDashboardData = async () => {
      try {
        setLoading(true)

        // 1. Fetch all profiles to get user counts
        const profilesSnap = await getDocs(collection(db, 'profiles'))
        const profiles = profilesSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))

        const farmers = profiles.filter(p => p.role === 'farmer').length
        const wholesalers = profiles.filter(p => p.role === 'wholesaler').length
        const consumers = profiles.filter(p => p.role === 'consumer').length
        const totalUsers = profiles.length

        // 2. Fetch pending verifications (users without verified emails)
        const pendingQuery = query(
          collection(db, 'profiles'),
          where('emailVerified', '==', false)
        )
        const pendingSnap = await getDocs(pendingQuery)
        const pendingVerifications = pendingSnap.size

        // 3. Fetch orders to calculate revenue and transactions
        const ordersSnap = await getDocs(collection(db, 'orders'))
        const orders = ordersSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))
        
        const completedOrders = orders.filter(o => o.status === 'Delivered')
        const totalRevenue = completedOrders.reduce((sum, o) => sum + (o.total_price || 0), 0)

        // 4. Group orders by month for revenue chart (last 6 months)
        const monthlyData = {}
        const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
        const currentDate = new Date()
        
        for (let i = 5; i >= 0; i--) {
          const date = new Date(currentDate.getFullYear(), currentDate.getMonth() - i, 1)
          const monthKey = months[date.getMonth()]
          monthlyData[monthKey] = { month: monthKey, revenue: 0, orders: 0 }
        }

        orders.forEach(order => {
          if (order.created_at) {
            const orderDate = order.created_at.toDate ? order.created_at.toDate() : new Date(order.created_at)
            const monthKey = months[orderDate.getMonth()]
            if (monthlyData[monthKey]) {
              monthlyData[monthKey].orders += 1
              if (order.status === 'Delivered') {
                monthlyData[monthKey].revenue += order.total_price || 0
              }
            }
          }
        })

        const revenueData = Object.values(monthlyData)

        // 5. Group crops by category for pie chart
        const cropsSnap = await getDocs(collection(db, 'crops'))
        const crops = cropsSnap.docs.map(doc => doc.data())
        
        const categoryCounts = {}
        crops.forEach(crop => {
          const category = crop.category || 'Other'
          categoryCounts[category] = (categoryCounts[category] || 0) + 1
        })

        const categoryData = Object.entries(categoryCounts).map(([name, value]) => ({ name, value }))

        // 6. Fetch recent transactions (last 5 orders)
        const recentOrdersQuery = query(
          collection(db, 'orders'),
          orderBy('created_at', 'desc'),
          limit(5)
        )
        const recentOrdersSnap = await getDocs(recentOrdersQuery)
        const recentOrders = recentOrdersSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))

        // Map orders to transaction format
        const recentTransactions = recentOrders.map(order => ({
          id: order.id.slice(0, 8) + '...',
          buyer: order.wholesaler_name || order.consumer_name || 'Unknown',
          seller: order.farmer_name || 'Farmer',
          amount: `₹${(order.total_price || 0).toLocaleString()}`,
          status: order.status
        }))

        setStats({
          totalUsers,
          totalFarmers: farmers,
          totalWholesalers: wholesalers,
          totalConsumers: consumers,
          pendingVerifications,
          totalRevenue: `₹${totalRevenue.toLocaleString()}`
        })

        setRecentTransactions(recentTransactions)
        setCategoryData(categoryData.length > 0 ? categoryData : [{ name: 'No Data', value: 1 }])
        setRevenueChartData(revenueData)

      } catch (err) {
        console.error('Dashboard fetch error:', err)
        toast.error('Failed to load dashboard data')
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [])

  if (loading) {
    return (
      <div className="flex justify-center items-center py-20">
        <Loader2 className="w-10 h-10 text-leaf-600 animate-spin" />
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
        <StatCard icon={<Users className="w-5 h-5" />} label="Total Users" value={stats.totalUsers.toLocaleString()} delay={1} />
        <StatCard icon={<TrendingUp className="w-5 h-5" />} label="Revenue" value={stats.totalRevenue} delay={2} />
        <StatCard icon={<ShoppingCart className="w-5 h-5" />} label="Transactions" value={recentTransactions.length.toLocaleString()} delay={3} />
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
        {/* Revenue Chart */}
        <Card className="lg:col-span-2 p-5 animate-fade-in-up delay-5">
          <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Revenue & Orders (Last 6 Months)</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenueChartData}>
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip
                  contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }}
                />
                <Bar dataKey="revenue" fill="#2d8f2d" radius={[6, 6, 0, 0]} />
                <Bar dataKey="orders" fill="#0ea5e9" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Category Pie */}
        <Card className="p-5 animate-fade-in-up delay-6">
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
          <a href="/admin/transactions" className="text-sm text-sky-600 font-semibold hover:text-sky-700 flex items-center gap-1">
            View All <ArrowUpRight className="w-4 h-4" />
          </a>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100">
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">ID</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Buyer</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase hidden md:table-cell">Seller</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Amount</th>
                <th className="text-left px-5 py-3 text-xs font-semibold text-slate-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {recentTransactions.length > 0 ? (
                recentTransactions.map((txn) => (
                  <tr key={txn.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                    <td className="px-5 py-3 font-mono text-xs text-slate-600">{txn.id}</td>
                    <td className="px-5 py-3 text-slate-800 font-medium">{txn.buyer}</td>
                    <td className="px-5 py-3 text-slate-600 hidden md:table-cell">{txn.seller}</td>
                    <td className="px-5 py-3 font-bold text-slate-800">{txn.amount}</td>
                    <td className="px-5 py-3">
                      <Badge variant={txn.status === 'Delivered' ? 'success' : txn.status === 'Processing' ? 'info' : 'warning'}>
                        {txn.status}
                      </Badge>
                    </td>
                  </tr>
                ))
              ) : (
                <tr>
                  <td colSpan="5" className="px-5 py-8 text-center text-slate-400">
                    No transactions yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
