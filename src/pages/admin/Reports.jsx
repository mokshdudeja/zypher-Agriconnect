import { useState, useEffect } from 'react'
import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Card } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, getDocs } from 'firebase/firestore'
import { Loader2 } from 'lucide-react'

const COLORS = ['#2d8f2d', '#f97316', '#0ea5e9', '#f43f5e', '#8b5cf6']

export default function Reports() {
  const [loading, setLoading] = useState(true)
  const [revenueData, setRevenueData] = useState([])
  const [categoryData, setCategoryData] = useState([])
  const [metrics, setMetrics] = useState([])

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const [ordersSnap, cropsSnap, profilesSnap] = await Promise.all([
          getDocs(collection(db, 'orders')),
          getDocs(collection(db, 'crops')),
          getDocs(collection(db, 'profiles')),
        ])

        const orders = ordersSnap.docs.map(d => d.data())
        const crops = cropsSnap.docs.map(d => d.data())
        const profiles = profilesSnap.docs.map(d => d.data())

        // Revenue by month
        const monthly = {}
        orders.forEach(o => {
          const date = o.created_at?.toDate?.() || (o.created_at ? new Date(o.created_at) : null)
          if (date) {
            const month = date.toLocaleString('en-IN', { month: 'short' })
            if (!monthly[month]) monthly[month] = { month, revenue: 0, orders: 0 }
            monthly[month].revenue += o.total_price || 0
            monthly[month].orders += 1
          }
        })
        const revenueDataArr = Object.values(monthly).length > 0
          ? Object.values(monthly)
          : [{ month: 'No data', revenue: 0, orders: 0 }]

        // Category distribution
        const catCounts = {}
        crops.forEach(c => {
          const cat = c.category || 'Other'
          catCounts[cat] = (catCounts[cat] || 0) + 1
        })
        const pieData = Object.entries(catCounts).map(([name, value]) => ({ name, value }))

        // Metrics
        const totalRevenue = orders.reduce((s, o) => s + (o.total_price || 0), 0)
        const avgOrder = orders.length > 0 ? Math.round(totalRevenue / orders.length) : 0

        setRevenueData(revenueDataArr)
        setCategoryData(pieData.length > 0 ? pieData : [{ name: 'No data', value: 1 }])
        setMetrics([
          { label: 'Avg Order Value', value: `₹${avgOrder.toLocaleString('en-IN')}`, change: '', positive: true },
          { label: 'Total Orders', value: orders.length.toLocaleString(), change: '', positive: true },
          { label: 'Active Crops', value: crops.length.toLocaleString(), change: '', positive: true },
          { label: 'Total Users', value: profiles.length.toLocaleString(), change: '', positive: true },
        ])
      } catch (err) {
        console.error('Reports fetch error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchReports()
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
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl font-bold text-slate-800">Reports & Analytics</h1>
        <p className="text-slate-500 mt-1">Platform performance metrics from real data</p>
      </div>

      {/* Revenue Over Time */}
      <Card className="p-5 animate-fade-in-up delay-1">
        <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Revenue Over Time</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={revenueData}>
              <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
              <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
              <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }} />
              <Line type="monotone" dataKey="revenue" stroke="#2d8f2d" strokeWidth={3} dot={{ fill: '#2d8f2d', r: 5 }} />
              <Line type="monotone" dataKey="orders" stroke="#0ea5e9" strokeWidth={2} strokeDasharray="5 5" dot={false} />
            </LineChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        {/* Orders by Month */}
        <Card className="p-5 animate-fade-in-up delay-2">
          <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Monthly Orders</h3>
          <div className="h-64">
            <ResponsiveContainer width="100%" height="100%">
              <BarChart data={revenueData}>
                <XAxis dataKey="month" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: '#94a3b8' }} />
                <Tooltip contentStyle={{ borderRadius: 12, border: 'none', boxShadow: '0 4px 15px rgba(0,0,0,0.1)' }} />
                <Bar dataKey="orders" fill="#f97316" radius={[6, 6, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </div>
        </Card>

        {/* Category Distribution */}
        <Card className="p-5 animate-fade-in-up delay-3">
          <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Category Distribution</h3>
          <div className="h-48 flex items-center justify-center">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={categoryData} cx="50%" cy="50%" outerRadius={80} paddingAngle={3} dataKey="value" label={({ name, percent }) => `${name} ${(percent * 100).toFixed(0)}%`}>
                  {categoryData.map((_, index) => (
                    <Cell key={index} fill={COLORS[index % COLORS.length]} />
                  ))}
                </Pie>
                <Tooltip />
              </PieChart>
            </ResponsiveContainer>
          </div>
          <div className="flex flex-wrap justify-center gap-3 mt-4">
            {categoryData.map((cat, i) => (
              <div key={cat.name} className="flex items-center gap-1.5 text-xs text-slate-600">
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i % COLORS.length] }} />
                {cat.name}: {cat.value}
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Key Metrics Summary */}
      <Card className="p-5 animate-fade-in-up delay-4">
        <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Performance Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {metrics.map(m => (
            <div key={m.label} className="text-center">
              <p className="text-2xl font-display font-bold text-slate-800">{m.value}</p>
              <p className="text-xs text-slate-500 mt-1">{m.label}</p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
