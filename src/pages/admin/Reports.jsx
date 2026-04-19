import { BarChart, Bar, LineChart, Line, XAxis, YAxis, Tooltip, ResponsiveContainer, PieChart, Pie, Cell } from 'recharts'
import { Card } from '../../components/ui'
import { revenueChartData, categoryData, userGrowthData } from '../../data/mockData'

const COLORS = ['#2d8f2d', '#f97316', '#0ea5e9', '#f43f5e', '#8b5cf6']

export default function Reports() {
  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl font-bold text-slate-800">Reports & Analytics</h1>
        <p className="text-slate-500 mt-1">Platform performance metrics and trends</p>
      </div>

      {/* Revenue Over Time */}
      <Card className="p-5 animate-fade-in-up delay-1">
        <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Revenue Over Time</h3>
        <div className="h-72">
          <ResponsiveContainer width="100%" height="100%">
            <LineChart data={revenueChartData}>
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
              <BarChart data={revenueChartData}>
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
                <div className="w-3 h-3 rounded-full" style={{ backgroundColor: COLORS[i] }} />
                {cat.name}: {cat.value}%
              </div>
            ))}
          </div>
        </Card>
      </div>

      {/* Key Metrics Summary */}
      <Card className="p-5 animate-fade-in-up delay-4">
        <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Performance Summary</h3>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-6">
          {[
            { label: 'Avg Order Value', value: '₹3,200', change: '+12%', positive: true },
            { label: 'Farmer Retention', value: '94.5%', change: '+2.3%', positive: true },
            { label: 'Fulfillment Rate', value: '97.8%', change: '+0.5%', positive: true },
            { label: 'Dispute Rate', value: '0.3%', change: '-0.1%', positive: true },
          ].map(m => (
            <div key={m.label} className="text-center">
              <p className="text-2xl font-display font-bold text-slate-800">{m.value}</p>
              <p className="text-xs text-slate-500 mt-1">{m.label}</p>
              <p className={`text-xs font-semibold mt-0.5 ${m.positive ? 'text-leaf-600' : 'text-red-500'}`}>
                {m.change}
              </p>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
