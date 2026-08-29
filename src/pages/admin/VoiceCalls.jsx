import { useState, useEffect } from 'react'
import { Phone, PhoneCall, PhoneOff, PhoneForwarded, Clock, CheckCircle, XCircle, AlertTriangle, Loader2, Mic, Volume2, FileText, BarChart3 } from 'lucide-react'
import { Card, Badge, Button, StatCard } from '../../components/ui'
import { toast } from 'react-hot-toast'

const API_BASE = import.meta.env.VITE_API_BASE_URL || 'https://pee54yt4m2.execute-api.ap-south-1.amazonaws.com/dev'

const LANGUAGES = [
  { value: 'Hindi', label: 'हिन्दी (Hindi)' },
  { value: 'English', label: 'English' },
  { value: 'Tamil', label: 'தமிழ் (Tamil)' },
  { value: 'Telugu', label: 'తెలుగు (Telugu)' },
  { value: 'Kannada', label: 'ಕನ್ನಡ (Kannada)' },
  { value: 'Marathi', label: 'मराठी (Marathi)' },
  { value: 'Punjabi', label: 'ਪੰਜਾਬੀ (Punjabi)' },
  { value: 'Bengali', label: 'বাংলা (Bengali)' },
  { value: 'Gujarati', label: 'ગુજરાતી (Gujarati)' },
  { value: 'Malayalam', label: 'മലയാളം (Malayalam)' },
]

const STATUS_CONFIG = {
  initiated: { color: 'info', icon: Loader2, label: 'Connecting...', animate: true },
  connected: { color: 'success', icon: CheckCircle, label: 'Connected' },
  no_answer: { color: 'warning', icon: PhoneOff, label: 'No Answer' },
  busy: { color: 'warning', icon: AlertTriangle, label: 'Busy' },
  failed: { color: 'danger', icon: XCircle, label: 'Failed' },
}

