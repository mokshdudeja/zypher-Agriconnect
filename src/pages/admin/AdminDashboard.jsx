import { Users, TrendingUp, ShoppingCart, Sprout, ArrowUpRight, AlertCircle, Package } from 'lucide-react'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, LineChart, Line, PieChart, Pie, Cell } from 'recharts'
import { StatCard, Card, Badge } from '../../components/ui'
import { adminStats, revenueChartData, categoryData, adminTransactions } from '../../data/mockData'

const COLORS = ['#2d8f2d', '#f97316', '#0ea5e9', '#f43f5e', '#8b5cf6']

export default function AdminDashboard() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl sm:text-3xl font-bold text-slate-800">Dashboard Overview</h1>
        <p className="text-slate-500 mt-1">Welcome back, Admin. Here's your platform summary.</p>
      </div>

      {/* Stats Grid */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <StatCard icon={<Users className="w-5 h-5" />} label="Total Users" value={adminStats.totalUsers.toLocaleString()} trend={adminStats.monthlyGrowth} delay={1} />
        <StatCard icon={<TrendingUp className="w-5 h-5" />} label="Revenue" value={adminStats.totalRevenue} trend={18} delay={2} />
        <StatCard icon={<ShoppingCart className="w-5 h-5" />} label="Transactions" value={adminStats.totalTransactions.toLocaleString()} trend={12} delay={3} />
        <StatCard
          icon={<AlertCircle className="w-5 h-5" />}
          label="Pending Verify"
          value={adminStats.pendingVerifications}
          delay={4}
          color="bg-amber-50"
        />
      </div>

      {/* Charts Row */}
      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        {/* Revenue Chart */}
        <Card className="lg:col-span-2 p-5 animate-fade-in-up delay-5">
          <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Revenue & Orders</h3>
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
          <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Categories</h3>
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
                <div className="w-2.5 h-2.5 rounded-full" style={{ backgroundColor: COLORS[i] }} />
                {cat.name}
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
          <p className="text-3xl font-display font-bold text-slate-800 mt-2">{adminStats.totalFarmers.toLocaleString()}</p>
        </div>
        <div className="bg-harvest-50 border border-harvest-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 text-harvest-700">
            <Package className="w-5 h-5" />
            <span className="text-sm font-semibold">Wholesalers</span>
          </div>
          <p className="text-3xl font-display font-bold text-slate-800 mt-2">{adminStats.totalWholesalers.toLocaleString()}</p>
        </div>
        <div className="bg-sky-50 border border-sky-200 rounded-2xl p-5">
          <div className="flex items-center gap-2 text-sky-700">
            <Users className="w-5 h-5" />
            <span className="text-sm font-semibold">Consumers</span>
          </div>
          <p className="text-3xl font-display font-bold text-slate-800 mt-2">{adminStats.totalConsumers.toLocaleString()}</p>
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
              {adminTransactions.slice(0, 4).map((txn) => (
                <tr key={txn.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-3 font-mono text-xs text-slate-600">{txn.id}</td>
                  <td className="px-5 py-3 text-slate-800 font-medium">{txn.buyer}</td>
                  <td className="px-5 py-3 text-slate-600 hidden md:table-cell">{txn.seller}</td>
                  <td className="px-5 py-3 font-bold text-slate-800">{txn.amount}</td>
                  <td className="px-5 py-3">
                    <Badge variant={txn.status === 'Completed' ? 'success' : txn.status === 'Processing' ? 'info' : 'warning'}>
                      {txn.status}
                    </Badge>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  )
}
