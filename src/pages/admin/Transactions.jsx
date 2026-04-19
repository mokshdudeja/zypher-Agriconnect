import { Search, Download } from 'lucide-react'
import { useState } from 'react'
import { Card, Badge, Button } from '../../components/ui'
import { adminTransactions } from '../../data/mockData'

export default function Transactions() {
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('All')

  const statuses = ['All', 'Completed', 'Processing', 'Pending']
  const filtered = adminTransactions.filter(t => {
    const matchSearch = t.buyer.toLowerCase().includes(search.toLowerCase()) || t.seller.toLowerCase().includes(search.toLowerCase()) || t.id.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'All' || t.status === statusFilter
    return matchSearch && matchStatus
  })

  return (
    <div className="space-y-6 max-w-7xl mx-auto">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 animate-fade-in-up">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-800">Transaction Monitoring</h1>
          <p className="text-slate-500 mt-1">{adminTransactions.length} total transactions</p>
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
            placeholder="Search by ID, buyer, or seller..."
            className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-sky-500 shadow-sm"
          />
        </div>
        <div className="flex gap-2">
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
              {filtered.map((txn) => (
                <tr key={txn.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                  <td className="px-5 py-4 font-mono text-xs text-slate-600">{txn.id}</td>
                  <td className="px-5 py-4 font-medium text-slate-800">{txn.buyer}</td>
                  <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{txn.seller}</td>
                  <td className="px-5 py-4 text-slate-600 hidden sm:table-cell">{txn.item}</td>
                  <td className="px-5 py-4 font-bold text-slate-800">{txn.amount}</td>
                  <td className="px-5 py-4 text-slate-500 hidden md:table-cell">{txn.date}</td>
                  <td className="px-5 py-4">
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
