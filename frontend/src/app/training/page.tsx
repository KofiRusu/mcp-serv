/**
 * Training Submission Interface
 * 
 * A beautiful, modern UI for submitting training examples to ChatOS
 * Supports single examples, batch uploads, and submission tracking
 */

'use client';

import { useState, useCallback } from 'react';
import { Card } from '@/components/ui/card';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Textarea } from '@/components/ui/textarea';
import { Label } from '@/components/ui/label';
import { Badge } from '@/components/ui/badge';
import { Skeleton } from '@/components/ui/skeleton';
import { ScrollArea } from '@/components/ui/scroll-area';
import {
  AlertCircle,
  CheckCircle2,
  Loader2,
  Upload,
  Send,
  BarChart3,
  Zap,
  BookOpen,
} from 'lucide-react';

interface TrainingExample {
  instruction: string;
  output: string;
  category: string;
  difficulty: string;
}

interface SubmissionResponse {
  submission_id: string;
  status: string;
  count: number;
  message: string;
  timestamp: string;
}

interface QueueStatus {
  total_submissions: number;
  pending: number;
  processing: number;
  completed: number;
  failed: number;
  queue_size: number;
}

const API_BASE = 'http://localhost:8000/api/training';

const CATEGORIES = [
  { value: 'trading', label: '📈 Trading' },
  { value: 'investing', label: '💼 Investing' },
  { value: 'risk', label: '⚠️ Risk Management' },
  { value: 'crypto', label: '₿ Cryptocurrency' },
  { value: 'general', label: '🎓 General' },
];

const DIFFICULTIES = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
  { value: 'expert', label: 'Expert' },
];

