import { useState, useRef, useEffect } from 'react'
import { Mic, MicOff, Volume2, X, MessageSquare, Bot, User, Loader2, Wheat } from 'lucide-react'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev'

// Hindi crop name mapping
const CROP_MAP = {
  'गेहूं': 'wheat', 'gehu': 'wheat', 'wheat': 'wheat',
  'चावल': 'rice', 'chawal': 'rice', 'rice': 'rice', 'dhaan': 'rice', 'धान': 'rice',
  'मक्का': 'maize', 'makka': 'maize', 'maize': 'maize', 'corn': 'maize',
  'कपास': 'cotton', 'kapas': 'cotton', 'cotton': 'cotton',
  'सोयाबीन': 'soybean', 'soyabean': 'soybean', 'soybean': 'soybean',
  'आलू': 'potato', 'aloo': 'potato', 'potato': 'potato',
  'टमाटर': 'tomato', 'tamatar': 'tomato', 'tomato': 'tomato',
  'प्याज': 'onion', 'pyaaz': 'onion', 'onion': 'onion',
  'मूंगफली': 'groundnut', 'moongfali': 'groundnut', 'groundnut': 'groundnut',
  'गन्ना': 'sugarcane', 'ganna': 'sugarcane', 'sugarcane': 'sugarcane',
  'मूंग': 'moong', 'moong': 'moong',
  'सरसों': 'mustard', 'sarson': 'mustard', 'mustard': 'mustard',
  'चना': 'chickpea', 'chana': 'chickpea', 'chickpea': 'chickpea',
}

const STATE_MAP = {
  'उत्तर प्रदेश': 'uttar_pradesh', 'uttar pradesh': 'uttar_pradesh', 'up': 'uttar_pradesh',
  'महाराष्ट्र': 'maharashtra', 'maharashtra': 'maharashtra',
  'मध्य प्रदेश': 'madhya_pradesh', 'madhya pradesh': 'madhya_pradesh', 'mp': 'madhya_pradesh',
  'पंजाब': 'punjab', 'punjab': 'punjab',
  'हरियाणा': 'haryana', 'haryana': 'haryana',
  'राजस्थान': 'rajasthan', 'rajasthan': 'rajasthan',
  'कर्नाटक': 'karnataka', 'karnataka': 'karnataka',
  'तमिल नाडु': 'tamil_nadu', 'tamil nadu': 'tamil_nadu', 'tn': 'tamil_nadu',
  'गुजरात': 'gujarat', 'gujarat': 'gujarat',
  'पश्चिम बंगाल': 'west_bengal', 'west bengal': 'west_bengal', 'wb': 'west_bengal',
  'आंध्र प्रदेश': 'andhra_pradesh', 'andhra pradesh': 'andhra_pradesh', 'ap': 'andhra_pradesh',
  'तेलंगाना': 'telangana', 'telangana': 'telangana',
}

function parseVoiceInput(text) {
  const lower = text.toLowerCase()
  
  // Find crop
  let crop = null
  for (const [keyword, value] of Object.entries(CROP_MAP)) {
    if (lower.includes(keyword.toLowerCase())) {
      crop = value
      break
    }
  }
  
  // Find state
  let state = 'uttar_pradesh' // default
  for (const [keyword, value] of Object.entries(STATE_MAP)) {
    if (lower.includes(keyword.toLowerCase())) {
      state = value
      break
    }
  }
  
  return { crop, state }
}

