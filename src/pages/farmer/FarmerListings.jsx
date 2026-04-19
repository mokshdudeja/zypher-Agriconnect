import { QrCode, Edit, Trash2, Package, Loader2, Download } from 'lucide-react'
import { QRCodeSVG } from 'qrcode.react'
import { Badge, EmptyState, Button } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, where, getDocs, orderBy, deleteDoc, doc } from 'firebase/firestore'
import { useEffect, useState } from 'react'
import { useAuth } from '../../context/AuthContext'
import { toast } from 'react-hot-toast'

export default function FarmerListings() {
  const { user } = useAuth()
  const [crops, setCrops] = useState([])
  const [loading, setLoading] = useState(true)
  const [showQR, setShowQR] = useState(null)

  const fetchCrops = async () => {
    if (!user) return
    try {
      setLoading(true)
      const cropsRef = collection(db, 'crops')
      const q = query(
        cropsRef, 
        where('farmer_id', '==', user.id),
        orderBy('created_at', 'desc')
      )
      
      const querySnapshot = await getDocs(q)
      const cropsList = querySnapshot.docs.map(doc => ({
        id: doc.id,
        ...doc.data()
      }))
      
      setCrops(cropsList)
    } catch (err) {
      console.error('Fetch crops error:', err)
      toast.error('Failed to load listings')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchCrops()
  }, [user])

  const handleRemove = async (id) => {
    if (!window.confirm('Are you sure you want to remove this listing?')) return
    
    try {
      await deleteDoc(doc(db, 'crops', id))
      
      toast.success('Listing removed')
      setCrops(prev => prev.filter(c => c.id !== id))
    } catch (err) {
      console.error('Delete error:', err)
      toast.error('Failed to remove listing')
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between animate-fade-in-up">
        <div>
          <h1 className="font-display text-2xl font-bold text-slate-800">My Listings</h1>
          <p className="text-slate-500 mt-1">{crops.length} crops listed</p>
        </div>
      </div>

      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-leaf-600 animate-spin" />
        </div>
      ) : crops.length === 0 ? (
        <EmptyState
          icon={<Package className="w-16 h-16" />}
          title="No listings yet"
          description="Add your first crop to start selling on AgriConnect."
          action={
            <Button onClick={() => window.location.href = '/farmer/add-crop'}>
              Add Your First Crop
            </Button>
          }
        />
      ) : (
        <div className="space-y-3">
          {crops.map((crop, i) => (
            <div
              key={crop.id}
              className={`bg-white rounded-2xl p-5 shadow-card hover:shadow-card-hover transition-all duration-300 animate-fade-in-up delay-${Math.min(i + 1, 6)}`}
            >
              <div className="flex items-start gap-4">
                <div className="w-14 h-14 rounded-xl bg-leaf-50 flex items-center justify-center text-3xl shrink-0">
                  {crop.name.toLowerCase().includes('wheat') ? '🌾' : 
                   crop.name.toLowerCase().includes('rice') ? '🍚' : 
                   crop.name.toLowerCase().includes('corn') ? '🌽' : '🥦'}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-semibold text-slate-800 text-lg">{crop.name}</h3>
                      <p className="text-sm text-slate-500 mt-0.5">
                        {crop.quantity} {crop.unit} · ₹{crop.price}/{crop.unit}
                      </p>
                    </div>
                    <Badge variant={crop.status === 'Ready' ? 'success' : 'warning'}>
                      {crop.status}
                    </Badge>
                  </div>
                  <p className="text-xs text-slate-400 mt-1">
                    Harvest: {new Date(crop.harvest_date).toLocaleDateString('en-IN', { day: 'numeric', month: 'short', year: 'numeric' })}
                  </p>
 
                  {/* Action Buttons */}
                  <div className="flex items-center gap-2 mt-3">
                    <button
                      onClick={() => setShowQR(showQR === crop.id ? null : crop.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-leaf-700 bg-leaf-50 hover:bg-leaf-100 rounded-lg transition-colors"
                    >
                      <QrCode className="w-3.5 h-3.5" /> QR Code
                    </button>
                    <button className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-slate-600 bg-slate-50 hover:bg-slate-100 rounded-lg transition-colors">
                      <Edit className="w-3.5 h-3.5" /> Edit
                    </button>
                    <button
                      onClick={() => handleRemove(crop.id)}
                      className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-semibold text-red-600 bg-red-50 hover:bg-red-100 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-3.5 h-3.5" /> Remove
                    </button>
                  </div>

                  {/* QR Code Section */}
                  {showQR === crop.id && (
                    <div className="mt-4 p-4 bg-slate-50 rounded-2xl border border-slate-100 animate-scale-in flex flex-col items-center">
                      <div className="bg-white p-3 rounded-xl shadow-sm border border-slate-100" id={`qr-wrapper-${crop.id}`}>
                        <QRCodeSVG 
                          id={`qr-svg-${crop.id}`}
                          value={`${window.location.origin}/consumer/products/${crop.id}`}
                          size={128}
                          level="H"
                          includeMargin={true}
                        />
                      </div>
                      <p className="text-xs text-slate-500 mt-3 font-medium">Digital Passport for {crop.name}</p>
                      <button 
                        onClick={() => {
                          const svg = document.getElementById(`qr-svg-${crop.id}`);
                          if (svg) {
                            const svgData = new XMLSerializer().serializeToString(svg);
                            const canvas = document.createElement("canvas");
                            const ctx = canvas.getContext("2d");
                            const img = new Image();
                            img.onload = () => {
                              canvas.width = img.width;
                              canvas.height = img.height;
                              ctx.drawImage(img, 0, 0);
                              const pngFile = canvas.toDataURL("image/png");
                              const downloadLink = document.createElement("a");
                              downloadLink.download = `QR_${crop.name}.png`;
                              downloadLink.href = pngFile;
                              downloadLink.click();
                            };
                            img.src = "data:image/svg+xml;base64," + btoa(svgData);
                          }
                        }}
                        className="mt-3 inline-flex items-center gap-1.5 text-xs font-semibold text-sky-600 hover:text-sky-700 bg-sky-50 px-3 py-1.5 rounded-lg transition-colors border border-sky-100"
                      >
                        <Download className="w-3.5 h-3.5" /> Download QR
                      </button>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
