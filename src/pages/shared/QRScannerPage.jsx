import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Html5QrcodeScanner } from 'html5-qrcode'
import { X, Camera, ShieldCheck, ChevronLeft } from 'lucide-react'
import { toast } from 'react-hot-toast'

export default function QRScannerPage() {
  const navigate = useNavigate()
  const [isScanning, setIsScanning] = useState(true)

  useEffect(() => {
    const scanner = new Html5QrcodeScanner('reader', {
      qrbox: {
        width: 250,
        height: 250,
      },
      fps: 10,
    })

    scanner.render(onScanSuccess, onScanError)

    function onScanSuccess(result) {
      scanner.clear()
      setIsScanning(false)
      
      // Try to parse the URL
      try {
        const urlString = result.startsWith('http') ? result : `${window.location.origin}${result}`
        const url = new URL(urlString)
        const path = url.pathname
        
        // Check if it's our product link
        if (path.includes('/consumer/products/')) {
          toast.success('Crop identified! Opening profile...')
          navigate(path)
        } else {
          toast.error('Unrecognized QR Code format')
        }
      } catch (e) {
        toast.error('Invalid QR Code data')
      }
    }

    function onScanError(err) {
      // quiet error
    }

    return () => {
      scanner.clear().catch(e => console.error('Scanner cleanup error:', e))
    }
  }, [navigate])

  return (
    <div className="fixed inset-0 bg-slate-900 z-50 flex flex-col text-white overflow-hidden">
      {/* Header */}
      <div className="p-4 flex items-center justify-between border-b border-white/10 backdrop-blur-md bg-slate-900/50">
        <button 
          onClick={() => navigate(-1)}
          className="w-10 h-10 rounded-full bg-white/10 flex items-center justify-center hover:bg-white/20 transition-colors"
        >
          <ChevronLeft className="w-6 h-6" />
        </button>
        <h1 className="font-display font-bold text-lg text-white">Smart Crop Scanner</h1>
        <div className="w-10 h-10" /> {/* Spacer */}
      </div>

      {/* Scanner Visualizer */}
      <div className="flex-1 relative flex flex-col items-center justify-center p-6">
        <div className="relative w-full max-w-sm aspect-square bg-black shadow-2xl rounded-3xl overflow-hidden border border-white/10">
          {/* Decorative Corners */}
          <div className="absolute top-6 left-6 w-8 h-8 border-t-4 border-l-4 border-sky-500 rounded-tl-lg z-30" />
          <div className="absolute top-6 right-6 w-8 h-8 border-t-4 border-r-4 border-sky-500 rounded-tr-lg z-30" />
          <div className="absolute bottom-6 left-6 w-8 h-8 border-b-4 border-l-4 border-sky-500 rounded-bl-lg z-30" />
          <div className="absolute bottom-6 right-6 w-8 h-8 border-b-4 border-r-4 border-sky-500 rounded-br-lg z-30" />
          
          {/* Scanning Animation */}
          <div className="absolute inset-0 bg-sky-500/5 animate-pulse z-10 pointer-events-none" />
          <div className="absolute top-0 left-0 right-0 h-1 bg-gradient-to-r from-transparent via-sky-400 to-transparent shadow-[0_0_15px_rgba(56,189,248,0.8)] animate-scanner-line z-40 pointer-events-none" />

          {/* Core Scanner Element */}
          <div id="reader" className="w-full h-full scale-110"></div>
        </div>

        <div className="mt-8 text-center max-w-xs animate-fade-in px-4">
          <div className="inline-flex items-center gap-2 px-3 py-1 bg-leaf-500/20 text-leaf-400 rounded-full text-xs font-semibold mb-3">
            <ShieldCheck className="w-3.5 h-3.5" /> Secure Traceability
          </div>
          <p className="text-slate-300 text-sm leading-relaxed">
            Position the crop's QR code within the frame above to instantly view its origin, quality, and price history.
          </p>
        </div>
      </div>

      {/* Footer / Status */}
      <div className="p-8 bg-gradient-to-t from-black/80 to-transparent flex flex-col items-center">
        <div className="flex items-center gap-3 text-white/40 text-sm mb-6">
          <Camera className="w-4 h-4" />
          <span>Camera Access Active</span>
        </div>
        <button 
          onClick={() => navigate(-1)}
          className="w-full max-w-xs py-4 bg-white text-slate-900 rounded-2xl font-bold shadow-xl active:scale-95 transition-all"
        >
          Cancel Scan
        </button>
      </div>

      <style dangerouslySetInnerHTML={{ __html: `
        @keyframes scanner-line {
          0% { top: 10% }
          50% { top: 90% }
          100% { top: 10% }
        }
        .animate-scanner-line {
          animation: scanner-line 3s ease-in-out infinite;
        }
        #reader {
          border: none !important;
        }
        #reader video {
          object-fit: cover !important;
          width: 100% !important;
          height: 100% !important;
        }
        #reader__dashboard_section_csr button {
          background: #38bdf8 !important;
          color: white !important;
          border: none !important;
          padding: 12px 24px !important;
          border-radius: 12px !important;
          font-weight: 700 !important;
          margin-top: 10px !important;
          text-transform: uppercase !important;
          letter-spacing: 0.05em !important;
        }
        #reader img {
          display: none !important;
        }
      `}} />
    </div>
  )
}