export default function VoiceAgent() {
  const [isOpen, setIsOpen] = useState(false)
  const [isListening, setIsListening] = useState(false)
  const [isSpeaking, setIsSpeaking] = useState(false)
  const [isProcessing, setIsProcessing] = useState(false)
  const [messages, setMessages] = useState([
    { role: 'assistant', text: 'नमस्ते! मैं AgriConnect AI हूँ। बोलिए या टाइप करिए — मैं फसल की कीमत, मौसम, या सिफारिश बता सकता हूँ।\n\nHello! I\'m AgriConnect AI. Ask me about crop prices, weather, or get crop recommendations.', time: new Date() }
  ])
  const [inputText, setInputText] = useState('')
  const [selectedLang, setSelectedLang] = useState('hi-IN')
  const messagesEndRef = useRef(null)
  const recognitionRef = useRef(null)
  const audioRef = useRef(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    // Initialize Web Speech API
    if (typeof window !== 'undefined' && ('SpeechRecognition' in window || 'webkitSpeechRecognition' in window)) {
      const SpeechRecognition = window.SpeechRecognition || window.webkitSpeechRecognition
      recognitionRef.current = new SpeechRecognition()
      recognitionRef.current.continuous = false
      recognitionRef.current.interimResults = false
      recognitionRef.current.lang = selectedLang

      recognitionRef.current.onresult = (event) => {
        const transcript = event.results[0][0].transcript
        setIsListening(false)
        handleUserInput(transcript)
      }

      recognitionRef.current.onerror = (event) => {
        console.error('Speech recognition error:', event.error)
        setIsListening(false)
        if (event.error !== 'no-speech') {
          toast.error('Voice recognition failed. Try typing instead.')
        }
      }

      recognitionRef.current.onend = () => {
        setIsListening(false)
      }
    }

    return () => {
      if (recognitionRef.current) {
        try { recognitionRef.current.abort() } catch {}
      }
      if (audioRef.current) {
        audioRef.current.pause()
      }
    }
  }, [selectedLang])

  const startListening = () => {
    if (!recognitionRef.current) {
      toast.error('Voice recognition not supported in this browser')
      return
    }
    recognitionRef.current.lang = selectedLang
    try {
      recognitionRef.current.start()
      setIsListening(true)
    } catch (err) {
      console.error('Failed to start recognition:', err)
    }
  }

  const stopListening = () => {
    if (recognitionRef.current) {
      recognitionRef.current.stop()
    }
    setIsListening(false)
  }

  const speakText = async (text) => {
    try {
      setIsSpeaking(true)
      const res = await fetch(`${API_BASE}/api/sarvam/tts`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          text: text.substring(0, 500), // limit for TTS
          language: selectedLang.replace('-IN', ''),
          voice: 'priya'
        })
      })

      if (res.ok) {
        const blob = await res.blob()
        const url = URL.createObjectURL(blob)
        if (audioRef.current) {
          audioRef.current.pause()
        }
        audioRef.current = new Audio(url)
        audioRef.current.onended = () => setIsSpeaking(false)
        audioRef.current.onerror = () => setIsSpeaking(false)
        await audioRef.current.play()
      } else {
        // Fallback to browser TTS
        const utterance = new SpeechSynthesisUtterance(text.substring(0, 300))
        utterance.lang = selectedLang
        utterance.rate = 0.9
        utterance.onend = () => setIsSpeaking(false)
        speechSynthesis.speak(utterance)
      }
    } catch (err) {
      console.error('TTS error:', err)
      // Fallback to browser TTS
      try {
        const utterance = new SpeechSynthesisUtterance(text.substring(0, 300))
        utterance.lang = selectedLang
        utterance.rate = 0.9
        utterance.onend = () => setIsSpeaking(false)
        speechSynthesis.speak(utterance)
      } catch {
        setIsSpeaking(false)
      }
    }
  }

  const handleUserInput = async (text) => {
    if (!text.trim()) return

    const userMsg = { role: 'user', text: text.trim(), time: new Date() }
    setMessages(prev => [...prev, userMsg])
    setInputText('')
    setIsProcessing(true)

    try {
      const lower = text.toLowerCase()
      
      // Detect intent
      if (lower.includes('price') || lower.includes('कीमत') || lower.includes('daam') || lower.includes('दाम') || lower.includes('rate') || lower.includes('भाव')) {
        // Price query
        const { crop, state } = parseVoiceInput(text)
        if (crop) {
          const res = await fetch(`${API_BASE}/api/predict/${crop}/${state}`)
          const data = await res.json()
          
          const trendEmoji = data.trend === 'bullish' ? '📈' : data.trend === 'bearish' ? '📉' : '➡️'
          const responseText = `${crop} की कीमत ${data.current_price} रुपये प्रति क्विंटल है।\n7 दिन में: ${data.predicted_price_7d} रुपये\n15 दिन में: ${data.predicted_price_15d} रुपये\n30 दिन में: ${data.predicted_price_30d} रुपये\n\nप्रवृत्ति: ${data.trend} ${trendEmoji}\nविश्वास स्तर: ${Math.round(data.confidence * 100)}%`
          
          const assistantMsg = { role: 'assistant', text: responseText, time: new Date(), data }
          setMessages(prev => [...prev, assistantMsg])
          speakText(responseText.replace(/\n/g, '. '))
        } else {
          const responseText = 'कृपया फसल का नाम बताएं। जैसे: गेहूं, चावल, मक्का, आलू, टमाटर।\n\nPlease name the crop: wheat, rice, maize, potato, tomato.'
          setMessages(prev => [...prev, { role: 'assistant', text: responseText, time: new Date() }])
          speakText('कृपया फसल का नाम बताएं')
        }
      } else if (lower.includes('weather') || lower.includes('मौसम') || lower.includes('barish') || lower.includes('बारिश') || lower.includes('rain')) {
        // Weather query
        const { state } = parseVoiceInput(text)
        const res = await fetch(`${API_BASE}/api/weather/v2?state=${state}&days=3`)
        const data = await res.json()
        
        const responseText = `${state.replace(/_/g, ' ')} में आज ${data.current.temp}°C तापमान है और ${data.current.humidity}% नमी है।\nअगले 3 दिन: ${data.forecast.map(f => f.temp_max + '°C').join(', ')}।\n\n${data.farming_recommendations?.[0] || 'मौसम सामान्य है।'}`
        
        setMessages(prev => [...prev, { role: 'assistant', text: responseText, time: new Date() }])
        speakText(responseText.replace(/\n/g, '. '))
      } else if (lower.includes('recommend') || lower.includes('सिफारिश') || lower.includes('क्या उगाएं') || lower.includes('suggest') || lower.includes('best crop')) {
        // Crop recommendation
        const responseText = 'फसल सिफारिश के लिए मुझे बताइए:\n1. मिट्टी का प्रकार (चिकनी/दोमट/reti)\n2. pH (5.5-8.0)\n3. तापमान (°C)\n4. बारिश (mm)\n\nOr use the Crop Recommendation tool on the dashboard.'
        setMessages(prev => [...prev, { role: 'assistant', text: responseText, time: new Date() }])
        speakText('फसल सिफारिश के लिए मिट्टी की जानकारी चाहिए')
      } else if (lower.includes('hello') || lower.includes('नमस्ते') || lower.includes('hi') || lower.includes('hey')) {
        const responseText = 'नमस्ते! आप AgriConnect AI से बात कर रहे हैं। आप मुझसे पूछ सकते हैं:\n\n1. "गेहूं की कीमत बताओ" — Crop price\n2. "मौसम कैसा है" — Weather update\n3. "क्या उगाएं" — Crop recommendation'
        setMessages(prev => [...prev, { role: 'assistant', text: responseText, time: new Date() }])
        speakText('नमस्ते! मैं AgriConnect AI हूँ। आप फसल की कीमत, मौसम, या सिफारिश पूछ सकते हैं।')
      } else {
        // General — try to parse as crop query
        const { crop, state } = parseVoiceInput(text)
        if (crop) {
          const res = await fetch(`${API_BASE}/api/predict/${crop}/${state}`)
          const data = await res.json()
          const responseText = `${crop} (${state.replace(/_/g, ' ')}) की आज की कीमत ₹${data.current_price} प्रति क्विंटल है। 7 दिन में ₹${data.predicted_price_7d} की उम्मीद है।`
          setMessages(prev => [...prev, { role: 'assistant', text: responseText, time: new Date() }])
          speakText(responseText)
        } else {
          const responseText = 'मुझे समझ नहीं आया। आप कह सकते हैं:\n\n• "गेहूं की कीमत" — Price check\n• "मौसम बताओ" — Weather\n• "नमस्ते" — Greeting'
          setMessages(prev => [...prev, { role: 'assistant', text: responseText, time: new Date() }])
        }
      }
    } catch (err) {
      console.error('Agent error:', err)
      const errorText = 'कुछ गड़बड़ हुई। कृपया दोबारा कोशिश करें।\n\nSomething went wrong. Please try again.'
      setMessages(prev => [...prev, { role: 'assistant', text: errorText, time: new Date() }])
    } finally {
      setIsProcessing(false)
    }
  }

  const handleSubmit = (e) => {
    e.preventDefault()
    if (inputText.trim() && !isProcessing) {
      handleUserInput(inputText)
    }
  }

  const quickActions = [
    { label: '🌾 गेहूं कीमत', text: 'गेहूं की कीमत बताओ' },
    { label: '🍚 चावल कीमत', text: 'चावल की कीमत बताओ' },
    { label: '☁️ मौसम', text: 'मौसम कैसा है' },
    { label: '🏡 सिफारिश', text: 'क्या उगाएं' },
  ]

  if (!isOpen) {
    return (
      <button
        onClick={() => setIsOpen(true)}
        className="fixed bottom-6 right-6 z-50 w-16 h-16 bg-gradient-to-br from-emerald-500 to-green-600 text-white rounded-full shadow-2xl hover:shadow-3xl hover:scale-110 transition-all duration-300 flex items-center justify-center group"
        aria-label="Open Voice Agent"
      >
        <Bot className="w-7 h-7 group-hover:scale-110 transition-transform" />
        <span className="absolute -top-1 -right-1 w-4 h-4 bg-red-500 rounded-full animate-pulse" />
      </button>
    )
  }

  return (
    <div className="fixed bottom-6 right-6 z-50 w-[400px] max-w-[calc(100vw-2rem)] h-[600px] max-h-[calc(100vh-3rem)] bg-white rounded-3xl shadow-2xl border border-slate-200 flex flex-col overflow-hidden animate-slide-up">
      {/* Header */}
      <div className="bg-gradient-to-r from-emerald-600 to-green-600 text-white p-4 flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-white/20 rounded-xl flex items-center justify-center">
            <Wheat className="w-6 h-6" />
          </div>
          <div>
            <h3 className="font-bold text-sm">AgriConnect AI</h3>
            <p className="text-xs text-emerald-100">Voice Assistant • कृषि सहायक</p>
          </div>
        </div>
        <div className="flex items-center gap-2">
          <select
            value={selectedLang}
            onChange={(e) => setSelectedLang(e.target.value)}
            className="text-xs bg-white/20 text-white border border-white/30 rounded-lg px-2 py-1 focus:outline-none"
          >
            <option value="hi-IN">हिंदी</option>
            <option value="en-IN">English</option>
            <option value="ta-IN">தமிழ்</option>
            <option value="te-IN">తెలుగు</option>
            <option value="kn-IN">ಕನ್ನಡ</option>
            <option value="mr-IN">मराठी</option>
          </select>
          <button
            onClick={() => setIsOpen(false)}
            className="w-8 h-8 bg-white/20 hover:bg-white/30 rounded-lg flex items-center justify-center transition-colors"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3 bg-slate-50">
        {messages.map((msg, i) => (
          <div key={i} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
            <div className={`max-w-[85%] rounded-2xl px-4 py-3 ${
              msg.role === 'user'
                ? 'bg-emerald-600 text-white rounded-br-md'
                : 'bg-white text-slate-800 shadow-sm border border-slate-100 rounded-bl-md'
            }`}>
              <div className="flex items-start gap-2">
                {msg.role === 'assistant' && (
                  <Bot className="w-4 h-4 text-emerald-500 mt-0.5 shrink-0" />
                )}
                {msg.role === 'user' && (
                  <User className="w-4 h-4 text-emerald-100 mt-0.5 shrink-0" />
                )}
                <div>
                  <p className="text-sm whitespace-pre-line leading-relaxed">{msg.text}</p>
                  {msg.data && (
                    <div className="mt-2 p-2 bg-emerald-50 rounded-lg text-xs text-emerald-700">
                      <span className="font-semibold">7d: ₹{msg.data.predicted_price_7d}</span> • 
                      <span className="font-semibold"> 30d: ₹{msg.data.predicted_price_30d}</span> • 
                      <span className="capitalize"> {msg.data.trend}</span>
                    </div>
                  )}
                  <p className={`text-[10px] mt-1 ${msg.role === 'user' ? 'text-emerald-200' : 'text-slate-400'}`}>
                    {msg.time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' })}
                  </p>
                </div>
              </div>
            </div>
          </div>
        ))}
        
        {isProcessing && (
          <div className="flex justify-start">
            <div className="bg-white text-slate-800 shadow-sm border border-slate-100 rounded-2xl rounded-bl-md px-4 py-3">
              <div className="flex items-center gap-2">
                <Bot className="w-4 h-4 text-emerald-500" />
                <div className="flex gap-1">
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }} />
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }} />
                  <span className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }} />
                </div>
              </div>
            </div>
          </div>
        )}
        
        <div ref={messagesEndRef} />
      </div>

      {/* Quick Actions */}
      <div className="px-4 py-2 bg-white border-t border-slate-100 shrink-0">
        <div className="flex gap-2 overflow-x-auto pb-1 scrollbar-none">
          {quickActions.map((action) => (
            <button
              key={action.label}
              onClick={() => handleUserInput(action.text)}
              disabled={isProcessing}
              className="shrink-0 px-3 py-1.5 bg-emerald-50 text-emerald-700 text-xs font-semibold rounded-full hover:bg-emerald-100 transition-colors disabled:opacity-50"
            >
              {action.label}
            </button>
          ))}
        </div>
      </div>

      {/* Input */}
      <div className="p-4 bg-white border-t border-slate-100 shrink-0">
        <form onSubmit={handleSubmit} className="flex items-center gap-2">
          <button
            type="button"
            onClick={isListening ? stopListening : startListening}
            disabled={isProcessing}
            className={`w-11 h-11 rounded-xl flex items-center justify-center shrink-0 transition-all ${
              isListening
                ? 'bg-red-500 text-white animate-pulse shadow-lg'
                : 'bg-emerald-100 text-emerald-600 hover:bg-emerald-200'
            } disabled:opacity-50`}
          >
            {isListening ? <MicOff className="w-5 h-5" /> : <Mic className="w-5 h-5" />}
          </button>
          
          <input
            type="text"
            value={inputText}
            onChange={(e) => setInputText(e.target.value)}
            placeholder={isListening ? 'सुन रहा हूँ...' : 'Type or speak...'}
            disabled={isProcessing}
            className="flex-1 px-4 py-2.5 bg-slate-100 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-emerald-500 disabled:opacity-50"
          />

          <button
            type="submit"
            disabled={!inputText.trim() || isProcessing}
            className="w-11 h-11 bg-emerald-600 text-white rounded-xl flex items-center justify-center shrink-0 hover:bg-emerald-700 disabled:opacity-50 transition-colors"
          >
            {isProcessing ? <Loader2 className="w-5 h-5 animate-spin" /> : <MessageSquare className="w-5 h-5" />}
          </button>
        </form>
        
        {isSpeaking && (
          <div className="flex items-center gap-2 mt-2 px-1">
            <Volume2 className="w-3 h-3 text-emerald-500 animate-pulse" />
            <span className="text-[10px] text-emerald-600 font-medium">Speaking...</span>
            <button
              onClick={() => { speechSynthesis.cancel(); audioRef.current?.pause(); setIsSpeaking(false) }}
              className="text-[10px] text-red-500 font-medium hover:underline"
            >
              Stop
            </button>
          </div>
        )}
      </div>
    </div>
  )
}
