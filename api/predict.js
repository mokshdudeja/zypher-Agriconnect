
export default async function handler(request, response) {
  if (request.method !== 'POST') {
    return response.status(405).json({ error: 'Method not allowed' });
  }

  const today = new Date();
  const { crop } = request.body;

  if (!crop) {
    return response.status(400).json({ error: 'Crop name is required' });
  }

  // Market Prediction Logic (Mocked AI Analysis)
  const basePrices = {
    'Wheat': 2200,
    'Rice': 2500,
    'Corn': 1800,
    'Tomato': 1200,
    'Potato': 1500,
    'Soybean': 4500,
    'Cotton': 6000
  };

  // Simple Seeded PRNG based on crop + date (UTC)
  const dateStr = today.toISOString().split('T')[0];
  const seedStr = `${crop}-${dateStr}`;
  let seed = 0;
  for (let i = 0; i < seedStr.length; i++) {
    seed = ((seed << 5) - seed) + seedStr.charCodeAt(i);
    seed |= 0; 
  }

  // Linear Congruential Generator
  const seededRandom = () => {
    seed = (seed * 1664525 + 1013904223) % 4294967296;
    return seed / 4294967296;
  };

  const basePrice = basePrices[crop] || 1500;
  
  // Simulate market fluctuations for 7 days
  const forecast = [];
  let peakPrice = -1;
  let peakDay = null;

  for (let i = 0; i < 7; i++) {
    const date = new Date(today);
    date.setDate(today.getDate() + i);
    
    // Random walk with slight upward bias
    // Seeded variance
    const variance = (seededRandom() * 400) - 150; 
    const dayPrice = (basePrice + variance) / 100;
    const finalPrice = parseFloat(dayPrice.toFixed(2));

    if (finalPrice > peakPrice) {
      peakPrice = finalPrice;
      peakDay = date.toISOString();
    }

    forecast.push({
      date: date.toISOString(),
      label: i === 0 ? 'Today' : date.toLocaleDateString('en-IN', { weekday: 'short' }),
      price: finalPrice
    });
  }

  return response.status(200).json({
    crop,
    predicted_price: forecast[0].price,
    forecast,
    best_date_to_sell: peakDay,
    trend: forecast[6].price > forecast[0].price ? 'rising' : 'falling',
    confidence: 0.85 + (seededRandom() * 0.1),
    timestamp: new Date().toISOString(),
    provider: "AgriConnect-Vercel-AI"
  });
}
