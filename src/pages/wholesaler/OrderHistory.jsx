import { useState, useEffect } from 'react'
import { FileText, Download, Loader2 } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, where, orderBy, getDocs } from 'firebase/firestore'
import { useAuth } from '../../context/AuthContext'
import { toast } from 'react-hot-toast'

export default function OrderHistory() {
  const { user } = useAuth()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return

    const fetchOrders = async () => {
      try {
        setLoading(true)
        const ordersQuery = query(
          collection(db, 'orders'),
          where('wholesaler_id', '==', user.id),
          orderBy('created_at', 'desc')
        )
        const snapshot = await getDocs(ordersQuery)
        const ordersData = snapshot.docs.map(doc => {
          const data = doc.data()
          const date = data.created_at?.toDate ? data.created_at.toDate() : new Date(data.created_at)
          return {
            id: doc.id,
            ...data,
            date: date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' }),
          }
        })
        setOrders(ordersData)
      } catch (err) {
        console.error('Order history fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchOrders()
  }, [user])

  const exportToCsv = (data, filename) => {
    const headers = ['Order ID', 'Crop', 'Farmer', 'Quantity', 'Unit', 'Price/Unit', 'Total', 'Status', 'Date']
    const rows = data.map(o => [
      o.id.slice(0, 8),
      o.crop_name || '',
      o.farmer_name || '',
      o.quantity || 0,
      o.unit || '',
      o.price_per_unit || 0,
      o.total_price || 0,
      o.status || '',
      o.date,
    ])
    const csv = [headers, ...rows].map(r => r.join(',')).join('\n')
    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `${filename}.csv`
    a.click()
    URL.revokeObjectURL(url)
    toast.success('CSV exported!')
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-10 h-10 text-harvest-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl font-bold text-slate-800">Order History</h1>
        <p className="text-slate-500 mt-1">View all past and current orders</p>
      </div>

      <Card className="animate-fade-in-up delay-1">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <p className="text-sm text-slate-500">{orders.length} orders</p>
          <button 
            onClick={() => exportToCsv(orders, 'Order_History')}
            className="flex items-center gap-1.5 text-sm text-harvest-600 font-semibold hover:text-harvest-700 active:scale-95 transition-transform"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>
        <div className="divide-y divide-slate-50">
          {orders.length > 0 ? (
            orders.map((order) => (
              <div key={order.id} className="p-5 hover:bg-slate-50/50 transition-colors">
                <div className="flex items-start justify-between gap-3">
                  <div className="flex items-start gap-3">
                    <div className="w-10 h-10 rounded-xl bg-harvest-50 flex items-center justify-center shrink-0">
                      <FileText className="w-5 h-5 text-harvest-600" />
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800">{order.crop_name || 'Unknown Crop'}</p>
                      <p className="text-sm text-slate-500">from {order.farmer_name || 'Farmer'}</p>
                      <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                        <span>{order.quantity} {order.unit}</span>
                        <span>·</span>
                        <span>₹{order.price_per_unit}/{order.unit}</span>
                        <span>·</span>
                        <span>{order.date}</span>
                      </div>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-bold text-slate-800">₹{(order.total_price || 0).toLocaleString()}</p>
                    <Badge variant={
                      order.status === 'Delivered' ? 'success' :
                      order.status === 'Processing' ? 'info' : 'warning'
                    }>
                      {order.status}
                    </Badge>
                  </div>
                </div>
              </div>
            ))
          ) : (
            <div className="p-12 text-center text-slate-400">
              <FileText className="w-12 h-12 mx-auto mb-3 text-slate-300" />
              <p>No orders yet</p>
            </div>
          )}
        </div>
      </Card>
    </div>
  )
}