export default function VoiceCalls() {
  // Call form
  const [phone, setPhone] = useState('')
  const [farmerName, setFarmerName] = useState('')
  const [state, setState] = useState('')
  const [cropName, setCropName] = useState('')
  const [language, setLanguage] = useState('Hindi')
  const [calling, setCalling] = useState(false)

  // Call history
  const [calls, setCalls] = useState([])
  const [stats, setStats] = useState(null)
  const [loading, setLoading] = useState(true)
  const [selectedCall, setSelectedCall] = useState(null)
  const [filter, setFilter] = useState('all')

  // Fetch call history + stats
  useEffect(() => {
    const fetchData = async () => {
      try {
        const [callsRes, statsRes] = await Promise.all([
          fetch(`${API_BASE}/api/voice-agents/calls?limit=100`),
          fetch(`${API_BASE}/api/voice-agents/stats`),
        ])
        if (callsRes.ok) {
          const data = await callsRes.json()
          setCalls(data.calls || [])
        }
        if (statsRes.ok) {
          setStats(await statsRes.json())
        }
      } catch (err) {
        console.error('Failed to fetch call data:', err)
      } finally {
        setLoading(false)
      }
    }
    fetchData()
    // Poll for updates every 10 seconds
    const interval = setInterval(fetchData, 10000)
    return () => clearInterval(interval)
  }, [])

  // Trigger outbound call
  const handleCall = async () => {
    if (!phone) {
      toast.error('Please enter a phone number')
      return
    }

    // Validate Indian phone format
    const cleanPhone = phone.replace(/\s/g, '')
    if (!cleanPhone.startsWith('+91') && !cleanPhone.startsWith('91')) {
      toast.error('Enter a valid Indian phone number (e.g. +919876543210)')
      return
    }

    const formattedPhone = cleanPhone.startsWith('+') ? cleanPhone : `+${cleanPhone}`

    try {
      setCalling(true)
      const res = await fetch(`${API_BASE}/api/voice-agents/call`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmer_phone: formattedPhone,
          farmer_name: farmerName || undefined,
          state: state || undefined,
          crop_name: cropName || undefined,
          language,
        }),
      })

      const data = await res.json()

      if (res.ok) {
        toast.success(`Call initiated! Attempt ID: ${data.attempt_id?.slice(0, 8)}...`)
        setPhone('')
        setFarmerName('')
        setCropName('')
        // Refresh call list
        const callsRes = await fetch(`${API_BASE}/api/voice-agents/calls?limit=100`)
        if (callsRes.ok) {
          const callsData = await callsRes.json()
          setCalls(callsData.calls || [])
        }
      } else {
        toast.error(data.detail || 'Failed to initiate call')
      }
    } catch (err) {
      toast.error('Could not connect to Voice Agent service')
      console.error(err)
    } finally {
      setCalling(false)
    }
  }

  const filteredCalls = filter === 'all' ? calls : calls.filter(c => c.status === filter)

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="animate-fade-in-up">
        <h1 className="font-display text-2xl sm:text-3xl font-bold text-slate-800">Voice Agent Calls</h1>
        <p className="text-slate-500 mt-1">Call farmers directly using Sarvam AI Voice Agents — no smartphone needed</p>
      </div>

      {/* Stats */}
      {stats && (
        <div className="grid grid-cols-2 lg:grid-cols-5 gap-4">
          <StatCard icon={<Phone className="w-5 h-5" />} label="Total Calls" value={stats.total} delay={1} />
          <StatCard icon={<PhoneCall className="w-5 h-5" />} label="Connected" value={stats.connected} color="bg-leaf-50" delay={2} />
          <StatCard icon={<PhoneOff className="w-5 h-5" />} label="No Answer" value={stats.no_answer} delay={3} />
          <StatCard icon={<XCircle className="w-5 h-5" />} label="Failed" value={stats.failed} delay={4} />
          <StatCard icon={<Clock className="w-5 h-5" />} label="Avg Duration" value={`${stats.avg_duration_seconds}s`} delay={5} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        {/* Call Form */}
        <div className="lg:col-span-1">
          <Card className="p-6 animate-fade-in-up delay-2">
            <div className="flex items-center gap-2 mb-5">
              <div className="w-10 h-10 rounded-xl bg-leaf-100 flex items-center justify-center">
                <PhoneForwarded className="w-5 h-5 text-leaf-600" />
              </div>
              <div>
                <h2 className="font-display text-lg font-bold text-slate-800">Make a Call</h2>
                <p className="text-xs text-slate-500">AI agent calls the farmer</p>
              </div>
            </div>

            <div className="space-y-4">
              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Farmer Phone *</label>
                <div className="relative">
                  <Phone className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-400" />
                  <input
                    type="tel"
                    value={phone}
                    onChange={e => setPhone(e.target.value)}
                    placeholder="+919876543210"
                    className="w-full pl-10 pr-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500"
                  />
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Farmer Name</label>
                <input
                  type="text"
                  value={farmerName}
                  onChange={e => setFarmerName(e.target.value)}
                  placeholder="e.g. Ram Singh"
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">State</label>
                  <select
                    value={state}
                    onChange={e => setState(e.target.value)}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-leaf-500"
                  >
                    <option value="">Auto-detect</option>
                    <option value="uttar_pradesh">Uttar Pradesh</option>
                    <option value="maharashtra">Maharashtra</option>
                    <option value="punjab">Punjab</option>
                    <option value="haryana">Haryana</option>
                    <option value="madhya_pradesh">Madhya Pradesh</option>
                    <option value="rajasthan">Rajasthan</option>
                    <option value="karnataka">Karnataka</option>
                    <option value="tamil_nadu">Tamil Nadu</option>
                    <option value="andhra_pradesh">Andhra Pradesh</option>
                    <option value="gujarat">Gujarat</option>
                    <option value="west_bengal">West Bengal</option>
                    <option value="bihar">Bihar</option>
                  </select>
                </div>

                <div>
                  <label className="block text-sm font-semibold text-slate-700 mb-1.5">Language</label>
                  <select
                    value={language}
                    onChange={e => setLanguage(e.target.value)}
                    className="w-full px-3 py-2.5 border border-slate-200 rounded-xl text-sm bg-white focus:outline-none focus:ring-2 focus:ring-leaf-500"
                  >
                    {LANGUAGES.map(l => (
                      <option key={l.value} value={l.value}>{l.label}</option>
                    ))}
                  </select>
                </div>
              </div>

              <div>
                <label className="block text-sm font-semibold text-slate-700 mb-1.5">Crop (optional)</label>
                <input
                  type="text"
                  value={cropName}
                  onChange={e => setCropName(e.target.value)}
                  placeholder="e.g. wheat, rice"
                  className="w-full px-4 py-2.5 border border-slate-200 rounded-xl text-sm focus:outline-none focus:ring-2 focus:ring-leaf-500"
                />
              </div>

              <Button
                variant="leaf"
                size="lg"
                className="w-full"
                onClick={handleCall}
                disabled={calling || !phone}
              >
                {calling ? (
                  <><Loader2 className="w-5 h-5 animate-spin" /> Connecting...</>
                ) : (
                  <><PhoneForwarded className="w-5 h-5" /> Call Farmer</>
                )}
              </Button>

              <p className="text-xs text-slate-400 text-center">
                The AI agent will call and speak in {language}. Farmer can respond by voice.
              </p>
            </div>
          </Card>

          {/* How it works */}
          <Card className="p-5 mt-4 animate-fade-in-up delay-3">
            <h3 className="font-display text-sm font-bold text-slate-800 mb-3">How It Works</h3>
            <div className="space-y-3">
              {[
                { step: 1, icon: PhoneForwarded, text: 'You enter the farmer\'s number and click Call' },
                { step: 2, icon: Volume2, text: 'Sarvam AI agent calls the farmer in Hindi' },
                { step: 3, icon: Mic, text: 'Farmer speaks naturally — agent understands Hindi/English' },
                { step: 4, icon: BarChart3, text: 'Agent shares crop prices, weather, order updates' },
                { step: 5, icon: FileText, text: 'Transcript and data saved automatically' },
              ].map(({ step, icon: Icon, text }) => (
                <div key={step} className="flex items-start gap-3">
                  <div className="w-7 h-7 rounded-full bg-leaf-100 flex items-center justify-center shrink-0 mt-0.5">
                    <span className="text-xs font-bold text-leaf-700">{step}</span>
                  </div>
                  <div className="flex items-start gap-2">
                    <Icon className="w-4 h-4 text-slate-400 mt-0.5 shrink-0" />
                    <p className="text-sm text-slate-600">{text}</p>
                  </div>
                </div>
              ))}
            </div>
          </Card>
        </div>

        {/* Call History */}
        <div className="lg:col-span-2">
          <Card className="animate-fade-in-up delay-2">
            <div className="p-5 border-b border-slate-100">
              <div className="flex items-center justify-between">
                <h2 className="font-display text-lg font-bold text-slate-800">Call History</h2>
                <div className="flex gap-2">
                  {['all', 'connected', 'no_answer', 'failed'].map(f => (
                    <button
                      key={f}
                      onClick={() => setFilter(f)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
                        filter === f
                          ? 'bg-leaf-600 text-white'
                          : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                      }`}
                    >
                      {f === 'all' ? 'All' : f === 'no_answer' ? 'No Answer' : f.charAt(0).toUpperCase() + f.slice(1)}
                      {f !== 'all' && (
                        <span className="ml-1">({calls.filter(c => f === 'all' || c.status === f).length})</span>
                      )}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {loading ? (
              <div className="flex justify-center py-16">
                <Loader2 className="w-8 h-8 text-leaf-600 animate-spin" />
              </div>
            ) : filteredCalls.length > 0 ? (
              <div className="divide-y divide-slate-50 max-h-[600px] overflow-y-auto">
                {filteredCalls.map((call) => {
                  const config = STATUS_CONFIG[call.status] || STATUS_CONFIG.initiated
                  const StatusIcon = config.icon
                  return (
                    <div
                      key={call.attempt_id}
                      className="p-4 hover:bg-slate-50/50 transition-colors cursor-pointer"
                      onClick={() => setSelectedCall(selectedCall?.attempt_id === call.attempt_id ? null : call)}
                    >
                      <div className="flex items-center justify-between">
                        <div className="flex items-center gap-3">
                          <div className={`w-10 h-10 rounded-xl flex items-center justify-center ${
                            call.status === 'connected' ? 'bg-leaf-50' :
                            call.status === 'failed' ? 'bg-red-50' : 'bg-slate-100'
                          }`}>
                            <StatusIcon className={`w-5 h-5 ${
                              config.animate ? 'animate-spin' : ''
                            } ${
                              call.status === 'connected' ? 'text-leaf-600' :
                              call.status === 'failed' ? 'text-red-500' : 'text-slate-500'
                            }`} />
                          </div>
                          <div>
                            <p className="font-semibold text-slate-800 text-sm">{call.farmer_phone}</p>
                            <p className="text-xs text-slate-400">
                              {call.farmer_name && `${call.farmer_name} · `}
                              {new Date(call.created_at).toLocaleString('en-IN', { dateStyle: 'medium', timeStyle: 'short' })}
                            </p>
                          </div>
                        </div>
                        <div className="text-right">
                          <Badge variant={config.color}>{config.label}</Badge>
                          {call.duration && (
                            <p className="text-xs text-slate-400 mt-1">{Math.round(call.duration)}s</p>
                          )}
                        </div>
                      </div>

                      {/* Expanded transcript */}
                      {selectedCall?.attempt_id === call.attempt_id && call.transcript && (
                        <div className="mt-4 p-4 bg-slate-50 rounded-xl space-y-2 animate-fade-in">
                          <p className="text-xs font-bold text-slate-500 uppercase tracking-wider mb-2">Transcript</p>
                          {call.transcript.map((turn, i) => (
                            <div key={i} className={`flex ${turn.role === 'agent' ? 'justify-start' : 'justify-end'}`}>
                              <div className={`max-w-[80%] px-3 py-2 rounded-xl text-sm ${
                                turn.role === 'agent'
                                  ? 'bg-leaf-100 text-leaf-800 rounded-bl-none'
                                  : 'bg-sky-100 text-sky-800 rounded-br-none'
                              }`}>
                                <p className="text-[10px] font-bold mb-0.5 opacity-60">
                                  {turn.role === 'agent' ? '🤖 Agent' : '👨‍🌾 Farmer'}
                                </p>
                                {turn.en_text}
                              </div>
                            </div>
                          ))}
                        </div>
                      )}

                      {selectedCall?.attempt_id === call.attempt_id && call.failure_reason && (
                        <div className="mt-3 p-3 bg-red-50 rounded-xl text-sm text-red-700">
                          <p className="font-semibold">Failure reason:</p>
                          <p>{call.failure_reason}</p>
                        </div>
                      )}

                      {selectedCall?.attempt_id === call.attempt_id && call.agent_variables && (
                        <div className="mt-3 p-3 bg-amber-50 rounded-xl text-sm">
                          <p className="font-semibold text-amber-800 mb-1">Extracted Data:</p>
                          <pre className="text-xs text-amber-700 overflow-x-auto">
                            {JSON.stringify(call.agent_variables, null, 2)}
                          </pre>
                        </div>
                      )}
                    </div>
                  )
                })}
              </div>
            ) : (
              <div className="p-12 text-center text-slate-400">
                <Phone className="w-12 h-12 mx-auto mb-3 text-slate-300" />
                <p className="font-semibold">No calls yet</p>
                <p className="text-sm mt-1">Make your first call to a farmer using the form</p>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  )
}
