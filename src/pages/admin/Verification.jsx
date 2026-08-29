import { useState, useEffect } from 'react'
import { Clock, FileText, CheckCircle, XCircle } from 'lucide-react'
import { Card, Badge, Button } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, getDocs, doc, updateDoc } from 'firebase/firestore'
import { Loader2 } from 'lucide-react'

export default function Verification() {
  const [items, setItems] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchVerifications = async () => {
      try {
        const snap = await getDocs(collection(db, 'profiles'))
        const verifications = snap.docs
          .map(d => {
            const data = d.data()
            return {
              id: d.id,
              name: data.name || 'Unknown',
              type: data.role ? data.role.charAt(0).toUpperCase() + data.role.slice(1) : 'Farmer',
              docs: data.documents || data.docs || 'Documents not uploaded',
              submitted: data.created_at?.toDate?.()?.toLocaleDateString('en-IN') ||
                         (data.created_at ? new Date(data.created_at).toLocaleDateString('en-IN') : '—'),
              status: data.verified === true ? 'Approved' : data.status || 'Pending',
            }
          })
          .filter(u => u.status !== 'Approved' || Math.random() > 0.7) // Show some pending + recent
        setItems(verifications)
      } catch (err) {
        console.error('Verification fetch error:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchVerifications()
  }, [])

  const approve = async (id) => {
    try {
      await updateDoc(doc(db, 'profiles', id), { verified: true, status: 'Verified' })
      setItems(items.map(i => i.id === id ? { ...i, status: 'Approved' } : i))
    } catch (err) {
      console.error('Approve error:', err)
    }
  }

  const reject = async (id) => {
    try {
      await updateDoc(doc(db, 'profiles', id), { verified: false, status: 'Rejected' })
      setItems(items.map(i => i.id === id ? { ...i, status: 'Rejected' } : i))
    } catch (err) {
      console.error('Reject error:', err)
    }
  }

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
        <h1 className="font-display text-2xl font-bold text-slate-800">Verification Panel</h1>
        <p className="text-slate-500 mt-1">{items.filter(i => i.status === 'Pending' || i.status === 'Under Review').length} pending reviews</p>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 sm:grid-cols-4 gap-4 animate-fade-in-up delay-1">
        <div className="bg-white rounded-2xl p-4 shadow-card text-center">
          <p className="text-2xl font-bold text-slate-800">{items.length}</p>
          <p className="text-xs text-slate-500 mt-1">Total Requests</p>
        </div>
        <div className="bg-amber-50 rounded-2xl p-4 shadow-card text-center border border-amber-200">
          <p className="text-2xl font-bold text-amber-600">{items.filter(i => i.status === 'Pending').length}</p>
          <p className="text-xs text-slate-500 mt-1">Pending</p>
        </div>
        <div className="bg-leaf-50 rounded-2xl p-4 shadow-card text-center border border-leaf-200">
          <p className="text-2xl font-bold text-leaf-600">{items.filter(i => i.status === 'Approved').length}</p>
          <p className="text-xs text-slate-500 mt-1">Approved</p>
        </div>
        <div className="bg-red-50 rounded-2xl p-4 shadow-card text-center border border-red-200">
          <p className="text-2xl font-bold text-red-600">{items.filter(i => i.status === 'Rejected').length}</p>
          <p className="text-xs text-slate-500 mt-1">Rejected</p>
        </div>
      </div>

      {/* Verification Items */}
      <div className="space-y-3">
        {items.length > 0 ? items.map((item, i) => (
          <Card key={item.id} className="p-5 animate-fade-in-up">
            <div className="flex flex-col sm:flex-row sm:items-center gap-4">
              <div className="flex items-start gap-4 flex-1">
                <div className={`w-12 h-12 rounded-xl flex items-center justify-center shrink-0 ${
                  item.status === 'Approved' ? 'bg-leaf-50 text-leaf-600' :
                  item.status === 'Rejected' ? 'bg-red-50 text-red-600' :
                  'bg-amber-50 text-amber-600'
                }`}>
                  {item.status === 'Approved' ? <CheckCircle className="w-6 h-6" /> :
                   item.status === 'Rejected' ? <XCircle className="w-6 h-6" /> :
                   <Clock className="w-6 h-6" />}
                </div>
                <div className="min-w-0">
                  <div className="flex items-center gap-2 flex-wrap">
                    <h3 className="font-semibold text-slate-800">{item.name}</h3>
                    <Badge variant={
                      item.type === 'Farmer' ? 'success' :
                      item.type === 'Wholesaler' ? 'warning' : 'info'
                    }>
                      {item.type}
                    </Badge>
                  </div>
                  <div className="flex items-center gap-2 mt-1 text-sm text-slate-500">
                    <FileText className="w-3.5 h-3.5" />
                    {item.docs}
                  </div>
                  <p className="text-xs text-slate-400 mt-1">Submitted: {item.submitted}</p>
                </div>
              </div>

              <div className="flex items-center gap-2 sm:shrink-0">
                <Badge variant={
                  item.status === 'Approved' ? 'success' :
                  item.status === 'Rejected' ? 'danger' :
                  item.status === 'Under Review' ? 'info' : 'pending'
                }>
                  {item.status}
                </Badge>

                {(item.status === 'Pending' || item.status === 'Under Review') && (
                  <div className="flex gap-2 ml-2">
                    <Button size="sm" variant="primary" onClick={() => approve(item.id)}>
                      <CheckCircle className="w-4 h-4" /> Approve
                    </Button>
                    <Button size="sm" variant="danger" onClick={() => reject(item.id)}>
                      <XCircle className="w-4 h-4" /> Reject
                    </Button>
                  </div>
                )}
              </div>
            </div>
          </Card>
        )) : (
          <Card className="p-8 text-center text-sm text-slate-400">
            No verification requests yet
          </Card>
        )}
      </div>
    </div>
  )
}
