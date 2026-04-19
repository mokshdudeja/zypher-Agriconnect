/* ===== MOCK DATA FOR AGRI CONNECT ===== */

export const farmerCrops = [
  { id: 1, name: 'Organic Wheat', quantity: '500 kg', harvestDate: '2026-05-15', status: 'Growing', price: '₹28/kg', image: '🌾' },
  { id: 2, name: 'Basmati Rice', quantity: '1200 kg', harvestDate: '2026-06-01', status: 'Ready', price: '₹65/kg', image: '🍚' },
  { id: 3, name: 'Fresh Tomatoes', quantity: '300 kg', harvestDate: '2026-04-20', status: 'Ready', price: '₹40/kg', image: '🍅' },
  { id: 4, name: 'Green Chillies', quantity: '150 kg', harvestDate: '2026-04-25', status: 'Growing', price: '₹80/kg', image: '🌶️' },
  { id: 5, name: 'Onions', quantity: '800 kg', harvestDate: '2026-05-10', status: 'Ready', price: '₹25/kg', image: '🧅' },
]

export const farmerStats = {
  totalListings: 5,
  readyCrops: 3,
  totalRevenue: '₹1,24,500',
  pendingOrders: 2,
}

export const wholesalerDeals = [
  { id: 1, farmer: 'Ramesh Kumar', crop: 'Organic Wheat', qty: '500 kg', price: '₹28/kg', total: '₹14,000', status: 'Active', date: '2026-04-15' },
  { id: 2, farmer: 'Suresh Patel', crop: 'Basmati Rice', qty: '1200 kg', price: '₹62/kg', total: '₹74,400', status: 'Completed', date: '2026-04-10' },
  { id: 3, farmer: 'Lakshmi Devi', crop: 'Fresh Tomatoes', qty: '300 kg', price: '₹38/kg', total: '₹11,400', status: 'Pending', date: '2026-04-18' },
  { id: 4, farmer: 'Anil Sharma', crop: 'Onions', qty: '800 kg', price: '₹24/kg', total: '₹19,200', status: 'Active', date: '2026-04-12' },
]

export const wholesalerInventory = [
  { id: 1, crop: 'Organic Wheat', stock: '350 kg', purchased: '500 kg', sold: '150 kg', warehouse: 'Warehouse A' },
  { id: 2, crop: 'Basmati Rice', stock: '900 kg', purchased: '1200 kg', sold: '300 kg', warehouse: 'Warehouse B' },
  { id: 3, crop: 'Green Chillies', stock: '80 kg', purchased: '150 kg', sold: '70 kg', warehouse: 'Warehouse A' },
  { id: 4, crop: 'Onions', stock: '600 kg', purchased: '800 kg', sold: '200 kg', warehouse: 'Warehouse C' },
]

export const wholesalerListings = [
  { id: 1, farmer: 'Ramesh Kumar', crop: 'Organic Wheat', qty: '500 kg', price: '₹28/kg', location: 'Punjab', rating: 4.5, harvestDate: '2026-05-15' },
  { id: 2, farmer: 'Suresh Patel', crop: 'Basmati Rice', qty: '1200 kg', price: '₹65/kg', location: 'Haryana', rating: 4.8, harvestDate: '2026-06-01' },
  { id: 3, farmer: 'Lakshmi Devi', crop: 'Fresh Tomatoes', qty: '300 kg', price: '₹40/kg', location: 'Karnataka', rating: 4.2, harvestDate: '2026-04-20' },
  { id: 4, farmer: 'Anil Sharma', crop: 'Green Chillies', qty: '150 kg', price: '₹80/kg', location: 'Andhra Pradesh', rating: 4.6, harvestDate: '2026-04-25' },
  { id: 5, farmer: 'Meena Bai', crop: 'Onions', qty: '800 kg', price: '₹25/kg', location: 'Maharashtra', rating: 4.3, harvestDate: '2026-05-10' },
  { id: 6, farmer: 'Gopal Singh', crop: 'Potatoes', qty: '1000 kg', price: '₹18/kg', location: 'Uttar Pradesh', rating: 4.1, harvestDate: '2026-05-20' },
]

