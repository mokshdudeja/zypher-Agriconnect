import { useState, useEffect } from 'react'
import { Warehouse, AlertTriangle, Loader2 } from 'lucide-react'
import { Card, Badge } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, where, getDocs, getDoc, doc } from 'firebase/firestore'
import { useAuth } from '../../context/AuthContext'

export default function Inventory() {
  const { user } = useAuth()
  const [inventory, setInventory] = useState([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (!user) return

    const fetchInventory = async () => {
      try {
        setLoading(true)

        // Get all delivered orders for this wholesaler
        const ordersQuery = query(
          collection(db, 'orders'),
          where('wholesaler_id', '==', user.id),
          where('status', '==', 'Delivered')
        )
        const ordersSnap = await getDocs(ordersQuery)

        // Aggregate by crop
        const cropMap = {}
        for (const orderDoc of ordersSnap.docs) {
          const order = orderDoc.data()
          const cropName = order.crop_name || 'Unknown Crop'
          if (!cropMap[cropName]) {
            cropMap[cropName] = {
              crop: cropName,
              totalPurchased: 0,
              unit: order.unit || 'kg',
              warehouse: 'Warehouse A',
            }
          }
          cropMap[cropName].totalPurchased += order.quantity || 0
        }

        // For simplicity, assume half sold (real app would track sales)
        const inventoryList = Object.values(cropMap).map(item => ({
          id: item.crop,
          crop: item.crop,
          purchased: item.totalPurchased,
          sold: Math.floor(item.totalPurchased * 0.3),
          stock: item.totalPurchased - Math.floor(item.totalPurchased * 0.3),
          unit: item.unit,
          warehouse: item.warehouse,
        }))

        setInventory(inventoryList)
      } catch (err) {
        console.error('Inventory fetch error:', err)
      } finally {
        setLoading(false)
      }
    }

    fetchInventory()
  }, [user])

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
        <h1 className="font-display text-2xl font-bold text-slate-800">Inventory Management</h1>
        <p className="text-slate-500 mt-1">Track your stock levels and warehouses</p>
      </div>

      {/* Inventory Table */}
      <Card className="animate-fade-in-up delay-1">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b border-slate-100 bg-slate-50/50">
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Crop</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Current Stock</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">Purchased</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider hidden md:table-cell">Sold</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Warehouse</th>
                <th className="text-left px-5 py-3.5 text-xs font-semibold text-slate-500 uppercase tracking-wider">Status</th>
              </tr>
            </thead>
            <tbody>
              {inventory.length > 0 ? (
                inventory.map((item) => {
                  const isLow = item.stock < item.purchased * 0.2
                  return (
                    <tr key={item.id} className="border-b border-slate-50 hover:bg-slate-50/50 transition-colors">
                      <td className="px-5 py-4 font-medium text-slate-800">{item.crop}</td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-2">
                          <span className={`font-semibold ${isLow ? 'text-red-600' : 'text-slate-700'}`}>{item.stock} {item.unit}</span>
                          {isLow && <AlertTriangle className="w-4 h-4 text-red-500" />}
                        </div>
                      </td>
                      <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{item.purchased} {item.unit}</td>
                      <td className="px-5 py-4 text-slate-600 hidden md:table-cell">{item.sold} {item.unit}</td>
                      <td className="px-5 py-4">
                        <div className="flex items-center gap-1.5 text-slate-600">
                          <Warehouse className="w-4 h-4 text-slate-400" />
                          {item.warehouse}
                        </div>
                      </td>
                      <td className="px-5 py-4">
                        <Badge variant={isLow ? 'danger' : 'success'}>
                          {isLow ? 'Low Stock' : 'In Stock'}
                        </Badge>
                      </td>
                    </tr>
                  )
                })
              ) : (
                <tr>
                  <td colSpan="6" className="px-5 py-8 text-center text-slate-400">
                    No inventory yet. Completed orders will appear here.
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        </div>
      </Card>

      {/* Stock Level Cards */}
      {inventory.length > 0 && (
        <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 animate-fade-in-up delay-2">
          {inventory.map((item) => {
            const pct = item.purchased > 0 ? Math.round((item.stock / item.purchased) * 100) : 0
            return (
              <div key={item.id} className="bg-white rounded-2xl p-4 shadow-card">
                <p className="text-sm font-semibold text-slate-800">{item.crop}</p>
                <p className="text-xs text-slate-500 mt-0.5">{item.stock} {item.unit} remaining</p>
                <div className="mt-3 bg-slate-100 rounded-full h-2 overflow-hidden">
                  <div
                    className={`h-full rounded-full transition-all duration-700 ${pct < 30 ? 'bg-red-500' : pct < 60 ? 'bg-harvest-500' : 'bg-leaf-500'}`}
                    style={{ width: `${pct}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 mt-1">{pct}% remaining</p>
              </div>
            )
          })}
        </div>
      )}
    </div>
  )
}
