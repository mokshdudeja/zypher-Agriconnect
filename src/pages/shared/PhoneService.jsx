import { useState } from 'react'
import { Phone, Mic, ShoppingCart, Cloud, User, Package, BarChart3, ArrowRight, Star, CheckCircle, Volume2, Hash, Sprout, MessageCircle, Headphones, Zap } from 'lucide-react'

const callSteps = [
  {
    step: 1,
    icon: <Phone className="w-6 h-6" />,
    title: "कॉल करें",
    titleEn: "Make a Call",
    description: "अपने फ़ोन से AgriConnect नंबर पर कॉल करें। कोई स्मार्टफ़ोन की ज़रूरत नहीं।",
    descriptionEn: "Call the AgriConnect number from any phone. No smartphone needed.",
  },
  {
    step: 2,
    icon: <Hash className="w-6 h-6" />,
    title: "मेनू चुनें",
    titleEn: "Choose Menu",
    description: "अपनी भाषा में सुनें और बटन दबाएं: 1=कीमत, 2=मौसम, 3=प्रोफाइल, 4=फसल, 5=ऑर्डर",
    descriptionEn: "Listen in your language and press: 1=Price, 2=Weather, 3=Profile, 4=Crops, 5=Orders",
  },
  {
    step: 3,
    icon: <Mic className="w-6 h-6" />,
    title: "बोलें या दबाएं",
    titleEn: "Speak or Press",
    description: "फसल का नाम बोलें (हिंदी/अंग्रेज़ी) या बटन दबाकर जानकारी लें।",
    descriptionEn: "Say crop name in Hindi/English or press buttons for info.",
  },
  {
    step: 4,
    icon: <Volume2 className="w-6 h-6" />,
    title: "जवाब सुनें",
    titleEn: "Hear Response",
    description: "AI आपको फसल की कीमत, मौसम, या ऑर्डर की जानकारी हिंदी में बताएगा।",
    descriptionEn: "AI tells you crop prices, weather, or orders in Hindi.",
  },
]

const features = [
  {
    icon: <BarChart3 className="w-8 h-8 text-leaf-600" />,
    title: "फसल की कीमत",
    titleEn: "Crop Prices",
    description: "AI से भविष्य की कीमत का अनुमान — 7, 15, 30 दिन",
    descriptionEn: "AI price predictions — 7, 15, 30 day forecasts",
    keyword: "1 दबाएं",
  },
  {
    icon: <Cloud className="w-8 h-8 text-sky-600" />,
    title: "मौसम की जानकारी",
    titleEn: "Weather",
    description: "तापमान, बारिश, नमी — और खेती के सुझाव",
    descriptionEn: "Temperature, rainfall, humidity + farming advice",
    keyword: "2 दबाएं",
  },
  {
    icon: <User className="w-8 h-8 text-harvest-600" />,
    title: "प्रोफाइल प्रबंधन",
    titleEn: "Profile",
    description: "अपना नाम, फ़ोन, स्थान अपडेट करें",
    descriptionEn: "Update your name, phone, location",
    keyword: "3 दबाएं",
  },
  {
    icon: <Package className="w-8 h-8 text-earth-600" />,
    title: "फसल सूची",
    titleEn: "Crop Listings",
    description: "नई फसल जोड़ें, कीमत बदलें, बेची गई मार्क करें",
    descriptionEn: "Add new crop, change price, mark as sold",
    keyword: "4 दबाएं",
  },
  {
    icon: <ShoppingCart className="w-8 h-8 text-red-600" />,
    title: "ऑर्डर प्रबंधन",
    titleEn: "Orders",
    description: "नए ऑर्डर देखें, स्वीकार/अस्वीकार करें",
    descriptionEn: "View new orders, accept/reject",
    keyword: "5 दबाएं",
  },
  {
    icon: <Star className="w-8 h-8 text-harvest-500" />,
    title: "नई फसल जोड़ें",
    titleEn: "Add Crop",
    description: "बोलकर या बटन दबाकर फसल सूची में जोड़ें",
    descriptionEn: "Add to listings by speaking or pressing buttons",
    keyword: "6 दबाएं",
  },
]

