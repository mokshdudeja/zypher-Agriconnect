import { useState } from "react";
import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend,
  ResponsiveContainer,
} from "recharts";
import {
  TrendingUp, TrendingDown, Minus, Cloud, Droplets,
  BarChart3, Activity, Target, Brain, RefreshCw, Search, Sprout,
} from "lucide-react";

const API_BASE = import.meta.env.VITE_API_BASE_URL || import.meta.env.VITE_API_URL || "https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev";

const CROPS = [
  { id: "wheat", name: "Wheat", emoji: "🌾", color: "#F59E0B" },
  { id: "rice", name: "Rice", emoji: "🍚", color: "#10B981" },
  { id: "maize", name: "Maize", emoji: "🌽", color: "#F97316" },
  { id: "cotton", name: "Cotton", emoji: "☁️", color: "#8B5CF6" },
  { id: "sugarcane", name: "Sugarcane", emoji: "🎋", color: "#EF4444" },
  { id: "soybean", name: "Soybean", emoji: "🫘", color: "#06B6D4" },
  { id: "potato", name: "Potato", emoji: "🥔", color: "#A78BFA" },
  { id: "tomato", name: "Tomato", emoji: "🍅", color: "#EC4899" },
  { id: "onion", name: "Onion", emoji: "🧅", color: "#F472B6" },
  { id: "groundnut", name: "Groundnut", emoji: "🥜", color: "#D97706" },
];

const STATES = [
  "uttar_pradesh", "maharashtra", "madhya_pradesh", "west_bengal",
  "rajasthan", "karnataka", "andhra_pradesh", "gujarat", "punjab", "tamil_nadu",
];

const TREND_ICONS = {
  bullish: <TrendingUp className="text-leaf-600" size={20} />,
  bearish: <TrendingDown className="text-red-500" size={20} />,
  stable: <Minus className="text-harvest-500" size={20} />,
};

const TREND_COLORS = {
  bullish: "text-leaf-600",
  bearish: "text-red-500",
  stable: "text-harvest-500",
};

const FACTOR_LABELS = {
  low_rainfall: { label: "Low Rainfall", icon: <Droplets size={14} />, color: "bg-orange-100 text-orange-700" },
  high_rainfall: { label: "High Rainfall", icon: <Cloud size={14} />, color: "bg-sky-100 text-sky-700" },
  high_demand: { label: "High Demand", icon: <TrendingUp size={14} />, color: "bg-leaf-100 text-leaf-700" },
  low_demand: { label: "Low Demand", icon: <TrendingDown size={14} />, color: "bg-red-100 text-red-700" },
  normal_market_conditions: { label: "Normal Market", icon: <Activity size={14} />, color: "bg-slate-100 text-slate-700" },
  export_ban: { label: "Export Restrictions", icon: <Target size={14} />, color: "bg-harvest-100 text-harvest-700" },
};


