'use client'

import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { 
  X, 
  ChevronRight, 
  ChevronLeft,
  Sparkles,
  MessageSquare,
  LayoutGrid,
  Play,
  Rocket,
  CheckCircle2,
} from 'lucide-react'
import { Button } from '@/components/ui/button'
import { cn } from '@/lib/utils'

interface OnboardingTourProps {
  isOpen: boolean
  onComplete: () => void
}

interface TourStep {
  id: string
  title: string
  description: string
  icon: React.ReactNode
  highlight?: string // CSS selector to highlight
  position?: 'center' | 'left' | 'right' | 'bottom'
}

const TOUR_STEPS: TourStep[] = [
  {
    id: 'welcome',
    title: 'Welcome to Automation Builder! 🎉',
    description: 'Create powerful trading automations with AI or build them visually. Let me show you around.',
    icon: <Sparkles className="w-8 h-8 text-purple-400" />,
    position: 'center',
  },
  {
    id: 'ai-chat',
    title: 'AI Builder Chat',
    description: 'Describe what you want in natural language. Our AI will generate the automation blocks for you. Just say "Create a DCA bot that buys $100 of BTC every day".',
    icon: <MessageSquare className="w-8 h-8 text-purple-400" />,
    highlight: '[data-tour="ai-chat"]',
    position: 'right',
  },
  {
    id: 'canvas',
    title: 'Visual Canvas',
    description: 'Your automation blocks appear here. Drag to reposition, click to configure, and connect blocks to define the flow.',
    icon: <LayoutGrid className="w-8 h-8 text-emerald-400" />,
    highlight: '[data-tour="canvas"]',
    position: 'left',
  },
  {
    id: 'test',
    title: 'Test Your Automation',
    description: 'Click "Test Run" to see your automation in action. View logs and output in real-time without deploying.',
    icon: <Play className="w-8 h-8 text-blue-400" />,
    highlight: '[data-tour="test-run"]',
    position: 'bottom',
  },
  {
    id: 'deploy',
    title: 'Deploy to Production',
    description: 'When ready, deploy your automation to Docker. It will run continuously, even when the browser is closed.',
    icon: <Rocket className="w-8 h-8 text-emerald-400" />,
    highlight: '[data-tour="deploy"]',
    position: 'bottom',
  },
  {
    id: 'complete',
    title: 'You\'re All Set! ✨',
    description: 'Start building your first automation. Pick AI Chat for guided creation, Manual for full control, or Guided for step-by-step.',
    icon: <CheckCircle2 className="w-8 h-8 text-emerald-400" />,
    position: 'center',
  },
]

