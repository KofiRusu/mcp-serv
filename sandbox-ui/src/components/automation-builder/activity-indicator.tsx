'use client'

import { useState, useEffect, createContext, useContext, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { cn } from '@/lib/utils'
import {
  CheckCircle2,
  XCircle,
  AlertCircle,
  Info,
  Loader2,
  Sparkles,
  X,
  PartyPopper,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'

// Types
interface Toast {
  id: string
  type: 'success' | 'error' | 'warning' | 'info' | 'loading'
  title: string
  description?: string
  duration?: number
  action?: {
    label: string
    onClick: () => void
  }
}

interface ActivityContextType {
  showToast: (toast: Omit<Toast, 'id'>) => string
  hideToast: (id: string) => void
  updateToast: (id: string, updates: Partial<Toast>) => void
  showProgress: (id: string, title: string, progress: number) => void
  hideProgress: (id: string) => void
  showConfetti: () => void
  showShake: (elementId: string) => void
}

const ActivityContext = createContext<ActivityContextType | null>(null)

// Provider component
export function ActivityProvider({ children }: { children: React.ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])
  const [progressBars, setProgressBars] = useState<Map<string, { title: string; progress: number }>>(new Map())
  const [showingConfetti, setShowingConfetti] = useState(false)

  const showToast = useCallback((toast: Omit<Toast, 'id'>) => {
    const id = `toast-${Date.now()}`
    setToasts(prev => [...prev, { ...toast, id }])

    // Auto-remove after duration (except for loading)
    if (toast.type !== 'loading' && toast.duration !== Infinity) {
      setTimeout(() => {
        hideToast(id)
      }, toast.duration || 4000)
    }

    return id
  }, [])

  const hideToast = useCallback((id: string) => {
    setToasts(prev => prev.filter(t => t.id !== id))
  }, [])

  const updateToast = useCallback((id: string, updates: Partial<Toast>) => {
    setToasts(prev => prev.map(t => t.id === id ? { ...t, ...updates } : t))
  }, [])

  const showProgress = useCallback((id: string, title: string, progress: number) => {
    setProgressBars(prev => new Map(prev).set(id, { title, progress }))
  }, [])

  const hideProgress = useCallback((id: string) => {
    setProgressBars(prev => {
      const next = new Map(prev)
      next.delete(id)
      return next
    })
  }, [])

  const showConfetti = useCallback(() => {
    setShowingConfetti(true)
    setTimeout(() => setShowingConfetti(false), 3000)
  }, [])

  const showShake = useCallback((elementId: string) => {
    const el = document.getElementById(elementId)
    if (el) {
      el.classList.add('shake-animation')
      setTimeout(() => {
        el.classList.remove('shake-animation')
      }, 500)
    }
  }, [])

  return (
    <ActivityContext.Provider value={{
      showToast,
      hideToast,
      updateToast,
      showProgress,
      hideProgress,
      showConfetti,
      showShake,
    }}>
      {children}
      
      {/* Toast Container */}
      <ToastContainer toasts={toasts} onHide={hideToast} />
      
      {/* Progress Bars */}
      <ProgressContainer progressBars={progressBars} />
      
      {/* Confetti */}
      <ConfettiEffect show={showingConfetti} />
      
      {/* Shake CSS */}
      <style jsx global>{`
        .shake-animation {
          animation: shake 0.5s ease-in-out;
        }
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          10%, 30%, 50%, 70%, 90% { transform: translateX(-4px); }
          20%, 40%, 60%, 80% { transform: translateX(4px); }
        }
      `}</style>
    </ActivityContext.Provider>
  )
}

// Hook to use activity indicators
export function useActivity() {
  const context = useContext(ActivityContext)
  if (!context) {
    throw new Error('useActivity must be used within ActivityProvider')
  }
  return context
}

// Toast Container
export function ToastContainer({ toasts, onHide }: { toasts: Toast[]; onHide: (id: string) => void }) {
  return (
    <div className="fixed bottom-4 right-4 z-[200] flex flex-col gap-2 max-w-sm w-full">
      <AnimatePresence mode="popLayout">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} onHide={() => onHide(toast.id)} />
        ))}
      </AnimatePresence>
    </div>
  )
}

