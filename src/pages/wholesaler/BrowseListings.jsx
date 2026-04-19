import { useState } from 'react'
import { Search, MapPin, Star, Filter, Loader2 } from 'lucide-react'
import { Button, Card, Badge } from '../../components/ui'
import { db } from '../../lib/firebase'
import { collection, query, getDocs, orderBy, addDoc, serverTimestamp } from 'firebase/firestore'
import { useEffect } from 'react'
import { toast } from 'react-hot-toast'
import { useAuth } from '../../context/AuthContext'

export default function BrowseListings() {
  const [search, setSearch] = useState('')
  const [bidModal, setBidModal] = useState(null)
  const [bidAmount, setBidAmount] = useState('')
  const [listings, setListings] = useState([])
  const [loading, setLoading] = useState(true)
  const { user } = useAuth()
  const [submitting, setSubmitting] = useState(false)

  useEffect(() => {
    const fetchListings = async () => {
      try {
        setLoading(true)
        
        // 1. Fetch crops
        const cropsSnap = await getDocs(query(collection(db, 'crops'), orderBy('created_at', 'desc')))
        const cropsData = cropsSnap.docs.map(doc => ({ id: doc.id, ...doc.data() }))

        // 2. Fetch profiles to "join" metadata
        const profilesSnap = await getDocs(collection(db, 'profiles'))
        const profilesMap = {}
        profilesSnap.docs.forEach(doc => {
          profilesMap[doc.id] = doc.data()
        })

        const mapped = cropsData.map(l => ({
          id: l.id,
          farmer_id: l.farmer_id,
          crop: l.name,
          farmer: profilesMap[l.farmer_id]?.name || 'Local Farmer',
          qty: `${l.quantity} ${l.unit}`,
          numericQty: l.quantity,
          unit: l.unit,
          price: `₹${l.price}/${l.unit}`,
          numericPrice: l.price,
          harvestDate: l.harvest_date,
          location: l.location || 'Unknown',
          rating: (4.0 + Math.random()).toFixed(1)
        }))

        setListings(mapped)
      } catch (err) {
        console.error('Fetch error:', err)
        toast.error('Failed to load listings')
      } finally {
        setLoading(false)
      }
    }

    fetchListings()
  }, [])

  const handleSubmitBid = async () => {
    if (!bidAmount || isNaN(parseFloat(bidAmount))) {
      toast.error('Please enter a valid bid amount')
      return
    }

    try {
      setSubmitting(true)
      await addDoc(collection(db, 'bids'), {
        crop_id: bidModal.id,
        crop_name: bidModal.crop,
        farmer_id: bidModal.farmer_id,
        wholesaler_id: user.uid,
        wholesaler_name: user.name || 'Anonymous Wholesaler',
        bid_amount: parseFloat(bidAmount),
        status: 'pending',
        created_at: serverTimestamp()
      })
      
      toast.success(`Successfully placed bid of ₹${bidAmount} for ${bidModal.crop}`)
      setBidModal(null)
      setBidAmount('')
    } catch (err) {
      console.error('Bid error:', err)
      toast.error('Failed to submit bid. Please try again.')
    } finally {
      setSubmitting(false)
    }
  }

  const handleBuyNow = async (listing) => {
    if (!window.confirm(`Buy ${listing.qty} of ${listing.crop} for ${listing.price}?`)) return

    try {
      setSubmitting(true)
      await addDoc(collection(db, 'orders'), {
        listing_id: listing.id,
        crop_name: listing.crop,
        farmer_id: listing.farmer_id,
        wholesaler_id: user.uid,
        wholesaler_name: user.name || 'Anonymous Wholesaler',
        quantity: listing.numericQty,
        unit: listing.unit,
        price_per_unit: listing.numericPrice,
        total_price: listing.numericPrice * listing.numericQty,
        status: 'Pending', // Awaiting farmer acceptance
        created_at: serverTimestamp()
      })
      
      toast.success(`Order placed successfully for ${listing.crop}!`)
    } catch (err) {
      console.error('Buy error:', err)
      toast.error('Failed to place order.')
    } finally {
      setSubmitting(false)
    }
  }

  const filtered = listings.filter(l =>
    l.crop.toLowerCase().includes(search.toLowerCase()) ||
    l.farmer.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl font-bold text-slate-800">Browse Farmer Listings</h1>
        <p className="text-slate-500 mt-1">{filtered.length} listings available</p>
      </div>

      {/* Search + Filter */}
      <div className="flex flex-col sm:flex-row gap-3 animate-fade-in-up delay-1">
        <div className="relative flex-1">
          <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-5 h-5 text-slate-400" />
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search by crop or farmer..."
            className="w-full pl-11 pr-4 py-3 bg-white border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-harvest-500 focus:border-harvest-500"
          />
        </div>
        <Button variant="secondary" className="shrink-0">
          <Filter className="w-4 h-4" /> Filters
        </Button>
      </div>

      {/* Listing Cards */}
      {loading ? (
        <div className="flex justify-center py-20">
          <Loader2 className="w-10 h-10 text-harvest-600 animate-spin" />
        </div>
      ) : filtered.length > 0 ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((listing, i) => (
            <Card key={listing.id} className={`p-5 animate-fade-in-up`}>
              <div className="flex items-start justify-between mb-3">
                <div>
                  <h3 className="font-semibold text-slate-800 text-lg">{listing.crop}</h3>
                  <p className="text-sm text-slate-500">{listing.farmer}</p>
                </div>
                <div className="flex items-center gap-1 text-sm text-amber-500">
                  <Star className="w-4 h-4 fill-current" />
                  <span className="font-semibold">{listing.rating}</span>
                </div>
              </div>

              <div className="space-y-2 mb-4">
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">Quantity</span>
                  <span className="font-medium text-slate-700">{listing.qty}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">Price</span>
                  <span className="font-bold text-harvest-600">{listing.price}</span>
                </div>
                <div className="flex items-center justify-between text-sm">
                  <span className="text-slate-500">Harvest</span>
                  <span className="text-slate-600">{new Date(listing.harvestDate).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}</span>
                </div>
              </div>

              <div className="flex items-center gap-1 text-xs text-slate-400 mb-4">
                <MapPin className="w-3.5 h-3.5" />
                {listing.location}
              </div>

              <div className="flex gap-2">
                <Button 
                  size="sm" 
                  variant="harvest" 
                  className="flex-1" 
                  onClick={() => {
                    setBidModal(listing)
                    setBidAmount(listing.numericPrice.toString())
                  }}
                  disabled={submitting}
                >
                  Place Bid
                </Button>
                <Button 
                  size="sm" 
                  variant="secondary" 
                  className="flex-1"
                  onClick={() => handleBuyNow(listing)}
                  disabled={submitting}
                >
                  Buy Now
                </Button>
              </div>
            </Card>
          ))}
        </div>
      ) : (
        <div className="bg-white rounded-3xl p-12 text-center border-2 border-dashed border-slate-200">
          <div className="w-16 h-16 bg-slate-50 rounded-full flex items-center justify-center mx-auto mb-4">
            <Search className="w-8 h-8 text-slate-300" />
          </div>
          <h3 className="font-display text-xl font-bold text-slate-800">No listings found</h3>
          <p className="text-slate-500 max-w-xs mx-auto mt-2">Try searching for a different crop or farmer name.</p>
        </div>
      )}

      {/* Bid Modal */}
      {bidModal && (
        <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4 animate-fade-in" onClick={() => setBidModal(null)}>
          <div className="bg-white rounded-2xl p-6 w-full max-w-md shadow-elevated animate-scale-in" onClick={e => e.stopPropagation()}>
            <h3 className="font-display text-xl font-bold text-slate-800">Place Bid</h3>
            <p className="text-sm text-slate-500 mt-1">
              {bidModal.crop} from {bidModal.farmer}
            </p>

            <div className="mt-4 p-3 bg-slate-50 rounded-xl">
              <div className="flex justify-between text-sm">
                <span className="text-slate-500">Listed Price</span>
                <span className="font-bold text-slate-800">{bidModal.price}</span>
              </div>
              <div className="flex justify-between text-sm mt-1">
                <span className="text-slate-500">Quantity</span>
                <span className="text-slate-700">{bidModal.qty}</span>
              </div>
            </div>

            <div className="mt-4">
              <label className="block text-sm font-semibold text-slate-700 mb-1.5">Your Bid (₹ per unit)</label>
              <input
                type="number"
                value={bidAmount}
                onChange={(e) => setBidAmount(e.target.value)}
                placeholder="Enter your bid price"
                className="w-full px-4 py-3 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-harvest-500"
              />
            </div>

            <div className="flex gap-3 mt-5">
              <Button variant="secondary" className="flex-1" onClick={() => setBidModal(null)}>Cancel</Button>
              <Button 
                variant="harvest" 
                className="flex-1" 
                onClick={handleSubmitBid}
                disabled={submitting}
              >
                {submitting ? 'Submitting...' : 'Submit Bid'}
              </Button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