export function OnboardingTour({ isOpen, onComplete }: OnboardingTourProps) {
  const [currentStep, setCurrentStep] = useState(0)
  const [highlightPosition, setHighlightPosition] = useState<DOMRect | null>(null)

  const step = TOUR_STEPS[currentStep]
  const isFirst = currentStep === 0
  const isLast = currentStep === TOUR_STEPS.length - 1

  // Find highlighted element position
  useEffect(() => {
    if (step.highlight && isOpen) {
      const el = document.querySelector(step.highlight)
      if (el) {
        const rect = el.getBoundingClientRect()
        setHighlightPosition(rect)
      } else {
        setHighlightPosition(null)
      }
    } else {
      setHighlightPosition(null)
    }
  }, [step, isOpen])

  const handleNext = () => {
    if (isLast) {
      onComplete()
    } else {
      setCurrentStep(prev => prev + 1)
    }
  }

  const handlePrev = () => {
    if (!isFirst) {
      setCurrentStep(prev => prev - 1)
    }
  }

  const handleSkip = () => {
    onComplete()
  }

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <motion.div
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        exit={{ opacity: 0 }}
        className="fixed inset-0 z-[100]"
      >
        {/* Backdrop */}
        <div className="absolute inset-0 bg-black/80 backdrop-blur-sm" />
        
        {/* Spotlight Cutout */}
        {highlightPosition && (
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            className="absolute pointer-events-none"
            style={{
              left: highlightPosition.left - 8,
              top: highlightPosition.top - 8,
              width: highlightPosition.width + 16,
              height: highlightPosition.height + 16,
              boxShadow: '0 0 0 9999px rgba(0,0,0,0.8)',
              borderRadius: '12px',
              border: '2px solid rgba(168, 85, 247, 0.5)',
            }}
          />
        )}

        {/* Tour Card */}
        <motion.div
          key={step.id}
          initial={{ opacity: 0, y: 20, scale: 0.95 }}
          animate={{ opacity: 1, y: 0, scale: 1 }}
          exit={{ opacity: 0, y: -20, scale: 0.95 }}
          transition={{ type: 'spring', damping: 25, stiffness: 300 }}
          className={cn(
            "absolute bg-gray-900 border border-gray-700 rounded-xl shadow-2xl p-6 max-w-md",
            "shadow-purple-500/10",
            step.position === 'center' && "top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2",
            step.position === 'left' && "top-1/2 left-1/2 -translate-y-1/2 ml-8",
            step.position === 'right' && "top-1/2 right-8 -translate-y-1/2",
            step.position === 'bottom' && "bottom-64 left-1/2 -translate-x-1/2"
          )}
          style={
            highlightPosition && step.position === 'right'
              ? { left: highlightPosition.right + 24, top: highlightPosition.top }
              : highlightPosition && step.position === 'left'
              ? { left: highlightPosition.left - 440, top: highlightPosition.top }
              : {}
          }
        >
          {/* Close button */}
          <button
            onClick={handleSkip}
            className="absolute top-3 right-3 p-1 rounded-lg hover:bg-gray-800 transition-colors text-gray-400 hover:text-gray-200"
          >
            <X className="w-5 h-5" />
          </button>

          {/* Content */}
          <div className="flex flex-col items-center text-center">
            {/* Icon */}
            <motion.div
              animate={{ 
                scale: [1, 1.1, 1],
                rotate: [0, 5, -5, 0],
              }}
              transition={{ duration: 2, repeat: Infinity }}
              className="p-4 bg-gradient-to-br from-purple-500/20 to-pink-500/20 rounded-2xl mb-4"
            >
              {step.icon}
            </motion.div>

            {/* Title */}
            <h3 className="text-xl font-bold text-white mb-2">{step.title}</h3>
            
            {/* Description */}
            <p className="text-gray-400 text-sm leading-relaxed mb-6">
              {step.description}
            </p>

            {/* Progress dots */}
            <div className="flex gap-2 mb-6">
              {TOUR_STEPS.map((_, i) => (
                <button
                  key={i}
                  onClick={() => setCurrentStep(i)}
                  className={cn(
                    "w-2 h-2 rounded-full transition-all",
                    i === currentStep 
                      ? "w-6 bg-purple-500" 
                      : i < currentStep
                      ? "bg-purple-500/50"
                      : "bg-gray-600"
                  )}
                />
              ))}
            </div>

            {/* Navigation */}
            <div className="flex items-center gap-3 w-full">
              {!isFirst && (
                <Button
                  variant="outline"
                  onClick={handlePrev}
                  className="flex-1 gap-1"
                >
                  <ChevronLeft className="w-4 h-4" />
                  Back
                </Button>
              )}
              
              {isFirst && (
                <Button
                  variant="ghost"
                  onClick={handleSkip}
                  className="flex-1 text-gray-400"
                >
                  Skip Tour
                </Button>
              )}

              <Button
                onClick={handleNext}
                className={cn(
                  "flex-1 gap-1",
                  isLast 
                    ? "bg-emerald-600 hover:bg-emerald-500" 
                    : "bg-purple-600 hover:bg-purple-500"
                )}
              >
                {isLast ? 'Get Started' : 'Next'}
                {!isLast && <ChevronRight className="w-4 h-4" />}
              </Button>
            </div>
          </div>
        </motion.div>

        {/* Keyboard hints */}
        <div className="absolute bottom-4 left-1/2 -translate-x-1/2 text-xs text-gray-500 flex gap-4">
          <span>← → Navigate</span>
          <span>ESC Skip</span>
        </div>
      </motion.div>
    </AnimatePresence>
  )
}

export default OnboardingTour

