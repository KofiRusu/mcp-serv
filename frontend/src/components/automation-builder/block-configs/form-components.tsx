'use client'

import React, { useState, useEffect, useCallback } from 'react'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Slider } from '@/components/ui/slider'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { Badge } from '@/components/ui/badge'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'
import {
  Command,
  CommandEmpty,
  CommandGroup,
  CommandInput,
  CommandItem,
  CommandList,
} from '@/components/ui/command'
import {
  Popover,
  PopoverContent,
  PopoverTrigger,
} from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { Check, ChevronsUpDown, X, Upload, AlertCircle } from 'lucide-react'
import type { FieldSchema, BlockConfigSchema } from './schemas'

// ============ NUMBER INPUT ============
interface NumberInputProps {
  field: FieldSchema
  value: number
  onChange: (value: number) => void
}

export function NumberInput({ field, value, onChange }: NumberInputProps) {
  const [localValue, setLocalValue] = useState(value?.toString() || field.default?.toString() || '0')
  const [error, setError] = useState<string | null>(null)

  const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const newValue = e.target.value
    setLocalValue(newValue)
    
    const num = parseFloat(newValue)
    if (isNaN(num)) {
      setError('Must be a number')
      return
    }
    
    if (field.min !== undefined && num < field.min) {
      setError(`Min: ${field.min}`)
      return
    }
    
    if (field.max !== undefined && num > field.max) {
      setError(`Max: ${field.max}`)
      return
    }
    
    setError(null)
    onChange(num)
  }

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <div className="relative">
        <Input
          type="number"
          value={localValue}
          onChange={handleChange}
          min={field.min}
          max={field.max}
          step={field.step || 1}
          className={cn(error && 'border-red-500')}
        />
        {error && (
          <div className="flex items-center gap-1 mt-1 text-xs text-red-500">
            <AlertCircle className="w-3 h-3" />
            {error}
          </div>
        )}
      </div>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ SLIDER INPUT ============
interface SliderInputProps {
  field: FieldSchema
  value: number
  onChange: (value: number) => void
}