export default function CropPricePrediction() {
  const [selectedCrop, setSelectedCrop] = useState("wheat");
  const [selectedState, setSelectedState] = useState("uttar_pradesh");
  const [selectedUnit, setSelectedUnit] = useState("quintal");
  const [prediction, setPrediction] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);
  const [historyData, setHistoryData] = useState([]);

  const fetchPrediction = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch(`${API_BASE}/api/predict/${selectedCrop}/${selectedState}?unit=${selectedUnit}`);
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      setPrediction(data);

      // Generate mock chart data based on prediction
      generateChartData(data);
    } catch (err) {
      setError(err.message);
      setPrediction(null);
    } finally {
      setLoading(false);
    }
  };

  const generateChartData = (pred) => {
    const days = 30;
    const chartData = [];
    const basePrice = pred.current_price || 2000;

    for (let i = 0; i <= days; i++) {
      const day = new Date();
      day.setDate(day.getDate() - days + i);

      let predicted;
      if (i <= 7) predicted = basePrice + (pred.predicted_price_7d - basePrice) * (i / 7);
      else if (i <= 15) predicted = pred.predicted_price_7d + (pred.predicted_price_15d - pred.predicted_price_7d) * ((i - 7) / 8);
      else predicted = pred.predicted_price_15d + (pred.predicted_price_30d - pred.predicted_price_15d) * ((i - 15) / 15);

      // Add some realistic noise
      const noise = (Math.sin(i * 0.5) + Math.cos(i * 0.3)) * basePrice * 0.02;

      chartData.push({
        date: day.toLocaleDateString("en-IN", { day: "numeric", month: "short" }),
        price: i < days ? Math.round(basePrice + noise + (predicted - basePrice) * (i / days)) : null,
        predicted: i <= days ? Math.round(predicted + noise * 0.3) : null,
        lower: Math.round(predicted - basePrice * 0.05),
        upper: Math.round(predicted + basePrice * 0.05),
      });
    }
    setHistoryData(chartData);
  };

  return (
    <div className="min-h-screen bg-gradient-to-b from-earth-50 to-leaf-50/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">

        {/* Header */}
        <div className="mb-8 animate-fade-in">
          <div className="flex items-center gap-3 mb-2">
            <div className="w-10 h-10 bg-gradient-to-br from-leaf-500 to-leaf-700 rounded-xl flex items-center justify-center shadow-md">
              <Sprout className="w-6 h-6 text-white" />
            </div>
            <div>
              <h1 className="text-3xl font-bold text-slate-800 font-display">Crop Price Prediction</h1>
              <p className="text-slate-500 text-sm">
                AI-powered price forecasting using XGBoost + LSTM + Prophet ensemble model
              </p>
            </div>
          </div>
        </div>

        {/* Selection Controls */}
        <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-6 mb-6 animate-fade-in">
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* Crop Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Select Crop</label>
              <div className="flex flex-wrap gap-2">
                {CROPS.map((crop) => (
                  <button
                    key={crop.id}
                    onClick={() => setSelectedCrop(crop.id)}
                    className={`px-3 py-1.5 rounded-full text-sm font-medium transition-all ${
                      selectedCrop === crop.id
                        ? "bg-leaf-600 text-white shadow-md"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {crop.emoji} {crop.name}
                  </button>
                ))}
              </div>
            </div>

            {/* State Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Select State</label>
              <select
                value={selectedState}
                onChange={(e) => setSelectedState(e.target.value)}
                className="w-full px-4 py-2 border border-slate-200 rounded-xl focus:ring-2 focus:ring-leaf-500 focus:border-leaf-500"
              >
                {STATES.map((state) => (
                  <option key={state} value={state}>
                    {state.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase())}
                  </option>
                ))}
              </select>
            </div>

            {/* Unit Selection */}
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-2">Price Unit</label>
              <div className="flex gap-2">
                {["kg", "quintal", "tonne"].map((u) => (
                  <button
                    key={u}
                    onClick={() => setSelectedUnit(u)}
                    className={`px-3 py-2 rounded-xl text-sm font-medium transition-all flex-1 ${
                      selectedUnit === u
                        ? "bg-leaf-600 text-white shadow-md"
                        : "bg-slate-100 text-slate-600 hover:bg-slate-200"
                    }`}
                  >
                    {u === "kg" ? "Per kg" : u === "quintal" ? "Per quintal" : "Per tonne"}
                  </button>
                ))}
              </div>
            </div>

            {/* Predict Button */}
            <div className="flex items-end">
              <button
                onClick={fetchPrediction}
                disabled={loading}
                className="w-full px-6 py-2.5 bg-gradient-to-r from-leaf-600 to-leaf-700 text-white rounded-xl font-medium hover:from-leaf-700 hover:to-leaf-800 transition-all disabled:opacity-50 flex items-center justify-center gap-2"
              >
                {loading ? (
                  <RefreshCw className="animate-spin" size={18} />
                ) : (
                  <Search size={18} />
                )}
                {loading ? "Predicting..." : "Get Prediction"}
              </button>
            </div>
          </div>
        </div>

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-xl p-4 mb-6 text-red-700">
            ⚠️ {error}. Make sure the prediction API is running at {API_BASE}
          </div>
        )}

        {prediction && (
          <>
            {/* Price Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-6 animate-fade-in">
              {/* Current Price */}
              <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-slate-500">Current Price</span>
                  <Activity className="text-slate-400" size={18} />
                </div>
                <div className="text-2xl font-bold text-slate-800">
                  ₹{prediction.current_price?.toLocaleString("en-IN") || "—"}
                </div>
                <span className="text-xs text-slate-400">per {selectedUnit}</span>
              </div>

              {/* 7-Day */}
              <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-slate-500">7-Day Forecast</span>
                  {TREND_ICONS[prediction.trend]}
                </div>
                <div className={`text-2xl font-bold ${TREND_COLORS[prediction.trend]}`}>
                  ₹{prediction.predicted_price_7d?.toLocaleString("en-IN") || "—"}
                </div>
                <span className="text-xs text-slate-400">
                  {prediction.current_price > 0
                    ? `${(((prediction.predicted_price_7d - prediction.current_price) / prediction.current_price) * 100).toFixed(1)}%`
                    : "—"}{" "}
                  change
                </span>
              </div>

              {/* 15-Day */}
              <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-slate-500">15-Day Forecast</span>
                  {TREND_ICONS[prediction.trend]}
                </div>
                <div className={`text-2xl font-bold ${TREND_COLORS[prediction.trend]}`}>
                  ₹{prediction.predicted_price_15d?.toLocaleString("en-IN") || "—"}
                </div>
                <span className="text-xs text-slate-400">
                  {prediction.current_price > 0
                    ? `${(((prediction.predicted_price_15d - prediction.current_price) / prediction.current_price) * 100).toFixed(1)}%`
                    : "—"}{" "}
                  change
                </span>
              </div>

              {/* 30-Day */}
              <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-5">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-sm font-medium text-slate-500">30-Day Forecast</span>
                  {TREND_ICONS[prediction.trend]}
                </div>
                <div className={`text-2xl font-bold ${TREND_COLORS[prediction.trend]}`}>
                  ₹{prediction.predicted_price_30d?.toLocaleString("en-IN") || "—"}
                </div>
                <span className="text-xs text-slate-400">
                  {prediction.current_price > 0
                    ? `${(((prediction.predicted_price_30d - prediction.current_price) / prediction.current_price) * 100).toFixed(1)}%`
                    : "—"}{" "}
                  change
                </span>
              </div>
            </div>

            {/* Confidence & Trend */}
            <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-6 animate-fade-in">
              {/* Confidence Gauge */}
              <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <Target size={18} className="text-leaf-600" />
                  Model Confidence
                </h3>
                <div className="relative pt-4">
                  <div className="flex mb-2 items-center justify-between">
                    <span className="text-sm text-slate-500">Confidence Level</span>
                    <span className="text-sm font-bold text-leaf-600">
                      {(prediction.confidence * 100).toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-slate-100 rounded-full h-3">
                    <div
                      className={`h-3 rounded-full transition-all duration-1000 ${
                        prediction.confidence > 0.8
                          ? "bg-gradient-to-r from-leaf-400 to-leaf-500"
                          : prediction.confidence > 0.6
                          ? "bg-gradient-to-r from-yellow-400 to-orange-500"
                          : "bg-gradient-to-r from-red-400 to-red-500"
                      }`}
                      style={{ width: `${prediction.confidence * 100}%` }}
                    />
                  </div>
                  <p className="text-xs text-slate-400 mt-2">
                    {prediction.confidence > 0.8
                      ? "High confidence — models agree on direction"
                      : prediction.confidence > 0.6
                      ? "Moderate confidence — some model disagreement"
                      : "Low confidence — conflicting signals from models"}
                  </p>
                </div>

                {/* Model Weights */}
                {prediction.model_weights && (
                  <div className="mt-6">
                    <h4 className="text-sm font-medium text-slate-700 mb-3">Ensemble Weights</h4>
                    <div className="space-y-2">
                      {Object.entries(prediction.model_weights).map(([model, weight]) => (
                        <div key={model} className="flex items-center gap-3">
                          <span className="text-xs text-slate-500 w-16 capitalize">{model}</span>
                          <div className="flex-1 bg-slate-100 rounded-full h-2">
                            <div
                              className="h-2 rounded-full bg-leaf-500"
                              style={{ width: `${weight * 100}%` }}
                            />
                          </div>
                          <span className="text-xs font-medium text-slate-600 w-10 text-right">
                            {(weight * 100).toFixed(0)}%
                          </span>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Contributing Factors */}
              <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-6">
                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <BarChart3 size={18} className="text-leaf-600" />
                  Market Factors
                </h3>
                <div className="space-y-3">
                  {(prediction.factors || []).map((factor) => {
                    const info = FACTOR_LABELS[factor] || {
                      label: factor,
                      icon: <Activity size={14} />,
                      color: "bg-slate-100 text-slate-700",
                    };
                    return (
                      <div
                        key={factor}
                        className={`flex items-center gap-3 p-3 rounded-xl ${info.color}`}
                      >
                        {info.icon}
                        <span className="text-sm font-medium">{info.label}</span>
                      </div>
                    );
                  })}
                </div>

                {/* Trend Badge */}
                <div className="mt-6 p-4 bg-slate-50 rounded-xl">
                  <div className="flex items-center justify-between">
                    <span className="text-sm text-slate-500">Market Trend</span>
                    <div className="flex items-center gap-2">
                      {TREND_ICONS[prediction.trend]}
                      <span className={`text-lg font-bold capitalize ${TREND_COLORS[prediction.trend]}`}>
                        {prediction.trend}
                      </span>
                    </div>
                  </div>
                </div>
              </div>
            </div>

            {/* Price Chart */}
            {historyData.length > 0 && (
              <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-6 mb-6 animate-fade-in">
                <h3 className="text-lg font-semibold text-slate-800 mb-4 flex items-center gap-2">
                  <BarChart3 size={18} className="text-leaf-600" />
                  30-Day Price Trajectory
                </h3>
                <ResponsiveContainer width="100%" height={350}>
                  <LineChart data={historyData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#f0f0f0" />
                    <XAxis
                      dataKey="date"
                      tick={{ fontSize: 12 }}
                      interval="preserveStartEnd"
                    />
                    <YAxis
                      tick={{ fontSize: 12 }}
                      tickFormatter={(v) => `₹${v}`}
                    />
                    <Tooltip
                      formatter={(value, name) => [`₹${value}`, name]}
                      contentStyle={{ borderRadius: "12px" }}
                    />
                    <Legend />
                    <Line
                      type="monotone"
                      dataKey="price"
                      stroke="#10B981"
                      strokeWidth={2}
                      dot={false}
                      name="Predicted Price"
                    />
                    <Line
                      type="monotone"
                      dataKey="upper"
                      stroke="#D1FAE5"
                      strokeWidth={1}
                      strokeDasharray="5 5"
                      dot={false}
                      name="Upper Bound"
                    />
                    <Line
                      type="monotone"
                      dataKey="lower"
                      stroke="#D1FAE5"
                      strokeWidth={1}
                      strokeDasharray="5 5"
                      dot={false}
                      name="Lower Bound"
                    />
                  </LineChart>
                </ResponsiveContainer>
              </div>
            )}

            {/* Prediction Metadata */}
            <div className="bg-white rounded-2xl shadow-card border border-slate-100 p-6 animate-fade-in">
              <h3 className="text-lg font-semibold text-slate-800 mb-4">Prediction Details</h3>
              <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
                <div>
                  <span className="text-slate-500">Generated at</span>
                  <p className="font-medium">
                    {prediction.generated_at
                      ? new Date(prediction.generated_at).toLocaleString("en-IN")
                      : "—"}
                  </p>
                </div>
                <div>
                  <span className="text-slate-500">Cached</span>
                  <p className="font-medium">{prediction.cached ? "Yes" : "No"}</p>
                </div>
                <div>
                  <span className="text-slate-500">Crop</span>
                  <p className="font-medium capitalize">{prediction.crop}</p>
                </div>
                <div>
                  <span className="text-slate-500">State</span>
                  <p className="font-medium capitalize">
                    {prediction.state?.replace(/_/g, " ")}
                  </p>
                </div>
              </div>
            </div>
          </>
        )}

        {/* Empty State */}
        {!prediction && !loading && !error && (
          <div className="text-center py-20 animate-fade-in">
            <Brain className="mx-auto text-slate-300 mb-4" size={64} />
            <h3 className="text-xl font-semibold text-slate-500 mb-2">
              Select a crop and state
            </h3>
            <p className="text-slate-400">
              Click "Get Prediction" to see AI-powered price forecasts
            </p>
          </div>
        )}
      </div>
    </div>
  );
}
