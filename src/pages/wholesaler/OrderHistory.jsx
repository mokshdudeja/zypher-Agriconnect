import { FileText, Download } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { wholesalerDeals } from '../../data/mockData'
import { exportToCsv } from '../../utils/exportToCsv'

export default function OrderHistory() {
  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl font-bold text-slate-800">Order History</h1>
        <p className="text-slate-500 mt-1">View all past and current orders</p>
      </div>

      <Card className="animate-fade-in-up delay-1">
        <div className="p-5 border-b border-slate-100 flex items-center justify-between">
          <p className="text-sm text-slate-500">{wholesalerDeals.length} orders</p>
          <button 
            onClick={() => exportToCsv(wholesalerDeals, 'Order_History')}
            className="flex items-center gap-1.5 text-sm text-harvest-600 font-semibold hover:text-harvest-700 active:scale-95 transition-transform"
          >
            <Download className="w-4 h-4" /> Export CSV
          </button>
        </div>
        <div className="divide-y divide-slate-50">
          {wholesalerDeals.map((deal) => (
            <div key={deal.id} className="p-5 hover:bg-slate-50/50 transition-colors">
              <div className="flex items-start justify-between gap-3">
                <div className="flex items-start gap-3">
                  <div className="w-10 h-10 rounded-xl bg-harvest-50 flex items-center justify-center shrink-0">
                    <FileText className="w-5 h-5 text-harvest-600" />
                  </div>
                  <div>
                    <p className="font-semibold text-slate-800">{deal.crop}</p>
                    <p className="text-sm text-slate-500">from {deal.farmer}</p>
                    <div className="flex items-center gap-3 mt-1 text-xs text-slate-400">
                      <span>{deal.qty}</span>
                      <span>·</span>
                      <span>{deal.price}</span>
                      <span>·</span>
                      <span>{deal.date}</span>
                    </div>
                  </div>
                </div>
                <div className="text-right shrink-0">
                  <p className="font-bold text-slate-800">{deal.total}</p>
                  <Badge variant={
                    deal.status === 'Completed' ? 'success' :
                    deal.status === 'Active' ? 'info' : 'warning'
                  }>
                    {deal.status}
                  </Badge>
                </div>
              </div>
            </div>
          ))}
        </div>
      </Card>
    </div>
  )
}