export const consumerProducts = [
  { id: 1, name: 'Organic Wheat Flour', price: 65, originalPrice: 80, unit: '1 kg', rating: 4.5, reviews: 128, category: 'Grains', farmer: 'Ramesh Kumar', location: 'Punjab', organic: true, image: '🌾' },
  { id: 2, name: 'Premium Basmati Rice', price: 120, originalPrice: 150, unit: '1 kg', rating: 4.8, reviews: 256, category: 'Grains', farmer: 'Suresh Patel', location: 'Haryana', organic: false, image: '🍚' },
  { id: 3, name: 'Farm Fresh Tomatoes', price: 45, originalPrice: 55, unit: '500g', rating: 4.2, reviews: 89, category: 'Vegetables', farmer: 'Lakshmi Devi', location: 'Karnataka', organic: true, image: '🍅' },
  { id: 4, name: 'Green Chillies Pack', price: 30, originalPrice: 40, unit: '250g', rating: 4.6, reviews: 64, category: 'Vegetables', farmer: 'Anil Sharma', location: 'Andhra Pradesh', organic: true, image: '🌶️' },
  { id: 5, name: 'Crispy Fresh Onions', price: 35, originalPrice: 40, unit: '1 kg', rating: 4.3, reviews: 112, category: 'Vegetables', farmer: 'Meena Bai', location: 'Maharashtra', organic: false, image: '🧅' },
  { id: 6, name: 'Golden Potatoes', price: 28, originalPrice: 35, unit: '1 kg', rating: 4.1, reviews: 95, category: 'Vegetables', farmer: 'Gopal Singh', location: 'UP', organic: false, image: '🥔' },
  { id: 7, name: 'Alphonso Mangoes', price: 350, originalPrice: 450, unit: '1 dozen', rating: 4.9, reviews: 320, category: 'Fruits', farmer: 'Rajesh Patil', location: 'Maharashtra', organic: true, image: '🥭' },
  { id: 8, name: 'Fresh Spinach Bundle', price: 25, originalPrice: 30, unit: '500g', rating: 4.4, reviews: 78, category: 'Vegetables', farmer: 'Sunita Verma', location: 'Rajasthan', organic: true, image: '🥬' },
]

export const consumerOrders = [
  { id: 'AGC-1001', items: ['Organic Wheat Flour', 'Basmati Rice'], total: '₹185', status: 'Delivered', date: '2026-04-10', eta: null },
  { id: 'AGC-1002', items: ['Farm Fresh Tomatoes', 'Green Chillies'], total: '₹75', status: 'In Transit', date: '2026-04-16', eta: '2026-04-19' },
  { id: 'AGC-1003', items: ['Alphonso Mangoes'], total: '₹350', status: 'Processing', date: '2026-04-18', eta: '2026-04-22' },
]

export const adminStats = {
  totalUsers: 12450,
  totalFarmers: 3200,
  totalWholesalers: 890,
  totalConsumers: 8360,
  totalTransactions: 45230,
  totalRevenue: '₹2.4 Cr',
  pendingVerifications: 18,
  activeListings: 1560,
  monthlyGrowth: 12.5,
}

