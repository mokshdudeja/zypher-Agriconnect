
/**
 * AWS Lambda Function for AgriConnect Market Price Prediction
 * Expected Event Structure: { "crop": "Wheat" }
 * Returns: { "predicted_price": number, "trend": string }
 */
export const handler = async (event) => {
  // Parse incoming request (handles both direct and Function URL formats)
  let body = event;
  if (event.body) {
    body = JSON.parse(event.body);
  }

  const { crop } = body;
  
  if (!crop) {
    return {
      statusCode: 400,
      body: JSON.stringify({ error: "Crop name is required" })
    };
  }

  // Basic prediction logic (simulating market trend analysis)
  const basePrices = {
    'Wheat': 2200,
    'Rice': 2500,
    'Corn': 1800,
    'Tomato': 1200,
    'Potato': 1500
  };

  const basePrice = basePrices[crop] || 1000;
  const variance = Math.floor(Math.random() * 200) - 100; // ±100
  const trend = Math.random() > 0.5 ? 'rising' : 'falling';
  const predictedPrice = (basePrice + variance) / 100; // Return in per kg format

  const responseBody = {
    crop,
    predicted_price: parseFloat(predictedPrice.toFixed(2)),
    trend,
    currency: "INR",
    timestamp: new Date().toISOString()
  };

  return {
    statusCode: 200,
    headers: {
      "Content-Type": "application/json",
      "Access-Control-Allow-Origin": "*" // Required for CORS
    },
    body: JSON.stringify(responseBody)
  };
};
