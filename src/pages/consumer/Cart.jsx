import { useState } from 'react'
import { Link } from 'react-router-dom'
import { Trash2, Minus, Plus, ShoppingBag, ArrowRight } from 'lucide-react'
import { Button, EmptyState } from '../../components/ui'
import { consumerProducts } from '../../data/mockData'

export default function Cart() {
  const [items, setItems] = useState([
    { ...consumerProducts[0], qty: 2 },
    { ...consumerProducts[2], qty: 1 },
    { ...consumerProducts[6], qty: 1 },
  ])

  const updateQty = (id, delta) => {
    setItems(items.map(item =>
      item.id === id ? { ...item, qty: Math.max(1, item.qty + delta) } : item
    ))
  }
  const remove = (id) => setItems(items.filter(i => i.id !== id))
  const subtotal = items.reduce((sum, i) => sum + (i.price * i.qty), 0)
  const delivery = subtotal >= 499 ? 0 : 49
  const total = subtotal + delivery

  if (items.length === 0) {
    return (
      <div className="max-w-7xl mx-auto px-4 py-12">
        <EmptyState
          icon={<ShoppingBag className="w-16 h-16" />}
          title="Your cart is empty"
          description="Browse our fresh produce and add items to your cart."
          action={
            <Link to="/consumer/products">
              <Button variant="sky">Start Shopping</Button>
            </Link>
          }
        />
      </div>
    )
  }

  return (
    <div className="max-w-7xl mx-auto px-4 sm:px-6 py-8">
      <h1 className="font-display text-3xl font-bold text-slate-800 animate-fade-in-up">Shopping Cart</h1>
      <p className="text-slate-500 mt-1 mb-6 animate-fade-in-up delay-1">{items.length} items</p>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Cart Items */}
        <div className="lg:col-span-2 space-y-3">
          {items.map((item, i) => (
            <div key={item.id} className={`bg-white rounded-2xl p-4 shadow-card hover:shadow-card-hover transition-all duration-300 animate-fade-in-up delay-${Math.min(i + 2, 6)}`}>
              <div className="flex gap-4">
                <div className="w-20 h-20 rounded-xl bg-gradient-to-br from-leaf-50 to-earth-50 flex items-center justify-center text-3xl shrink-0">
                  {item.image}
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-start justify-between gap-2">
                    <div>
                      <h3 className="font-semibold text-slate-800">{item.name}</h3>
                      <p className="text-xs text-slate-400 mt-0.5">{item.unit} · {item.farmer}</p>
                    </div>
                    <button
                      onClick={() => remove(item.id)}
                      className="p-1.5 text-slate-400 hover:text-red-500 hover:bg-red-50 rounded-lg transition-colors"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                  <div className="flex items-center justify-between mt-3">
                    <div className="flex items-center gap-2">
                      <button onClick={() => updateQty(item.id, -1)} className="w-8 h-8 rounded-lg border border-slate-200 flex items-center justify-center hover:bg-slate-50">
                        <Minus className="w-3 h-3" />
                      </button>
                      <span className="w-6 text-center font-semibold text-sm">{item.qty}</span>
                      <button onClick={() => updateQty(item.id, 1)} className="w-8 h-8 rounded-lg border border-slate-200 flex items-center justify-center hover:bg-slate-50">
                        <Plus className="w-3 h-3" />
                      </button>
                    </div>
                    <p className="font-bold text-slate-800">₹{item.price * item.qty}</p>
                  </div>
                </div>
              </div>
            </div>
          ))}
        </div>

        {/* Order Summary */}
        <div className="lg:col-span-1">
          <div className="bg-white rounded-2xl p-6 shadow-card sticky top-24 animate-fade-in-up delay-4">
            <h3 className="font-display text-lg font-bold text-slate-800 mb-4">Order Summary</h3>
            <div className="space-y-3 text-sm">
              <div className="flex justify-between">
                <span className="text-slate-500">Subtotal</span>
                <span className="font-medium text-slate-700">₹{subtotal}</span>
              </div>
              <div className="flex justify-between">
                <span className="text-slate-500">Delivery</span>
                <span className={`font-medium ${delivery === 0 ? 'text-leaf-600' : 'text-slate-700'}`}>
                  {delivery === 0 ? 'FREE' : `₹${delivery}`}
                </span>
              </div>
              {delivery > 0 && (
                <p className="text-xs text-leaf-600 bg-leaf-50 px-3 py-2 rounded-lg">
                  Add ₹{499 - subtotal} more for free delivery!
                </p>
              )}
              <div className="border-t border-slate-100 pt-3 flex justify-between">
                <span className="font-semibold text-slate-800">Total</span>
                <span className="text-xl font-bold text-slate-800">₹{total}</span>
              </div>
            </div>
            <Button variant="sky" size="lg" className="w-full mt-5">
              Checkout <ArrowRight className="w-5 h-5" />
            </Button>
            <p className="text-xs text-slate-400 text-center mt-3">Free returns within 7 days</p>
          </div>
        </div>
      </div>
    </div>
  )
}
