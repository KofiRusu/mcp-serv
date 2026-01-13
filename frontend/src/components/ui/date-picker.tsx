'use client'

import * as React from 'react'
import { useState, useEffect } from 'react'
import { Button } from './button'
import { Popover, PopoverContent, PopoverTrigger } from './popover'
import { cn } from '@/lib/utils'
import { CalendarDays, ChevronLeft, ChevronRight } from 'lucide-react'

interface DatePickerProps {
  value?: Date
  onChange?: (date: Date) => void
  placeholder?: string
  className?: string
  minDate?: Date
  maxDate?: Date
}

const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

const DAYS = ['Su', 'Mo', 'Tu', 'We', 'Th', 'Fr', 'Sa']

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay()
}

export function DatePicker({
  value,
  onChange,
  placeholder = 'Select date',
  className,
  minDate,
  maxDate,
}: DatePickerProps) {
  const [open, setOpen] = useState(false)
  const [viewDate, setViewDate] = useState(() => value || new Date())
  
  useEffect(() => {
    if (value) {
      setViewDate(value)
    }
  }, [value])

  const year = viewDate.getFullYear()
  const month = viewDate.getMonth()
  const daysInMonth = getDaysInMonth(year, month)
  const firstDay = getFirstDayOfMonth(year, month)

  const prevMonth = () => {
    setViewDate(new Date(year, month - 1, 1))
  }

  const nextMonth = () => {
    setViewDate(new Date(year, month + 1, 1))
  }

  const selectDate = (day: number) => {
    const newDate = new Date(year, month, day)
    onChange?.(newDate)
    setOpen(false)
  }

  const isDateDisabled = (day: number): boolean => {
    const date = new Date(year, month, day)
    if (minDate && date < minDate) return true
    if (maxDate && date > maxDate) return true
    return false
  }

  const isSelected = (day: number): boolean => {
    if (!value) return false
    return (
      value.getFullYear() === year &&
      value.getMonth() === month &&
      value.getDate() === day
    )
  }

  const isToday = (day: number): boolean => {
    const today = new Date()
    return (
      today.getFullYear() === year &&
      today.getMonth() === month &&
      today.getDate() === day
    )
  }

  const formatDate = (date?: Date): string => {
    if (!date) return placeholder
    return date.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric'
    })
  }

  // Generate calendar grid
  const calendarDays: (number | null)[] = []
  for (let i = 0; i < firstDay; i++) {
    calendarDays.push(null)
  }
  for (let i = 1; i <= daysInMonth; i++) {
    calendarDays.push(i)
  }

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild>
        <Button
          variant="outline"
          className={cn(
            'w-full justify-start text-left font-normal h-9 px-3 bg-gray-900 border-gray-700 hover:bg-gray-800',
            !value && 'text-muted-foreground',
            className
          )}
        >
          <CalendarDays className="mr-2 h-4 w-4 text-gray-400" />
          <span className="text-sm">{formatDate(value)}</span>
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-auto p-0 bg-[#1a1a24] border-gray-700" align="start">
        <div className="p-3">
          {/* Header with month/year navigation */}
          <div className="flex items-center justify-between mb-3">
            <button
              onClick={prevMonth}
              className="p-1.5 rounded-md hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
            >
              <ChevronLeft className="h-4 w-4" />
            </button>
            <span className="text-sm font-medium">
              {MONTHS[month]} {year}
            </span>
            <button
              onClick={nextMonth}
              className="p-1.5 rounded-md hover:bg-gray-800 text-gray-400 hover:text-white transition-colors"
            >
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>

          {/* Day headers */}
          <div className="grid grid-cols-7 gap-1 mb-1">
            {DAYS.map((day) => (
              <div
                key={day}
                className="h-8 w-8 flex items-center justify-center text-xs text-gray-500 font-medium"
              >
                {day}
              </div>
            ))}
          </div>

          {/* Calendar grid */}
          <div className="grid grid-cols-7 gap-1">
            {calendarDays.map((day, index) => (
              <div key={index} className="h-8 w-8">
                {day !== null && (
                  <button
                    onClick={() => selectDate(day)}
                    disabled={isDateDisabled(day)}
                    className={cn(
                      'h-8 w-8 rounded-md text-sm transition-colors flex items-center justify-center',
                      isSelected(day)
                        ? 'bg-purple-600 text-white'
                        : isToday(day)
                        ? 'bg-gray-800 text-purple-400'
                        : 'hover:bg-gray-800 text-gray-300',
                      isDateDisabled(day) && 'opacity-30 cursor-not-allowed hover:bg-transparent'
                    )}
                  >
                    {day}
                  </button>
                )}
              </div>
            ))}
          </div>

          {/* Quick actions */}
          <div className="flex gap-2 mt-3 pt-3 border-t border-gray-700">
            <button
              onClick={() => {
                onChange?.(new Date())
                setOpen(false)
              }}
              className="flex-1 px-2 py-1.5 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
            >
              Today
            </button>
            <button
              onClick={() => {
                const date = new Date()
                date.setDate(date.getDate() - 7)
                onChange?.(date)
                setOpen(false)
              }}
              className="flex-1 px-2 py-1.5 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
            >
              -7 days
            </button>
            <button
              onClick={() => {
                const date = new Date()
                date.setDate(date.getDate() - 30)
                onChange?.(date)
                setOpen(false)
              }}
              className="flex-1 px-2 py-1.5 text-xs text-gray-400 hover:text-white hover:bg-gray-800 rounded-md transition-colors"
            >
              -30 days
            </button>
          </div>
        </div>
      </PopoverContent>
    </Popover>
  )
}