export const adminUsers = [
  { id: 1, name: 'Ramesh Kumar', email: 'ramesh@mail.com', role: 'Farmer', status: 'Verified', joinDate: '2025-08-15', orders: 45 },
  { id: 2, name: 'Priya Wholesalers', email: 'priya@wholesale.com', role: 'Wholesaler', status: 'Verified', joinDate: '2025-09-20', orders: 120 },
  { id: 3, name: 'Amit Consumer', email: 'amit@mail.com', role: 'Consumer', status: 'Active', joinDate: '2025-11-05', orders: 28 },
  { id: 4, name: 'Sunita Organic Farm', email: 'sunita@farm.com', role: 'Farmer', status: 'Pending', joinDate: '2026-04-10', orders: 0 },
  { id: 5, name: 'Green Valley Retail', email: 'greenvalley@retail.com', role: 'Wholesaler', status: 'Pending', joinDate: '2026-04-15', orders: 0 },
  { id: 6, name: 'Ravi Shankar', email: 'ravi@mail.com', role: 'Consumer', status: 'Active', joinDate: '2026-01-12', orders: 15 },
  { id: 7, name: 'Meena Organic', email: 'meena@farm.com', role: 'Farmer', status: 'Verified', joinDate: '2025-07-20', orders: 67 },
  { id: 8, name: 'FreshMart Corp', email: 'fresh@mart.com', role: 'Wholesaler', status: 'Verified', joinDate: '2025-06-01', orders: 230 },
]

export const adminTransactions = [
  { id: 'TXN-001', buyer: 'Priya Wholesalers', seller: 'Ramesh Kumar', item: 'Organic Wheat', amount: '₹14,000', date: '2026-04-15', status: 'Completed' },
  { id: 'TXN-002', buyer: 'Amit Consumer', seller: 'Lakshmi Devi', item: 'Fresh Tomatoes', amount: '₹2,250', date: '2026-04-16', status: 'Completed' },
  { id: 'TXN-003', buyer: 'Green Valley Retail', seller: 'Suresh Patel', item: 'Basmati Rice', amount: '₹74,400', date: '2026-04-17', status: 'Processing' },
  { id: 'TXN-004', buyer: 'Ravi Shankar', seller: 'Meena Bai', item: 'Onions', amount: '₹875', date: '2026-04-18', status: 'Pending' },
  { id: 'TXN-005', buyer: 'FreshMart Corp', seller: 'Gopal Singh', item: 'Potatoes', amount: '₹36,000', date: '2026-04-18', status: 'Processing' },
]

export const adminVerifications = [
  { id: 1, name: 'Sunita Organic Farm', type: 'Farmer', docs: 'Land Record, Aadhaar', submitted: '2026-04-10', status: 'Pending' },
  { id: 2, name: 'Green Valley Retail', type: 'Wholesaler', docs: 'GST, Trade License', submitted: '2026-04-15', status: 'Pending' },
  { id: 3, name: 'Kisan Fresh', type: 'Farmer', docs: 'Land Record, PAN', submitted: '2026-04-12', status: 'Under Review' },
  { id: 4, name: 'Heritage Produce', type: 'Product', docs: 'Organic Certificate', submitted: '2026-04-14', status: 'Pending' },
]

export const revenueChartData = [
  { month: 'Oct', revenue: 18000, orders: 120 },
  { month: 'Nov', revenue: 24000, orders: 180 },
  { month: 'Dec', revenue: 31000, orders: 220 },
  { month: 'Jan', revenue: 28000, orders: 195 },
  { month: 'Feb', revenue: 35000, orders: 260 },
  { month: 'Mar', revenue: 42000, orders: 310 },
  { month: 'Apr', revenue: 48000, orders: 345 },
]

export const categoryData = [
  { name: 'Grains', value: 35 },
  { name: 'Vegetables', value: 30 },
  { name: 'Fruits', value: 25 },
  { name: 'Spices', value: 10 },
]

export const userGrowthData = [
  { month: 'Oct', farmers: 2400, wholesalers: 650, consumers: 5200 },
  { month: 'Nov', farmers: 2600, wholesalers: 700, consumers: 5800 },
  { month: 'Dec', farmers: 2750, wholesalers: 740, consumers: 6400 },
  { month: 'Jan', farmers: 2900, wholesalers: 780, consumers: 7000 },
  { month: 'Feb', farmers: 3000, wholesalers: 830, consumers: 7600 },
  { month: 'Mar', revenue: 3100, wholesalers: 860, consumers: 8000 },
  { month: 'Apr', farmers: 3200, wholesalers: 890, consumers: 8360 },
]
