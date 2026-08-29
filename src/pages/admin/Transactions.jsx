import { Search, Download } from 'lucide-react'
import { useState, useEffect } from 'react'
import { Card, Badge, Button } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, getDocs, query, orderBy } from 'firebase/firestore'
import { Loader2 } from 'lucide-react'

export default function Transactions() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')
  const [transactions, setTransactions] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchTransactions = async () => {
      try {
        const snap = await getDocs(collection(db, 'orders'))
        const txns = snap.docs.map((d, i) => {
          const data = d.data()
          return {
            id: d.id.slice(0, 8).toUpperCase(),
            buyer: data.wholesaler_name || data.consumer_name || data.buyer_name || '—',
            seller: data.farmer_name || data.seller_name || '—',
            item: data.crop_name || data.name || '—',
            amount: data.total_price || 0,
            date: data.created_at?.toDate?.()?.toLocaleDateString('en-IN') ||
                  (data.created_at ? new Date(data.created_at).toLocaleDateString('en-IN') : '—'),
            status: data.status || 'Pending',
          }
        })
        setTransactions(txns)
      } catch (err) {
        console.error('Transactions fetch error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchTransactions()
  }, [])

  const statuses = ['All', 'Completed', 'Processing', 'Pending', 'Delivered']
  const filtered = transactions.filter(t => {
    const matchSearch = t.buyer.toLowerCase().includes(search.toLowerCase()) ||
      t.seller.toLowerCase().includes(search.toLowerCase()) ||
      t.id.toLowerCase().includes(search.toLowerCase()) ||
      t.item.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'All' || t.status === statusFilter
    return matchSearch && matchStatus
  })

  if (loading) {
    return (
      <div className="flex items-center justify-center py-20">
        <Loader2 className="w-8 h-8 text-sky-600 animate-spin" />
      </div>
    )
  }

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-800">Transaction Monitoring</h1>
          <p className="text-slate-500 mt-1">{transactions.length} total transactions</p>
        </div>
        <Button variant="secondary" size="sm">
          <Download className="w-4 h-4" /> Export
        </Button>
      </div>

      {/* Filters */}
      <div className="flex flex-col sm:flex-row gap-3 animate-fade-in-up delay-1">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={e => setSearch(e.target.value)}
            placeholder="Search by ID, buyer, seller, or crop..."
            className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-sm"
          />
        </div>
        <div className="flex gap-2 flex-wrap">
          {statuses.map(s => (
            <button
              key={s}
              onClick={() => setStatusFilter(s)}
              className={`px-3 py-2 rounded-lg text-xs font-semibold transition-all ${
                statusFilter === s ? 'bg-slate-800 text-white' : 'bg-white border border-slate-200 text-slate-500 hover:bg-slate-50'
              }`}
            >
              {s}
            </button>
          ))}
        </div>
      </div>

      {/* Table */}
      <Card className="animate-fade-in-up delay-2">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50">
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">Transaction ID</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">Buyer</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase hidden md:table-cell">Seller</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase hidden sm:table-cell">Item</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">Amount</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase hidden md:table-cell">Date</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase">Status</th>
              </tr>
            </thead>
            <tbody>
              {filtered.length > 0 ? filtered.map((txn) => (
                <tr key={txn.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-4 font-mono text-xs text-slate-600">{txn.id}</td>
                  <td className="px-5 py-4 font-medium text-slate-800">{txn.buyer}</td>
                  <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{txn.seller}</td>
                  <td className="px-5 py-4 text-slate-600 hidden sm:table-cell">{txn.item}</td>
                  <td className="px-5 py-4 font-bold text-slate-800">₹{txn.amount.toLocaleString('en-IN')}</td>
                  <td className="px-5 py-4 text-slate-500 hidden md:table-cell">{txn.date}</td>
                  <td className="px-5 py-4">
                    <Badge variant={txn.status === 'Completed' || txn.status === 'Delivered' ? 'success' : txn.status === 'Processing' ? 'info' : 'warning'}>
                      {txn.status}
                    </Badge>
                  </td>
                </tr>
              )) : (
                <tr>
                  <td colSpan="7" className="px-5 py-8 text-center text-sm text-slate-400">
                    {transactions.length === 0 ? 'No transactions yet' : 'No matching transactions'}
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
