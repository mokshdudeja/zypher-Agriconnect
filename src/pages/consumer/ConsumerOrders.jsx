import { Package, MapPin, CheckCircle, Clock, Truck } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { consumerOrders } from '../../data/mockData'

const statusIcons = {
  Delivered: CheckCircle,
  'In Transit': Truck,
  Processing: Clock,
}

const statusColors = {
  Delivered: 'success',
  'In Transit': 'info',
  Processing: 'warning',
}

export default function ConsumerOrders() {
  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-3xl font-bold text-slate-800">My Orders</h1>
        <p className="text-slate-500 mt-1">{consumerOrders.length} orders</p>
      </div>

      <div className="space-y-4 mt-6">
        {consumerOrders.map((order, i) => {
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
                      <p className="font-semibold text-slate-800 font-mono text-sm">{order.id}</p>
                      <Badge variant={statusColors[order.status]}>{order.status}</Badge>
                    </div>
                    <p className="text-sm text-slate-500 mt-1">{order.items.join(', ')}</p>
                    <p className="text-xs text-slate-400 mt-1">Ordered on {order.date}</p>
                  </div>
                </div>
                <p className="font-bold text-slate-800 shrink-0">{order.total}</p>
              </div>

              {/* Tracking Progress */}
              {order.status !== 'Delivered' && (
                <div className="mt-5 pt-4 border-t border-slate-100">
                  <div className="flex items-center gap-2 mb-3">
                    <MapPin className="w-4 h-4 text-sky-500" />
                    <span className="text-sm text-slate-600">Expected by {order.eta}</span>
                  </div>
                  <div className="flex items-center gap-1">
                    {['Confirmed', 'Packing', 'Shipped', 'Out for Delivery', 'Delivered'].map((step, si) => {
                      const activeStep = order.status === 'Processing' ? 1 : order.status === 'In Transit' ? 3 : 5
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

              {order.status === 'Delivered' && (
                <div className="mt-4 pt-3 border-t border-slate-100">
                  <button className="text-sm text-sky-600 font-semibold hover:text-sky-700">
                    Rate & Review →
                  </button>
                </div>
              )}
            </Card>
          )
        })}
      </div>
    </div>
  )
}
