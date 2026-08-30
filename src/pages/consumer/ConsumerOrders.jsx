import { useState, useEffect } from 'react'
import { Package, MapPin, CheckCircle, Clock, Truck, Loader2, Star } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, where, orderBy, onSnapshot } from 'firebase/firestore'
import { useAuth } from '../../context/AuthContext'

const statusIcons = {
  Delivered: CheckCircle,
  'In Transit': Truck,
  Processing: Clock,
  Pending: Clock,
}

const statusColors = {
  Delivered: 'success',
  'In Transit': 'info',
  Processing: 'warning',
  Pending: 'warning',
}

export default function ConsumerOrders() {
  const { user } = useAuth()
  const [orders, setOrders] = useState([])
  const [loading, setLoading] = useState(true)
  const [ratingModal, setRatingModal] = useState(null)
  const [rating, setRating] = useState(5)
  const [review, setReview] = useState('')

  const handleRate = async () => {
    if (!ratingModal) return
    try {
      const { doc, updateDoc } = await import('firebase/firestore')
      const { db } = await import('../../lib/firebase')
      await updateDoc(doc(db, 'orders', ratingModal.id), {
        rating,
        review,
        rated_at: new Date().toISOString(),
      })
      setOrders(prev => prev.map(o => o.id === ratingModal.id ? { ...o, rating, review } : o))
      setRatingModal(null)
      setRating(5)
      setReview('')
    } catch (err) {
      console.error('Rating error:', err)
    }
  }

  useEffect(() => {
    if (!user) return

    setLoading(true)
    let currentUnsub = null

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
        return { id: docSnap.id, ...data, date: dateStr }
      })
      setOrders(ordersData)
      setLoading(false)
    }

    // Try with orderBy, fallback without
    try {
      const qOrdered = query(collection(db, 'orders'), where('consumer_id', '==', user.id), orderBy('created_at', 'desc'))
      currentUnsub = onSnapshot(qOrdered, processSnapshot, (err) => {
        console.error('Orders listener error:', err)
        try {
          if (currentUnsub) currentUnsub()
          const qSimple = query(collection(db, 'orders'), where('consumer_id', '==', user.id))
          currentUnsub = onSnapshot(qSimple, processSnapshot, (err2) => {
            console.error('Orders fallback error:', err2)
            setLoading(false)
          })
        } catch (e) {
          setLoading(false)
        }
      })
    } catch (e) {
      const qSimple = query(collection(db, 'orders'), where('consumer_id', '==', user.id))
      currentUnsub = onSnapshot(qSimple, processSnapshot, (err) => {
        console.error('Orders error:', err)
        setLoading(false)
      })
    }

    return () => { if (currentUnsub) currentUnsub() }
  }, [user])

  if (loading) {
    return (
      <div className="flex justify-center py-20">
        <Loader2 className="w-10 h-10 text-sky-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-3xl font-bold text-slate-800">My Orders</h1>
        <p className="text-slate-500 mt-1">{orders.length} orders</p>
      </div>

      <div className="space-y-4 mt-6">
        {orders.length > 0 ? (
          orders.map((order, i) => {
            const StatusIcon = statusIcons[order.status] || Package
            return (
              <Card key={order.id} className={`p-5 animate-fade-in-up delay-${Math.min(i + 1, 6)}`}>
                <div className="flex items-start justify-between gap-4">
                  <div className="flex items-start gap-4">
                    <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                      order.status === 'Delivered' ? 'bg-leaf-50 text-leaf-600' :
                      order.status === 'In Transit' ? 'bg-sky-50 text-sky-600' :
                      'bg-harvest-50 text-harvest-600'
                    }`}>
                      <StatusIcon className="w-6 h-6" />
                    </div>
                    <div>
                      <div className="flex items-center gap-2 flex-wrap">
                        <p className="font-semibold text-slate-800 font-mono text-sm">{order.id.slice(0, 8)}...</p>
                        <Badge variant={statusColors[order.status] || 'warning'}>{order.status}</Badge>
                      </div>
                      <p className="text-sm text-slate-500 mt-1">{order.crop_name} — {order.quantity} {order.unit}</p>
                      <p className="text-xs text-slate-400 mt-1">Ordered on {order.date}</p>
                    </div>
                  </div>
                  <p className="font-bold text-slate-800 shrink-0">₹{(order.total_price || 0).toLocaleString()}</p>
                </div>

                {/* Tracking Progress */}
                {order.status !== 'Delivered' && order.eta && (
                  <div className="mt-5 pt-4 border-t border-slate-100">
                    <div className="flex items-center gap-2 mb-3">
                      <MapPin className="w-4 h-4 text-sky-500" />
                      <span className="text-sm text-slate-600">Expected by {order.eta}</span>
                    </div>
                    <div className="flex items-center gap-1">
                      {['Confirmed', 'Packing', 'Shipped', 'Out for Delivery', 'Delivered'].map((step, si) => {
                        const activeStep = order.status === 'Processing' ? 1 : order.status === 'In Transit' ? 3 : 0
                        const isActive = si < activeStep
                        return (
                          <div key={step} className="flex-1 flex flex-col items-center gap-1">
                            <div className={`h-1.5 w-full rounded-full ${isActive ? 'bg-sky-500' : 'bg-slate-200'} transition-colors`} />
                            <span className={`text-[10px] ${isActive ? 'text-sky-600 font-semibold' : 'text-slate-400'} hidden sm:block`}>
                              {step}
                            </span>
                          </div>
                        )
                      })}
                    </div>
                  </div>
                )}

                {order.status === 'Delivered' && !order.rating && (
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <button
                      onClick={() => setRatingModal(order)}
                      className="text-sm text-sky-600 font-semibold hover:text-sky-700"
                    >
                      Rate & Review →
                    </button>
                  </div>
                )}
                {order.rating && (
                  <div className="mt-4 pt-3 border-t border-slate-100">
                    <div className="flex items-center gap-1">
                      {[1,2,3,4,5].map(s => (
                        <Star key={s} className={`w-4 h-4 ${s <= order.rating ? 'fill-amber-400 text-amber-400' : 'text-slate-200'}`} />
                      ))}
                      <span className="text-xs text-slate-500 ml-1">Your rating</span>
                    </div>
                    {order.review && <p className="text-xs text-slate-400 mt-1">"{order.review}"</p>}
                  </div>
                )}
              </Card>
            )
          })
        ) : (
          <div className="bg-white rounded-3xl p-12 text-center border-2 border-dashed border-slate-200">
            <Package className="w-12 h-12 text-slate-300 mx-auto mb-4" />
            <h3 className="font-display text-xl font-bold text-slate-800">No orders yet</h3>
            <p className="text-slate-500 mt-2">Your orders will appear here once you make a purchase.</p>
          </div>
        )}
      </div>

      {/* Rating Modal */}
      {ratingModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 animate-fade-in" onClick={() => setRatingModal(null)}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-elevated animate-scale-in" onClick={e => e.stopPropagation()}>
            <h3 className="font-display text-xl font-bold text-slate-800">Rate Your Order</h3>
            <p className="text-sm text-slate-500 mt-1">{ratingModal.crop_name}</p>
            <div className="flex items-center gap-1 mt-4 justify-center">
              {[1,2,3,4,5].map(s => (
                <button key={s} onClick={() => setRating(s)}>
                  <Star className={`w-8 h-8 transition-colors ${s <= rating ? 'fill-amber-400 text-amber-400' : 'text-slate-200 hover:text-amber-200'}`} />
                </button>
              ))}
            </div>
            <textarea
              value={review}
              onChange={e => setReview(e.target.value)}
              placeholder="Write a review (optional)"
              className="w-full mt-4 px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 resize-none"
              rows={3}
            />
            <div className="flex gap-3 mt-4">
              <button onClick={() => setRatingModal(null)} className="flex-1 px-4 py-2.5 bg-slate-100 text-slate-600 rounded-xl text-sm font-semibold hover:bg-slate-200 transition-colors">Cancel</button>
              <button onClick={handleRate} className="flex-1 px-4 py-2.5 bg-sky-600 text-white rounded-xl text-sm font-semibold hover:bg-sky-700 transition-colors">Submit</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