// Individual Toast
function ToastItem({ toast, onHide }: { toast: Toast; onHide: () => void }) {
  const icons = {
    success: CheckCircle2,
    error: XCircle,
    warning: AlertCircle,
    info: Info,
    loading: Loader2,
  }

  const colors = {
    success: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400',
    error: 'border-red-500/50 bg-red-500/10 text-red-400',
    warning: 'border-amber-500/50 bg-amber-500/10 text-amber-400',
    info: 'border-blue-500/50 bg-blue-500/10 text-blue-400',
    loading: 'border-purple-500/50 bg-purple-500/10 text-purple-400',
  }

  const Icon = icons[toast.type]

  return (
    <motion.div
      layout
      initial={{ opacity: 0, y: 20, scale: 0.95 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -20, scale: 0.95 }}
      transition={{ type: 'spring', stiffness: 400, damping: 30 }}
      className={cn(
        'relative p-4 rounded-xl border backdrop-blur-sm shadow-lg',
        'bg-gray-900/95',
        colors[toast.type]
      )}
    >
      <div className="flex items-start gap-3">
        <Icon className={cn(
          'w-5 h-5 flex-shrink-0 mt-0.5',
          toast.type === 'loading' && 'animate-spin'
        )} />
        <div className="flex-1 min-w-0">
          <p className="font-medium text-white text-sm">{toast.title}</p>
          {toast.description && (
            <p className="text-xs text-gray-400 mt-1">{toast.description}</p>
          )}
          {toast.action && (
            <Button
              size="sm"
              variant="ghost"
              onClick={toast.action.onClick}
              className="mt-2 h-7 text-xs"
            >
              {toast.action.label}
            </Button>
          )}
        </div>
        <Button
          variant="ghost"
          size="icon"
          onClick={onHide}
          className="h-6 w-6 hover:bg-white/10 flex-shrink-0"
        >
          <X className="w-3 h-3" />
        </Button>
      </div>
    </motion.div>
  )
}

// Progress Container
function ProgressContainer({ progressBars }: { progressBars: Map<string, { title: string; progress: number }> }) {
  if (progressBars.size === 0) return null

  return (
    <div className="fixed top-4 right-4 z-[200] flex flex-col gap-2 w-72">
      <AnimatePresence>
        {Array.from(progressBars.entries()).map(([id, { title, progress }]) => (
          <motion.div
            key={id}
            initial={{ opacity: 0, x: 20 }}
            animate={{ opacity: 1, x: 0 }}
            exit={{ opacity: 0, x: 20 }}
            className="p-3 rounded-lg bg-gray-900/95 border border-gray-700 backdrop-blur-sm shadow-lg"
          >
            <div className="flex items-center justify-between mb-2">
              <span className="text-sm font-medium text-white">{title}</span>
              <span className="text-xs text-gray-400">{Math.round(progress)}%</span>
            </div>
            <Progress value={progress} className="h-1.5" />
          </motion.div>
        ))}
      </AnimatePresence>
    </div>
  )
}

// Confetti Effect
function ConfettiEffect({ show }: { show: boolean }) {
  const [particles, setParticles] = useState<Array<{
    id: number
    x: number
    y: number
    color: string
    rotation: number
    size: number
  }>>([])

  useEffect(() => {
    if (show) {
      const colors = ['#10b981', '#8b5cf6', '#f59e0b', '#ec4899', '#3b82f6', '#ef4444']
      const newParticles = Array.from({ length: 50 }, (_, i) => ({
        id: i,
        x: 50 + (Math.random() - 0.5) * 30,
        y: 50 + (Math.random() - 0.5) * 30,
        color: colors[Math.floor(Math.random() * colors.length)],
        rotation: Math.random() * 360,
        size: 6 + Math.random() * 8,
      }))
      setParticles(newParticles)
    } else {
      setParticles([])
    }
  }, [show])

  if (!show) return null

  return (
    <div className="fixed inset-0 z-[300] pointer-events-none overflow-hidden">
      {/* Center burst */}
      <motion.div
        initial={{ scale: 0, opacity: 1 }}
        animate={{ scale: 2, opacity: 0 }}
        transition={{ duration: 0.5 }}
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-32 h-32 bg-gradient-radial from-purple-500/30 to-transparent rounded-full"
      />
      
      {/* Confetti particles */}
      {particles.map((particle) => (
        <motion.div
          key={particle.id}
          initial={{
            x: `${particle.x}vw`,
            y: `${particle.y}vh`,
            rotate: 0,
            opacity: 1,
          }}
          animate={{
            x: `${particle.x + (Math.random() - 0.5) * 60}vw`,
            y: `${particle.y + 50 + Math.random() * 30}vh`,
            rotate: particle.rotation + 360 * (Math.random() > 0.5 ? 1 : -1),
            opacity: 0,
          }}
          transition={{
            duration: 2 + Math.random(),
            ease: 'easeOut',
          }}
          style={{
            position: 'absolute',
            width: particle.size,
            height: particle.size * 0.6,
            backgroundColor: particle.color,
            borderRadius: 2,
          }}
        />
      ))}

      {/* Celebration icon */}
      <motion.div
        initial={{ scale: 0, y: '50%' }}
        animate={{ scale: [0, 1.2, 1], y: '50%' }}
        transition={{ duration: 0.4 }}
        className="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2"
      >
        <div className="bg-gradient-to-r from-purple-500 to-pink-500 p-4 rounded-full shadow-lg shadow-purple-500/50">
          <PartyPopper className="w-8 h-8 text-white" />
        </div>
      </motion.div>
    </div>
  )
}