const languages = [
  { code: "hi", name: "हिंदी", speakers: "600M+" },
  { code: "ta", name: "தமிழ்", speakers: "75M+" },
  { code: "te", name: "తెలుగు", speakers: "80M+" },
  { code: "kn", name: "ಕನ್ನಡ", speakers: "50M+" },
  { code: "mr", name: "मराठी", speakers: "80M+" },
  { code: "bn", name: "বাংলা", speakers: "100M+" },
]

export default function PhoneService() {
  const [activeTab, setActiveTab] = useState('how')

  return (
    <div className="min-h-screen bg-gradient-to-b from-earth-50 to-leaf-50/30">
      <div className="max-w-6xl mx-auto px-4 sm:px-6 py-8">

        {/* Hero */}
        <div className="text-center mb-12 animate-fade-in-up">
          <div className="inline-flex items-center gap-2 px-4 py-2 bg-leaf-100 text-leaf-700 rounded-full text-sm font-semibold mb-4">
            <Phone className="w-4 h-4" />
            कोई स्मार्टफ़ोन नहीं? कोई बात नहीं!
          </div>
          <h1 className="text-4xl sm:text-5xl font-bold text-slate-800 mb-4">
            <span className="font-display">फ़ोन से <span className="text-leaf-600">कृषि सेवा</span></span>
          </h1>
          <h2 className="text-xl sm:text-2xl font-semibold text-slate-500 mb-4 font-display">
            Phone-Based Farming Platform
          </h2>
          <p className="text-slate-500 max-w-2xl mx-auto text-lg">
            बिना स्मार्टफ़ोन के भी AI-संचालित कृषि सेवाओं का उपयोग करें।
            बस कॉल करें, बोलें, और जानकारी पाएं।
          </p>
          <div className="mt-6 inline-flex items-center gap-4 px-6 py-4 bg-gradient-to-br from-leaf-600 to-leaf-700 text-white rounded-2xl shadow-elevated">
            <div className="w-12 h-12 bg-white/15 rounded-xl flex items-center justify-center backdrop-blur-sm">
              <Phone className="w-6 h-6" />
            </div>
            <div className="text-left">
              <p className="text-sm font-medium text-leaf-200">अभी कॉल करें</p>
              <p className="text-2xl font-bold tracking-wide font-display">01141183996</p>
            </div>
          </div>
        </div>

        {/* Tabs */}
        <div className="flex justify-center gap-2 mb-8">
          {[
            { id: 'how', label: 'कैसे काम करता है' },
            { id: 'features', label: 'सुविधाएँ' },
            { id: 'languages', label: 'भाषाएँ' },
            { id: 'demo', label: 'डेमो' },
          ].map((tab) => (
            <button
              key={tab.id}
              onClick={() => setActiveTab(tab.id)}
              className={`px-4 py-2 rounded-xl text-sm font-semibold transition-all ${
                activeTab === tab.id
                  ? 'bg-leaf-600 text-white shadow-md'
                  : 'bg-white text-slate-600 border border-slate-200 hover:bg-slate-50'
              }`}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {/* How it Works */}
        {activeTab === 'how' && (
          <div className="space-y-8 animate-fade-in">
            <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
              {callSteps.map((step, i) => (
                <div key={i} className="bg-white rounded-2xl p-6 shadow-card border border-slate-100 hover:shadow-card-hover transition-all">
                  <div className="w-12 h-12 bg-leaf-100 text-leaf-600 rounded-xl flex items-center justify-center mb-4">
                    {step.icon}
                  </div>
                  <div className="text-xs text-leaf-600 font-bold mb-1">Step {step.step}</div>
                  <h3 className="font-bold text-slate-800 text-lg font-display">{step.title}</h3>
                  <p className="text-sm text-slate-400 mb-2">{step.titleEn}</p>
                  <p className="text-sm text-slate-600">{step.description}</p>
                  <p className="text-xs text-slate-400 mt-1">{step.descriptionEn}</p>
                </div>
              ))}
            </div>

            {/* Phone Mockup */}
            <div className="bg-white rounded-3xl p-8 shadow-card border border-slate-100 max-w-md mx-auto">
              <div className="text-center mb-6">
                <div className="w-20 h-20 bg-leaf-100 rounded-full flex items-center justify-center mx-auto mb-4">
                  <Phone className="w-10 h-10 text-leaf-600" />
                </div>
                <h3 className="font-bold text-xl text-slate-800 font-display">AgriConnect कॉल फ़्लो</h3>
              </div>
              <div className="space-y-3">
                {[
                  { ring: "📞 कॉल लगती है...", color: "bg-sky-50 text-sky-700 border border-sky-100" },
                  { ring: '🤖 "नमस्ते! कृपया विकल्प चुनें..."', color: "bg-leaf-50 text-leaf-700 border border-leaf-100" },
                  { ring: '👆 किसान: [1] दबाता है', color: "bg-harvest-50 text-harvest-700 border border-harvest-100" },
                  { ring: '🤖 "फसल का नाम बोलें..."', color: "bg-leaf-50 text-leaf-700 border border-leaf-100" },
                  { ring: '🗣️ किसान: "गेहूं"', color: "bg-earth-50 text-earth-700 border border-earth-100" },
                  { ring: '🤖 "गेहूं की कीमत ₹2042 है..."', color: "bg-leaf-50 text-leaf-700 border border-leaf-100" },
                ].map((item, i) => (
                  <div key={i} className={`${item.color} rounded-xl px-4 py-3 text-sm font-medium`}>
                    {item.ring}
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}

        {/* Features */}
        {activeTab === 'features' && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 animate-fade-in">
            {features.map((f, i) => (
              <div key={i} className="bg-white rounded-2xl p-6 shadow-card border border-slate-100 hover:shadow-card-hover transition-all">
                <div className="mb-4">{f.icon}</div>
                <h3 className="font-bold text-slate-800 text-lg font-display">{f.title}</h3>
                <p className="text-sm text-slate-400 mb-2">{f.titleEn}</p>
                <p className="text-sm text-slate-600 mb-3">{f.description}</p>
                <div className="inline-flex items-center gap-1 px-3 py-1 bg-leaf-50 text-leaf-700 rounded-full text-xs font-bold border border-leaf-100">
                  <Hash className="w-3 h-3" /> {f.keyword}
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Languages */}
        {activeTab === 'languages' && (
          <div className="animate-fade-in">
            <div className="bg-white rounded-2xl p-8 shadow-card border border-slate-100 max-w-2xl mx-auto">
              <h3 className="font-bold text-xl text-slate-800 mb-2 text-center font-display">11+ भाषाओं में सेवा</h3>
              <p className="text-sm text-slate-500 text-center mb-6">Service in 11+ Indian languages</p>
              <div className="grid grid-cols-2 sm:grid-cols-3 gap-4">
                {languages.map((lang) => (
                  <div key={lang.code} className="flex items-center gap-3 p-3 bg-slate-50 rounded-xl border border-slate-100">
                    <div className="w-10 h-10 bg-leaf-100 rounded-full flex items-center justify-center text-sm font-bold text-leaf-700">
                      {lang.code.toUpperCase()}
                    </div>
                    <div>
                      <p className="font-semibold text-slate-800">{lang.name}</p>
                      <p className="text-xs text-slate-400">{lang.speakers} speakers</p>
                    </div>
                  </div>
                ))}
              </div>
              <p className="text-sm text-slate-500 text-center mt-6">
                बोलने वाली AI तकनीक (Sarvam AI) सभी भाषाओं में प्राकृतिक आवाज़ में जवाब देती है।
              </p>
            </div>
          </div>
        )}

        {/* Demo */}
        {activeTab === 'demo' && (
          <div className="animate-fade-in max-w-2xl mx-auto">
            <div className="bg-white rounded-2xl p-8 shadow-card border border-slate-100">
              <h3 className="font-bold text-xl text-slate-800 mb-6 text-center font-display">डेमो कॉल फ़्लो</h3>
              <div className="space-y-4">
                {[
                  { side: 'phone', text: "📞 *555# डायल करते हैं", time: "0:00" },
                  { side: 'ai', text: '🤖 "नमस्ते राम जी! AgriConnect में आपका स्वागत है। कृपया विकल्प चुनें: कीमत जानें=1, मौसम=2, प्रोफाइल=3, फसल सूची=4, ऑर्डर=5, नई फसल=6"', time: "0:05" },
                  { side: 'phone', text: '👆 [1] दबाते हैं', time: "0:15" },
                  { side: 'ai', text: '🤖 "फसल का नाम बोलें। जैसे गेहूं, चावल, मक्का।"', time: "0:17" },
                  { side: 'phone', text: '🗣️ "गेहूं"', time: "0:20" },
                  { side: 'ai', text: '🤖 "गेहूं की आज की कीमत 2042 रुपये प्रति क्विंटल है। अगले 7 दिन में अनुमान 2031 रुपये है। बाज़ार की प्रवृत्ति स्थिर है। कोई और फसल पूछने के लिए 1, वापस मेनू में जाने के लिए 2 दबाएं।"', time: "0:22" },
                  { side: 'phone', text: '👆 [2] दबाते हैं', time: "0:40" },
                  { side: 'ai', text: '🤖 "मेनू पर वापस आ गए। कृपया विकल्प चुनें..."', time: "0:42" },
                  { side: 'phone', text: '👆 [4] दबाते हैं (फसल सूची)', time: "0:45" },
                  { side: 'ai', text: '🤖 "आपके पास 3 फसलें हैं। 1. गेहूं, 100 kg, ₹20/kg। 2. चावल, 50 kg, ₹30/kg। 3. मक्का, 200 kg, ₹15/kg। नई फसल जोड़ें=1, कीमत बदलें=2, बेची गई=3, वापस=4"', time: "0:48" },
                  { side: 'phone', text: '👆 [1] दबाते हैं (नई फसल)', time: "0:55" },
                  { side: 'ai', text: '🤖 "फसल का नाम बोलें।"', time: "0:57" },
                  { side: 'phone', text: '🗣️ "प्याज़"', time: "0:59" },
                  { side: 'ai', text: '🤖 "आप प्याज़ जोड़ रहे हैं। मात्रा बताएं — किलो में संख्या दबाएं।"', time: "1:01" },
                  { side: 'phone', text: '👆 [1][5][0] दबाते हैं (150 kg)', time: "1:04" },
                  { side: 'ai', text: '🤖 "150 किलो प्याज़। अब कीमत बताएं — प्रति किलो रुपये में।"', time: "1:07" },
                  { side: 'phone', text: '👆 [2][5] दबाते हैं (₹25/kg)', time: "1:10" },
                  { side: 'ai', text: '🤖 "बहुत अच्छा! प्याज़ की 150 किलो फसल 25 रुपये प्रति किलो की दर से जोड़ दी गई है। आपकी फसल अब खरीददारों को दिखाई देगी।"', time: "1:13" },
                ].map((msg, i) => (
                  <div key={i} className={`flex ${msg.side === 'phone' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
                      msg.side === 'phone'
                        ? 'bg-harvest-50 text-harvest-800 rounded-br-md border border-harvest-100'
                        : 'bg-leaf-50 text-leaf-800 rounded-bl-md border border-leaf-100'
                    }`}>
                      <p className="text-sm">{msg.text}</p>
                      <p className="text-[10px] text-slate-400 mt-1">{msg.time}</p>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Impact Stats */}
            <div className="grid grid-cols-3 gap-4 mt-8">
              <div className="bg-white rounded-2xl p-4 text-center shadow-card border border-slate-100">
                <div className="text-3xl font-bold text-leaf-600 font-display">0</div>
                <p className="text-sm text-slate-500">स्मार्टफ़ोन चाहिए</p>
                <p className="text-xs text-slate-400">Smartphone needed</p>
              </div>
              <div className="bg-white rounded-2xl p-4 text-center shadow-card border border-slate-100">
                <div className="text-3xl font-bold text-leaf-600 font-display">11+</div>
                <p className="text-sm text-slate-500">भाषाएँ</p>
                <p className="text-xs text-slate-400">Languages</p>
              </div>
              <div className="bg-white rounded-2xl p-4 text-center shadow-card border border-slate-100">
                <div className="text-3xl font-bold text-leaf-600 font-display">24/7</div>
                <p className="text-sm text-slate-500">उपलब्ध</p>
                <p className="text-xs text-slate-400">Available</p>
              </div>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
