import { useState, useEffect } from 'react'
import { Package, CheckCircle, XCircle, Clock, Loader2 } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, where, orderBy, onSnapshot, doc, updateDoc } from 'firebase/firestore'
import { useAuth } from '../../context/AuthContext'
import { toast } from 'react-hot-toast'

const statusColors = {
  Delivered: 'success',
  Processing: 'info',
  Pending: 'warning',
  Accepted: 'info',
  Rejected: 'danger',
}

export default function FarmerOrders() {
  const { user } = useAuth()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [updating, setUpdating] = useState(null)

  useEffect(() => {
    if (!user) return

    setLoading(true)

    // Try with orderBy first, fall back without it
    const trySnapshot = (q) => new Promise((resolve, reject) => {
      const unsub = onSnapshot(q, resolve, reject)
      // Store unsub closer so we can clean up on fallback
      unsubRef.current = unsub
    })

    const unsubRef = { current: null }

    const setupListener = async () => {
      try {
        // Try with orderBy
        const qOrdered = query(collection(db, 'orders'), where('farmer_id', '==', user.id), orderBy('created_at', 'desc'))
        const snapshot = await trySnapshot(qOrdered)
        processSnapshot(snapshot)
      } catch (err) {
        // Fallback: no orderBy
        try {
          if (unsubRef.current) unsubRef.current()
          const qSimple = query(collection(db, 'orders'), where('farmer_id', '==', user.id))
          const unsub = onSnapshot(qSimple, (snapshot) => {
            processSnapshot(snapshot)
          }, (err2) => {
            console.error('Orders listener error:', err2)
            toast.error('Failed to load orders')
            setLoading(false)
          })
          unsubRef.current = unsub
        } catch (err2) {
          console.error('Orders fetch error:', err2)
          toast.error('Failed to load orders')
          setLoading(false)
        }
      }
    }

    const processSnapshot = (snapshot) => {
      const ordersData = snapshot.docs.map(docSnap => {
        const data = docSnap.data()
        let dateStr = '—'
        try {
          const date = data.created_at?.toDate ? data.created_at.toDate() : new Date(data.created_at)
          if (!isNaN(date.getTime())) {
            dateStr = date.toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })
          }
        } catch (e) { /* ignore */ }
        return {
          id: docSnap.id,
          ...data,
          date: dateStr,
        }
      })
      setOrders(ordersData)
      setLoading(false)
    }

    setupListener()

    return () => { if (unsubRef.current) unsubRef.current() }
  }, [user])

  const handleAccept = async (orderId) => {
    try {
      setUpdating(orderId)
      await updateDoc(doc(db, 'orders', orderId), {
        status: 'Processing',
        updated_at: new Date().toISOString(),
      })
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'Processing' } : o))
      toast.success('Order accepted!')
    } catch (err) {
      console.error('Accept error:', err)
      toast.error('Failed to accept order')
    } finally {
      setUpdating(null)
    }
  }

  const handleReject = async (orderId) => {
    if (!window.confirm('Are you sure you want to reject this order?')) return
    try {
      setUpdating(orderId)
      await updateDoc(doc(db, 'orders', orderId), {
        status: 'Rejected',
        updated_at: new Date().toISOString(),
      })
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'Rejected' } : o))
      toast.success('Order rejected')
    } catch (err) {
      console.error('Reject error:', err)
      toast.error('Failed to reject order')
    } finally {
      setUpdating(null)
    }
  }

  const handleMarkDelivered = async (orderId) => {
    try {
      setUpdating(orderId)
      await updateDoc(doc(db, 'orders', orderId), {
        status: 'Delivered',
        updated_at: new Date().toISOString(),
      })
      setOrders(prev => prev.map(o => o.id === orderId ? { ...o, status: 'Delivered' } : o))
      toast.success('Order marked as delivered!')
    } catch (err) {
      console.error('Deliver error:', err)
      toast.error('Failed to update order')
    } finally {
      setUpdating(null)
    }
  }

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-10 h-10 text-leaf-600 animate-spin" />
      </div>
    )
  }

  const pendingOrders = orders.filter(o => o.status === 'Pending')
  const activeOrders = orders.filter(o => o.status === 'Processing' || o.status === 'Accepted')
  const completedOrders = orders.filter(o => o.status === 'Delivered' || o.status === 'Rejected')

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl font-bold text-slate-800">Incoming Orders</h1>
        <p className="text-slate-500 mt-1">{pendingOrders.length} pending · {activeOrders.length} active · {completedOrders.length} completed</p>
      </div>

      {/* Pending Orders — Require Action */}
      {pendingOrders.length > 0 && (
        <div className="animate-fade-in-up delay-1">
          <h2 className="font-display text-lg font-bold text-slate-800 mb-3 flex items-center gap-2">
            <Clock className="w-5 h-5 text-harvest-500" /> Pending Orders
          </h2>
          <div className="space-y-3">
            {pendingOrders.map((order) => (
              <Card key={order.id} className="p-5 border-2 border-harvest-200">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-harvest-50 flex items-center justify-center shrink-0">
                      <Package className="w-6 h-6 text-harvest-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-slate-800">{order.crop_name}</p>
                        <Badge variant="warning">Pending</Badge>
                      </div>
                      <p className="text-sm text-slate-500 mt-1">
                        {order.quantity} {order.unit} · ₹{order.price_per_unit}/{order.unit}
                      </p>
                      <p className="text-xs text-slate-400 mt-1">
                        Ordered by {order.wholesaler_name || 'Wholesaler'} · {order.date}
                      </p>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-bold text-slate-800">₹{(order.total_price || 0).toLocaleString()}</p>
                  </div>
                </div>
                <div className="flex gap-3 mt-4 pt-3 border-t border-slate-100">
                  <button
                    onClick={() => handleAccept(order.id)}
                    disabled={updating === order.id}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-leaf-600 hover:bg-leaf-700 text-white rounded-xl text-sm font-bold transition-colors disabled:opacity-50"
                  >
                    <CheckCircle className="w-4 h-4" /> Accept
                  </button>
                  <button
                    onClick={() => handleReject(order.id)}
                    disabled={updating === order.id}
                    className="flex-1 flex items-center justify-center gap-2 px-4 py-2.5 bg-red-50 hover:bg-red-100 text-red-600 border border-red-200 rounded-xl text-sm font-bold transition-colors disabled:opacity-50"
                  >
                    <XCircle className="w-4 h-4" /> Reject
                  </button>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Active Orders */}
      {activeOrders.length > 0 && (
        <div className="animate-fade-in-up delay-2">
          <h2 className="font-display text-lg font-bold text-slate-800 mb-3 flex items-center gap-2">
            <Package className="w-5 h-5 text-sky-500" /> Active Orders
          </h2>
          <div className="space-y-3">
            {activeOrders.map((order) => (
              <Card key={order.id} className="p-5">
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className="w-12 h-12 rounded-xl bg-sky-50 flex items-center justify-center shrink-0">
                      <Package className="w-6 h-6 text-sky-600" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2">
                        <p className="font-semibold text-slate-800">{order.crop_name}</p>
                        <Badge variant="info">{order.status}</Badge>
                      </div>
                      <p className="text-sm text-slate-500 mt-1">
                        {order.quantity} {order.unit} · ₹{order.price_per_unit}/{order.unit}
                      </p>
                      <p className="text-xs text-slate-400 mt-1">
                        {order.wholesaler_name || 'Wholesaler'} · {order.date}
                      </p>
                    </div>
                  </div>
                  <div className="text-right shrink-0">
                    <p className="font-bold text-slate-800">₹{(order.total_price || 0).toLocaleString()}</p>
                    <button
                      onClick={() => handleMarkDelivered(order.id)}
                      disabled={updating === order.id}
                      className="mt-2 px-4 py-2 bg-leaf-600 hover:bg-leaf-700 text-white rounded-lg text-xs font-bold transition-colors disabled:opacity-50"
                    >
                      Mark Delivered
                    </button>
                  </div>
                </div>
              </Card>
            ))}
          </div>
        </div>
      )}

      {/* Completed / Rejected */}
      {completedOrders.length > 0 && (
        <div className="animate-fade-in-up delay-3">
          <h2 className="font-display text-lg font-bold text-slate-800 mb-3">Order History</h2>
          <div className="space-y-3">
            {completedOrders.map((order) => (
              <div key={order.id} className="bg-white rounded-2xl p-4 shadow-card opacity-75">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-3">
                    <div className="w-10 h-10 rounded-xl bg-slate-50 flex items-center justify-center">
                      {order.status === 'Delivered' ? (
                        <CheckCircle className="w-5 h-5 text-leaf-500" />
                      ) : (
                        <XCircle className="w-5 h-5 text-red-400" />
                      )}
                    </div>
                    <div>
                      <p className="font-semibold text-slate-700">{order.crop_name}</p>
                      <p className="text-xs text-slate-400">{order.wholesaler_name || 'Wholesaler'} · {order.date}</p>
                    </div>
                  </div>
                  <div className="text-right">
                    <p className="font-semibold text-slate-600">₹{(order.total_price || 0).toLocaleString()}</p>
                    <Badge variant={order.status === 'Delivered' ? 'success' : 'danger'}>
                      {order.status}
                    </Badge>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </div>
      )}

      {orders.length === 0 && (
        <div className="bg-white rounded-3xl p-12 text-center border-2 border-dashed border-slate-200">
          <Package className="w-12 h-12 text-slate-300 mx-auto mb-4" />
          <h3 className="font-display text-xl font-bold text-slate-800">No orders yet</h3>
          <p className="text-slate-500 mt-2">Orders from wholesalers will appear here.</p>
        </div>
      )}
    </div>
  )
}