export function SliderInput({ field, value, onChange }: SliderInputProps) {
  const currentValue = value ?? field.default ?? field.min ?? 0

  return (
    <div className="space-y-3">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{field.label}</Label>
        {field.showValue && (
          <span className="text-sm font-mono bg-muted px-2 py-0.5 rounded">
            {currentValue}
          </span>
        )}
      </div>
      <Slider
        value={[currentValue]}
        onValueChange={([v]) => onChange(v)}
        min={field.min ?? 0}
        max={field.max ?? 100}
        step={field.step ?? 1}
        className="w-full"
      />
      <div className="flex justify-between text-xs text-muted-foreground">
        <span>{field.min}</span>
        <span>{field.max}</span>
      </div>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ SELECT INPUT ============
interface SelectInputProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

export function SelectInput({ field, value, onChange }: SelectInputProps) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <Select value={value || field.default} onValueChange={onChange}>
        <SelectTrigger>
          <SelectValue placeholder={`Select ${field.label.toLowerCase()}`} />
        </SelectTrigger>
        <SelectContent>
          {field.options?.map((option) => (
            <SelectItem key={option.value} value={option.value}>
              {option.label}
            </SelectItem>
          ))}
        </SelectContent>
      </Select>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ MULTI-SELECT INPUT ============
interface MultiSelectInputProps {
  field: FieldSchema
  value: string[]
  onChange: (value: string[]) => void
}

export function MultiSelectInput({ field, value, onChange }: MultiSelectInputProps) {
  const [open, setOpen] = useState(false)
  const [customInput, setCustomInput] = useState('')
  const selectedValues = value || field.default || []

  const toggleValue = (val: string) => {
    if (selectedValues.includes(val)) {
      onChange(selectedValues.filter((v: string) => v !== val))
    } else {
      onChange([...selectedValues, val])
    }
  }

  const addCustom = () => {
    if (customInput && !selectedValues.includes(customInput)) {
      onChange([...selectedValues, customInput])
      setCustomInput('')
    }
  }

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between h-auto min-h-10"
          >
            <div className="flex flex-wrap gap-1">
              {selectedValues.length > 0 ? (
                selectedValues.map((val: string) => (
                  <Badge key={val} variant="secondary" className="text-xs">
                    {val}
                    <X
                      className="ml-1 h-3 w-3 cursor-pointer"
                      onClick={(e) => {
                        e.stopPropagation()
                        toggleValue(val)
                      }}
                    />
                  </Badge>
                ))
              ) : (
                <span className="text-muted-foreground">Select items...</span>
              )}
            </div>
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-full p-0" align="start">
          <Command>
            <CommandInput placeholder="Search..." />
            <CommandList>
              <CommandEmpty>No items found.</CommandEmpty>
              <CommandGroup>
                {field.options?.map((option) => (
                  <CommandItem
                    key={option.value}
                    onSelect={() => toggleValue(option.value)}
                  >
                    <Check
                      className={cn(
                        'mr-2 h-4 w-4',
                        selectedValues.includes(option.value) ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                    {option.label}
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
            {field.allowCustom && (
              <div className="p-2 border-t flex gap-2">
                <Input
                  placeholder="Add custom..."
                  value={customInput}
                  onChange={(e) => setCustomInput(e.target.value)}
                  onKeyDown={(e) => e.key === 'Enter' && addCustom()}
                  className="h-8"
                />
                <Button size="sm" onClick={addCustom}>Add</Button>
              </div>
            )}
          </Command>
        </PopoverContent>
      </Popover>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ TOGGLE INPUT ============
interface ToggleInputProps {
  field: FieldSchema
  value: boolean
  onChange: (value: boolean) => void
}

export function ToggleInput({ field, value, onChange }: ToggleInputProps) {
  return (
    <div className="flex items-center justify-between py-2">
      <div className="space-y-0.5">
        <Label className="text-sm font-medium">{field.label}</Label>
        {field.description && (
          <p className="text-xs text-muted-foreground">{field.description}</p>
        )}
      </div>
      <Switch
        checked={value ?? field.default ?? false}
        onCheckedChange={onChange}
      />
    </div>
  )
}

// ============ SYMBOL SELECT ============
interface SymbolSelectProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

const POPULAR_SYMBOLS = [
  { value: 'BTCUSDT', label: 'BTC/USDT', icon: '₿' },
  { value: 'ETHUSDT', label: 'ETH/USDT', icon: 'Ξ' },
  { value: 'SOLUSDT', label: 'SOL/USDT', icon: '◎' },
  { value: 'BNBUSDT', label: 'BNB/USDT', icon: '⬡' },
  { value: 'XRPUSDT', label: 'XRP/USDT', icon: '✕' },
  { value: 'ADAUSDT', label: 'ADA/USDT', icon: '₳' },
  { value: 'DOGEUSDT', label: 'DOGE/USDT', icon: 'Ð' },
  { value: 'AVAXUSDT', label: 'AVAX/USDT', icon: '▲' },
  { value: 'DOTUSDT', label: 'DOT/USDT', icon: '●' },
  { value: 'MATICUSDT', label: 'MATIC/USDT', icon: '⬡' },
]

export function SymbolSelect({ field, value, onChange }: SymbolSelectProps) {
  const [open, setOpen] = useState(false)
  const [search, setSearch] = useState('')

  const filteredSymbols = POPULAR_SYMBOLS.filter(
    (s) => s.value.toLowerCase().includes(search.toLowerCase()) ||
           s.label.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <Popover open={open} onOpenChange={setOpen}>
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            role="combobox"
            aria-expanded={open}
            className="w-full justify-between"
          >
            {value ? (
              <span className="flex items-center gap-2">
                <span className="text-lg">
                  {POPULAR_SYMBOLS.find(s => s.value === value)?.icon || '●'}
                </span>
                {POPULAR_SYMBOLS.find(s => s.value === value)?.label || value}
              </span>
            ) : (
              <span className="text-muted-foreground">Select symbol...</span>
            )}
            <ChevronsUpDown className="ml-2 h-4 w-4 shrink-0 opacity-50" />
          </Button>
        </PopoverTrigger>
        <PopoverContent className="w-[250px] p-0">
          <Command>
            <CommandInput 
              placeholder="Search symbol..." 
              value={search}
              onValueChange={setSearch}
            />
            <CommandList>
              <CommandEmpty>
                <Button
                  variant="ghost"
                  className="w-full"
                  onClick={() => {
                    onChange(search.toUpperCase())
                    setOpen(false)
                  }}
                >
                  Use "{search.toUpperCase()}"
                </Button>
              </CommandEmpty>
              <CommandGroup>
                {filteredSymbols.map((symbol) => (
                  <CommandItem
                    key={symbol.value}
                    onSelect={() => {
                      onChange(symbol.value)
                      setOpen(false)
                    }}
                  >
                    <span className="text-lg mr-2">{symbol.icon}</span>
                    <span>{symbol.label}</span>
                    <Check
                      className={cn(
                        'ml-auto h-4 w-4',
                        value === symbol.value ? 'opacity-100' : 'opacity-0'
                      )}
                    />
                  </CommandItem>
                ))}
              </CommandGroup>
            </CommandList>
          </Command>
        </PopoverContent>
      </Popover>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ INTERVAL PICKER ============
interface IntervalPickerProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

const INTERVAL_OPTIONS = [
  { value: '1s', label: '1s', category: 'Seconds' },
  { value: '5s', label: '5s', category: 'Seconds' },
  { value: '15s', label: '15s', category: 'Seconds' },
  { value: '30s', label: '30s', category: 'Seconds' },
  { value: '1m', label: '1m', category: 'Minutes' },
  { value: '3m', label: '3m', category: 'Minutes' },
  { value: '5m', label: '5m', category: 'Minutes' },
  { value: '15m', label: '15m', category: 'Minutes' },
  { value: '30m', label: '30m', category: 'Minutes' },
  { value: '1h', label: '1h', category: 'Hours' },
  { value: '2h', label: '2h', category: 'Hours' },
  { value: '4h', label: '4h', category: 'Hours' },
  { value: '6h', label: '6h', category: 'Hours' },
  { value: '12h', label: '12h', category: 'Hours' },
  { value: '1d', label: '1D', category: 'Days' },
  { value: '3d', label: '3D', category: 'Days' },
  { value: '1w', label: '1W', category: 'Weeks' },
  { value: '1M', label: '1M', category: 'Months' },
]

export function IntervalPicker({ field, value, onChange }: IntervalPickerProps) {
  const currentValue = value || field.default || '1m'
  
  // Group by category
  const categories = [...new Set(INTERVAL_OPTIONS.map(o => o.category))]

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <div className="grid grid-cols-4 gap-1">
        {INTERVAL_OPTIONS.slice(0, 12).map((interval) => (
          <Button
            key={interval.value}
            variant={currentValue === interval.value ? 'default' : 'outline'}
            size="sm"
            className={cn(
              'h-8',
              currentValue === interval.value && 'bg-primary'
            )}
            onClick={() => onChange(interval.value)}
          >
            {interval.label}
          </Button>
        ))}
      </div>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ CONDITION BUILDER ============
interface ConditionBuilderProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

const CONDITION_TEMPLATES = [
  { label: 'RSI Oversold', value: 'rsi < 30' },
  { label: 'RSI Overbought', value: 'rsi > 70' },
  { label: 'MACD Bullish Cross', value: 'macd > signal && prev_macd <= prev_signal' },
  { label: 'MACD Bearish Cross', value: 'macd < signal && prev_macd >= prev_signal' },
  { label: 'Price Above MA', value: 'price > ma' },
  { label: 'Price Below MA', value: 'price < ma' },
  { label: 'Volume Spike', value: 'volume > avg_volume * 2' },
  { label: 'Profit Target', value: 'profit > 5' },
  { label: 'Stop Loss', value: 'loss > 2' },
]

export function ConditionBuilder({ field, value, onChange }: ConditionBuilderProps) {
  const [showTemplates, setShowTemplates] = useState(false)

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{field.label}</Label>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => setShowTemplates(!showTemplates)}
          className="text-xs"
        >
          {showTemplates ? 'Hide' : 'Templates'}
        </Button>
      </div>
      
      {showTemplates && (
        <div className="flex flex-wrap gap-1 p-2 bg-muted rounded-md">
          {CONDITION_TEMPLATES.map((template) => (
            <Badge
              key={template.value}
              variant="outline"
              className="cursor-pointer hover:bg-accent"
              onClick={() => {
                onChange(value ? `${value} && ${template.value}` : template.value)
              }}
            >
              {template.label}
            </Badge>
          ))}
        </div>
      )}
      
      <Textarea
        value={value || field.default || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder="Enter condition expression..."
        className="font-mono text-sm"
        rows={3}
      />
      
      <div className="text-xs text-muted-foreground">
        <p>Available variables: price, volume, rsi, macd, signal, ma, profit, loss</p>
      </div>
      
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ JSON INPUT ============
interface JsonInputProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

export function JsonInput({ field, value, onChange }: JsonInputProps) {
  const [error, setError] = useState<string | null>(null)
  const currentValue = value || field.default || '{}'

  const handleChange = (newValue: string) => {
    onChange(newValue)
    try {
      JSON.parse(newValue)
      setError(null)
    } catch (e) {
      setError('Invalid JSON')
    }
  }

  const formatJson = () => {
    try {
      const parsed = JSON.parse(currentValue)
      onChange(JSON.stringify(parsed, null, 2))
      setError(null)
    } catch (e) {
      setError('Cannot format invalid JSON')
    }
  }

  return (
    <div className="space-y-2">
      <div className="flex items-center justify-between">
        <Label className="text-sm font-medium">{field.label}</Label>
        <Button variant="ghost" size="sm" onClick={formatJson} className="text-xs">
          Format
        </Button>
      </div>
      <Textarea
        value={currentValue}
        onChange={(e) => handleChange(e.target.value)}
        className={cn('font-mono text-sm', error && 'border-red-500')}
        rows={4}
      />
      {error && (
        <div className="flex items-center gap-1 text-xs text-red-500">
          <AlertCircle className="w-3 h-3" />
          {error}
        </div>
      )}
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ URL INPUT ============
interface UrlInputProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

export function UrlInput({ field, value, onChange }: UrlInputProps) {
  const [error, setError] = useState<string | null>(null)

  const validateUrl = (url: string) => {
    if (!url) {
      setError(field.required ? 'URL is required' : null)
      return
    }
    try {
      new URL(url)
      setError(null)
    } catch {
      setError('Invalid URL format')
    }
  }

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <Input
        type="url"
        value={value || field.default || ''}
        onChange={(e) => {
          onChange(e.target.value)
          validateUrl(e.target.value)
        }}
        placeholder="https://..."
        className={cn(error && 'border-red-500')}
      />
      {error && (
        <div className="flex items-center gap-1 text-xs text-red-500">
          <AlertCircle className="w-3 h-3" />
          {error}
        </div>
      )}
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ FILE INPUT ============
interface FileInputProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

export function FileInput({ field, value, onChange }: FileInputProps) {
  const [fileName, setFileName] = useState<string | null>(null)

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) {
      setFileName(file.name)
      // In a real implementation, you'd upload the file and store the path
      onChange(file.name)
    }
  }

  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <div className="flex items-center gap-2">
        <Input
          type="file"
          onChange={handleFileChange}
          className="hidden"
          id={`file-${field.name}`}
          accept=".csv,.json"
        />
        <Button
          variant="outline"
          onClick={() => document.getElementById(`file-${field.name}`)?.click()}
          className="flex items-center gap-2"
        >
          <Upload className="w-4 h-4" />
          Choose File
        </Button>
        {(fileName || value) && (
          <span className="text-sm text-muted-foreground truncate max-w-[200px]">
            {fileName || value}
          </span>
        )}
      </div>
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ TEXT INPUT ============
interface TextInputProps {
  field: FieldSchema
  value: string
  onChange: (value: string) => void
}

export function TextInput({ field, value, onChange }: TextInputProps) {
  return (
    <div className="space-y-2">
      <Label className="text-sm font-medium">{field.label}</Label>
      <Input
        type="text"
        value={value || field.default || ''}
        onChange={(e) => onChange(e.target.value)}
        placeholder={field.description || `Enter ${field.label.toLowerCase()}`}
      />
      {field.description && (
        <p className="text-xs text-muted-foreground">{field.description}</p>
      )}
    </div>
  )
}

// ============ DYNAMIC CONFIG FORM ============
interface ConfigFormProps {
  schema: BlockConfigSchema
  config: Record<string, any>
  onChange: (config: Record<string, any>) => void
}

export function ConfigForm({ schema, config, onChange }: ConfigFormProps) {
  const handleFieldChange = useCallback((fieldName: string, value: any) => {
    onChange({ ...config, [fieldName]: value })
  }, [config, onChange])

  const renderField = (field: FieldSchema) => {
    const value = config[field.name]
    const key = `${schema.blockName}-${field.name}`

    switch (field.type) {
      case 'number':
        return (
          <NumberInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'slider':
        return (
          <SliderInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'select':
        return (
          <SelectInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'multi-select':
        return (
          <MultiSelectInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'toggle':
        return (
          <ToggleInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'symbol':
        return (
          <SymbolSelect
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'interval':
        return (
          <IntervalPicker
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'condition':
        return (
          <ConditionBuilder
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'json':
        return (
          <JsonInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'url':
        return (
          <UrlInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'file':
        return (
          <FileInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
      case 'text':
      default:
        return (
          <TextInput
            key={key}
            field={field}
            value={value}
            onChange={(v) => handleFieldChange(field.name, v)}
          />
        )
    }
  }

  return (
    <div className="space-y-4">
      {schema.fields.map(renderField)}
    </div>
  )
}