export default function TrainingPage() {
  const [tab, setTab] = useState('single');
  const [loading, setLoading] = useState(false);
  const [message, setMessage] = useState<{ type: 'success' | 'error'; text: string } | null>(null);
  const [queueStatus, setQueueStatus] = useState<QueueStatus | null>(null);
  const [submissions, setSubmissions] = useState<SubmissionResponse[]>([]);

  // Single example form
  const [singleExample, setSingleExample] = useState<TrainingExample>({
    instruction: '',
    output: '',
    category: 'trading',
    difficulty: 'medium',
  });

  // Batch form
  const [batchName, setBatchName] = useState('');
  const [batchDescription, setBatchDescription] = useState('');
  const [batchExamples, setBatchExamples] = useState<TrainingExample[]>([
    { instruction: '', output: '', category: 'trading', difficulty: 'medium' },
  ]);

  // Fetch queue status
  const fetchQueueStatus = useCallback(async () => {
    try {
      const res = await fetch(`${API_BASE}/queue/status`);
      if (res.ok) {
        const data = await res.json();
        setQueueStatus(data);
      }
    } catch (err) {
      console.error('Failed to fetch queue status:', err);
    }
  }, []);

  // Submit single example
  const handleSubmitSingle = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!singleExample.instruction.trim() || !singleExample.output.trim()) {
      setMessage({ type: 'error', text: 'Please fill in both instruction and output fields.' });
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/submit-example`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(singleExample),
      });

      if (res.ok) {
        const data: SubmissionResponse = await res.json();
        setSubmissions([data, ...submissions]);
        setMessage({ type: 'success', text: `✓ Example submitted (ID: ${data.submission_id})` });
        setSingleExample({
          instruction: '',
          output: '',
          category: 'trading',
          difficulty: 'medium',
        });
        fetchQueueStatus();
      } else {
        const error = await res.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to submit example.' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  // Submit batch
  const handleSubmitBatch = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!batchName.trim()) {
      setMessage({ type: 'error', text: 'Please enter a batch name.' });
      return;
    }

    const validExamples = batchExamples.filter(
      (ex) => ex.instruction.trim() && ex.output.trim()
    );

    if (validExamples.length === 0) {
      setMessage({ type: 'error', text: 'Please add at least one complete example.' });
      return;
    }

    setLoading(true);
    try {
      const res = await fetch(`${API_BASE}/submit-batch`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          batch_name: batchName,
          description: batchDescription,
          examples: validExamples,
        }),
      });

      if (res.ok) {
        const data: SubmissionResponse = await res.json();
        setSubmissions([data, ...submissions]);
        setMessage({
          type: 'success',
          text: `✓ Batch submitted with ${data.count} examples (ID: ${data.submission_id})`,
        });
        setBatchName('');
        setBatchDescription('');
        setBatchExamples([
          { instruction: '', output: '', category: 'trading', difficulty: 'medium' },
        ]);
        fetchQueueStatus();
      } else {
        const error = await res.json();
        setMessage({ type: 'error', text: error.detail || 'Failed to submit batch.' });
      }
    } catch (err) {
      setMessage({ type: 'error', text: 'Network error. Please try again.' });
    } finally {
      setLoading(false);
    }
  };

  // Add batch example
  const addBatchExample = () => {
    setBatchExamples([
      ...batchExamples,
      { instruction: '', output: '', category: 'trading', difficulty: 'medium' },
    ]);
  };

  // Remove batch example
  const removeBatchExample = (index: number) => {
    setBatchExamples(batchExamples.filter((_, i) => i !== index));
  };

  // Update batch example
  const updateBatchExample = (index: number, field: keyof TrainingExample, value: string) => {
    const updated = [...batchExamples];
    updated[index] = { ...updated[index], [field]: value };
    setBatchExamples(updated);
  };

  return (
    <div className="min-h-screen bg-gradient-to-br from-slate-950 via-slate-900 to-slate-800">
      {/* Header */}
      <div className="border-b border-slate-700 bg-slate-950/50 backdrop-blur">
        <div className="max-w-6xl mx-auto px-6 py-8">
          <div className="flex items-center justify-between mb-4">
            <div>
              <h1 className="text-4xl font-bold text-white mb-2 flex items-center gap-3">
                <Zap className="text-amber-400" size={32} />
                Training Submission
              </h1>
              <p className="text-slate-400">
                Submit training examples to improve ChatOS model performance
              </p>
            </div>
            <Button
              variant="outline"
              onClick={fetchQueueStatus}
              className="gap-2"
              disabled={loading}
            >
              <BarChart3 size={16} />
              Refresh Stats
            </Button>
          </div>
        </div>
      </div>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
          {/* Left Column - Forms */}
          <div className="lg:col-span-2 space-y-6">
            {/* Message Alert */}
            {message && (
              <div
                className={`border-l-4 p-4 rounded-lg flex items-center gap-3 ${
                  message.type === 'success'
                    ? 'border-l-green-500 bg-green-500/10'
                    : 'border-l-red-500 bg-red-500/10'
                }`}
              >
                {message.type === 'success' ? (
                  <CheckCircle2 className="text-green-500" size={20} />
                ) : (
                  <AlertCircle className="text-red-500" size={20} />
                )}
                <span className={message.type === 'success' ? 'text-green-200' : 'text-red-200'}>
                  {message.text}
                </span>
              </div>
            )}

            {/* Tab Navigation */}
            <div className="flex gap-2 border-b border-slate-700 mb-6">
              <button
                onClick={() => setTab('single')}
                className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                  tab === 'single'
                    ? 'border-amber-400 text-amber-400'
                    : 'border-transparent text-slate-400 hover:text-slate-300'
                }`}
              >
                <Send className="inline mr-2" size={18} />
                Single Example
              </button>
              <button
                onClick={() => setTab('batch')}
                className={`px-6 py-3 font-medium transition-colors border-b-2 ${
                  tab === 'batch'
                    ? 'border-amber-400 text-amber-400'
                    : 'border-transparent text-slate-400 hover:text-slate-300'
                }`}
              >
                <Upload className="inline mr-2" size={18} />
                Batch Submit
              </button>
            </div>

            {/* Single Example Tab */}
            {tab === 'single' && (
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <form onSubmit={handleSubmitSingle} className="space-y-6">
                  <div className="space-y-2">
                    <Label className="text-slate-300">Instruction / Question</Label>
                    <Textarea
                      placeholder="e.g., What is the RSI indicator used for in trading?"
                      value={singleExample.instruction}
                      onChange={(e) =>
                        setSingleExample({
                          ...singleExample,
                          instruction: e.target.value,
                        })
                      }
                      className="min-h-24 bg-slate-900 border-slate-600 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-slate-300">Output / Answer</Label>
                    <Textarea
                      placeholder="e.g., RSI measures the magnitude of recent price changes... (detailed explanation)"
                      value={singleExample.output}
                      onChange={(e) =>
                        setSingleExample({
                          ...singleExample,
                          output: e.target.value,
                        })
                      }
                      className="min-h-32 bg-slate-900 border-slate-600 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div className="grid grid-cols-2 gap-4">
                    <div className="space-y-2">
                      <Label className="text-slate-300">Category</Label>
                      <select
                        value={singleExample.category}
                        onChange={(e) =>
                          setSingleExample({
                            ...singleExample,
                            category: e.target.value,
                          })
                        }
                        className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white"
                      >
                        {CATEGORIES.map((cat) => (
                          <option key={cat.value} value={cat.value}>
                            {cat.label}
                          </option>
                        ))}
                      </select>
                    </div>

                    <div className="space-y-2">
                      <Label className="text-slate-300">Difficulty</Label>
                      <select
                        value={singleExample.difficulty}
                        onChange={(e) =>
                          setSingleExample({
                            ...singleExample,
                            difficulty: e.target.value,
                          })
                        }
                        className="w-full px-4 py-2 bg-slate-900 border border-slate-600 rounded-lg text-white"
                      >
                        {DIFFICULTIES.map((diff) => (
                          <option key={diff.value} value={diff.value}>
                            {diff.label}
                          </option>
                        ))}
                      </select>
                    </div>
                  </div>

                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-amber-500 hover:bg-amber-600 text-black font-semibold py-3"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 animate-spin" size={18} />
                        Submitting...
                      </>
                    ) : (
                      <>
                        <Send className="mr-2" size={18} />
                        Submit Example
                      </>
                    )}
                  </Button>
                </form>
              </Card>
            )}

            {/* Batch Tab */}
            {tab === 'batch' && (
              <Card className="bg-slate-800/50 border-slate-700 p-6">
                <form onSubmit={handleSubmitBatch} className="space-y-6">
                  <div className="space-y-2">
                    <Label className="text-slate-300">Batch Name</Label>
                    <Input
                      placeholder="e.g., advanced-trading-strategies"
                      value={batchName}
                      onChange={(e) => setBatchName(e.target.value)}
                      className="bg-slate-900 border-slate-600 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div className="space-y-2">
                    <Label className="text-slate-300">Description (Optional)</Label>
                    <Textarea
                      placeholder="Describe this batch of examples..."
                      value={batchDescription}
                      onChange={(e) => setBatchDescription(e.target.value)}
                      className="min-h-20 bg-slate-900 border-slate-600 text-white placeholder:text-slate-500"
                    />
                  </div>

                  <div className="space-y-4">
                    <div className="flex items-center justify-between">
                      <Label className="text-slate-300 font-semibold">Examples</Label>
                      <span className="text-sm text-slate-400">
                        {batchExamples.filter((ex) => ex.instruction && ex.output).length} valid
                      </span>
                    </div>

                    <ScrollArea className="h-96 pr-4">
                      <div className="space-y-4">
                        {batchExamples.map((example, idx) => (
                          <Card
                            key={idx}
                            className="bg-slate-900 border-slate-600 p-4 space-y-3"
                          >
                            <div className="flex items-center justify-between">
                              <span className="text-sm font-semibold text-amber-400">
                                Example {idx + 1}
                              </span>
                              {batchExamples.length > 1 && (
                                <Button
                                  type="button"
                                  variant="ghost"
                                  size="sm"
                                  onClick={() => removeBatchExample(idx)}
                                  className="text-red-400 hover:text-red-300 hover:bg-red-500/10"
                                >
                                  Remove
                                </Button>
                              )}
                            </div>

                            <div className="space-y-2">
                              <Input
                                placeholder="Instruction / Question"
                                value={example.instruction}
                                onChange={(e) =>
                                  updateBatchExample(idx, 'instruction', e.target.value)
                                }
                                className="bg-slate-800 border-slate-500 text-white text-sm"
                              />
                            </div>

                            <div className="space-y-2">
                              <Textarea
                                placeholder="Output / Answer"
                                value={example.output}
                                onChange={(e) =>
                                  updateBatchExample(idx, 'output', e.target.value)
                                }
                                className="min-h-16 bg-slate-800 border-slate-500 text-white text-sm"
                              />
                            </div>

                            <div className="grid grid-cols-2 gap-2">
                              <select
                                value={example.category}
                                onChange={(e) =>
                                  updateBatchExample(idx, 'category', e.target.value)
                                }
                                className="px-3 py-2 bg-slate-800 border border-slate-500 rounded text-white text-sm"
                              >
                                {CATEGORIES.map((cat) => (
                                  <option key={cat.value} value={cat.value}>
                                    {cat.label}
                                  </option>
                                ))}
                              </select>

                              <select
                                value={example.difficulty}
                                onChange={(e) =>
                                  updateBatchExample(idx, 'difficulty', e.target.value)
                                }
                                className="px-3 py-2 bg-slate-800 border border-slate-500 rounded text-white text-sm"
                              >
                                {DIFFICULTIES.map((diff) => (
                                  <option key={diff.value} value={diff.value}>
                                    {diff.label}
                                  </option>
                                ))}
                              </select>
                            </div>
                          </Card>
                        ))}
                      </div>
                    </ScrollArea>

                    <Button
                      type="button"
                      variant="outline"
                      onClick={addBatchExample}
                      className="w-full border-slate-600 text-slate-300 hover:bg-slate-700"
                    >
                      + Add Example
                    </Button>
                  </div>

                  <Button
                    type="submit"
                    disabled={loading}
                    className="w-full bg-amber-500 hover:bg-amber-600 text-black font-semibold py-3"
                  >
                    {loading ? (
                      <>
                        <Loader2 className="mr-2 animate-spin" size={18} />
                        Submitting...
                      </>
                    ) : (
                      <>
                        <Upload className="mr-2" size={18} />
                        Submit Batch ({batchExamples.filter((ex) => ex.instruction && ex.output).length} valid)
                      </>
                    )}
                  </Button>
                </form>
              </Card>
            )}
          </div>

          {/* Right Column - Stats & Recent Submissions */}
          <div className="space-y-6">
            {/* Queue Status */}
            <Card className="bg-gradient-to-br from-slate-800 to-slate-900 border-slate-700 p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                  <BarChart3 className="text-amber-400" size={20} />
                  Queue Status
                </h3>
                {loading && <Loader2 className="animate-spin text-amber-400" size={18} />}
              </div>

              {queueStatus ? (
                <div className="space-y-3">
                  <div className="flex justify-between items-center py-2 border-b border-slate-700">
                    <span className="text-slate-400">Total</span>
                    <Badge className="bg-slate-700 text-slate-200">{queueStatus.total_submissions}</Badge>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-700">
                    <span className="text-slate-400">Pending</span>
                    <Badge className="bg-yellow-500/20 text-yellow-300">{queueStatus.pending}</Badge>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-700">
                    <span className="text-slate-400">Processing</span>
                    <Badge className="bg-blue-500/20 text-blue-300">{queueStatus.processing}</Badge>
                  </div>
                  <div className="flex justify-between items-center py-2 border-b border-slate-700">
                    <span className="text-slate-400">Completed</span>
                    <Badge className="bg-green-500/20 text-green-300">{queueStatus.completed}</Badge>
                  </div>
                  <div className="flex justify-between items-center py-2">
                    <span className="text-slate-400">Failed</span>
                    <Badge className="bg-red-500/20 text-red-300">{queueStatus.failed}</Badge>
                  </div>
                </div>
              ) : (
                <div className="space-y-2">
                  <Skeleton className="h-6 bg-slate-700" />
                  <Skeleton className="h-6 bg-slate-700" />
                  <Skeleton className="h-6 bg-slate-700" />
                </div>
              )}
            </Card>

            {/* Instructions */}
            <Card className="bg-slate-800/30 border-slate-700 p-6">
              <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                <BookOpen className="text-blue-400" size={20} />
                Guidelines
              </h3>
              <ul className="space-y-3 text-sm text-slate-400">
                <li className="flex gap-2">
                  <span className="text-amber-400 font-bold">→</span>
                  <span>Keep instructions clear and specific</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-amber-400 font-bold">→</span>
                  <span>Provide detailed, accurate outputs</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-amber-400 font-bold">→</span>
                  <span>Use appropriate categories for better organization</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-amber-400 font-bold">→</span>
                  <span>Set realistic difficulty levels</span>
                </li>
                <li className="flex gap-2">
                  <span className="text-amber-400 font-bold">→</span>
                  <span>Batch submissions (1-1000) are supported</span>
                </li>
              </ul>
            </Card>

            {/* Recent Submissions */}
            {submissions.length > 0 && (
              <Card className="bg-slate-800/30 border-slate-700 p-6">
                <h3 className="text-lg font-semibold text-white mb-4">Recent Submissions</h3>
                <div className="space-y-3">
                  {submissions.slice(0, 3).map((submission) => (
                    <div
                      key={submission.submission_id}
                      className="p-3 bg-slate-900/50 rounded-lg border border-slate-700"
                    >
                      <div className="flex items-start justify-between mb-1">
                        <span className="font-mono text-xs text-amber-400">
                          {submission.submission_id}
                        </span>
                        <Badge className="bg-green-500/20 text-green-300 text-xs">
                          {submission.count}
                        </Badge>
                      </div>
                      <p className="text-xs text-slate-400">
                        {new Date(submission.timestamp).toLocaleTimeString()}
                      </p>
                    </div>
                  ))}
                </div>
              </Card>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
