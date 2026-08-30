import { Component } from 'react'
import { Sprout, RefreshCw } from 'lucide-react'

export default class ErrorBoundary extends Component {
  constructor(props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error) {
    return { hasError: true, error }
  }

  componentDidCatch(error, errorInfo) {
    console.error('ErrorBoundary caught:', error, errorInfo)
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="min-h-screen flex items-center justify-center bg-earth-50 px-4">
          <div className="text-center max-w-md animate-fade-in">
            <div className="w-16 h-16 bg-gradient-to-br from-harvest-500 to-harvest-700 rounded-2xl flex items-center justify-center mx-auto mb-4 shadow-lg">
              <Sprout className="w-9 h-9 text-white" />
            </div>
            <h1 className="font-display text-2xl font-bold text-slate-800 mb-2">
              Something went wrong
            </h1>
            <p className="text-slate-500 text-sm mb-6">
              The app hit an unexpected error. This is usually a temporary network issue.
            </p>
            <button
              onClick={() => {
                this.setState({ hasError: false, error: null })
                window.location.reload()
              }}
              className="inline-flex items-center gap-2 px-5 py-2.5 bg-leaf-600 text-white rounded-xl text-sm font-bold hover:bg-leaf-700 transition-colors"
            >
              <RefreshCw className="w-4 h-4" /> Try Again
            </button>
          </div>
        </div>
      )
    }

    return this.props.children
  }
}