// Loading Overlay Component
export function ProgressOverlay({ 
  show, 
  message = 'Processing...',
  progress 
}: { 
  show: boolean
  message?: string
  progress?: number 
}) {
  if (!show) return null

  return (
    <motion.div
      initial={{ opacity: 0 }}
      animate={{ opacity: 1 }}
      exit={{ opacity: 0 }}
      className="fixed inset-0 z-[150] bg-black/50 backdrop-blur-sm flex items-center justify-center"
    >
      <motion.div
        initial={{ scale: 0.9, opacity: 0 }}
        animate={{ scale: 1, opacity: 1 }}
        className="bg-gray-900 border border-gray-700 rounded-xl p-6 shadow-2xl max-w-sm w-full mx-4"
      >
        <div className="flex flex-col items-center text-center">
          <div className="relative">
            <Loader2 className="w-12 h-12 text-purple-500 animate-spin" />
            <Sparkles className="absolute -top-1 -right-1 w-5 h-5 text-purple-400 animate-pulse" />
          </div>
          <h3 className="mt-4 font-semibold text-white">{message}</h3>
          {progress !== undefined && (
            <div className="w-full mt-4">
              <Progress value={progress} className="h-2" />
              <p className="text-xs text-gray-400 mt-2">{Math.round(progress)}% complete</p>
            </div>
          )}
        </div>
      </motion.div>
    </motion.div>
  )
}

// Loading Spinner (simple version)
export function LoadingSpinner({ className }: { className?: string }) {
  return <Loader2 className={cn('w-4 h-4 animate-spin', className)} />
}

// Standalone Activity Indicator Component (for simple use cases)
export function ActivityIndicator({
  type,
  message,
}: {
  type: 'success' | 'error' | 'info' | 'loading'
  message: string
}) {
  const icons = {
    success: CheckCircle2,
    error: XCircle,
    info: Info,
    loading: Loader2,
  }

  const colors = {
    success: 'border-emerald-500/50 bg-emerald-500/10 text-emerald-400',
    error: 'border-red-500/50 bg-red-500/10 text-red-400',
    info: 'border-blue-500/50 bg-blue-500/10 text-blue-400',
    loading: 'border-purple-500/50 bg-purple-500/10 text-purple-400',
  }

  const Icon = icons[type]

  return (
    <motion.div
      initial={{ opacity: 0, y: -20, x: '-50%' }}
      animate={{ opacity: 1, y: 0, x: '-50%' }}
      exit={{ opacity: 0, y: -20, x: '-50%' }}
      className={cn(
        'fixed top-4 left-1/2 z-[200] px-4 py-2.5 rounded-full border backdrop-blur-sm shadow-lg',
        'flex items-center gap-2',
        colors[type]
      )}
    >
      <Icon className={cn(
        'w-4 h-4',
        type === 'loading' && 'animate-spin'
      )} />
      <span className="text-sm font-medium text-white whitespace-nowrap">{message}</span>
    </motion.div>
  )
}

export default ActivityProvider
