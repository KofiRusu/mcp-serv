# 🚀 ChatOS Training Submission UI

> **Complete web interface for submitting training examples to ChatOS PersRM model**

## Overview

The Training Submission UI is a modern, beautiful web interface that allows users to:
- ✅ Submit individual training examples
- ✅ Create and submit batches of examples (1-1000)
- ✅ Track submission status in real-time
- ✅ Monitor training queue progress
- ✅ View statistics and guidelines

Built with **Next.js 16**, **React 19**, **Tailwind CSS**, and **Radix UI** for a premium user experience.

---

## 🎯 Quick Start

### Prerequisites
- Node.js 18+ and npm
- Training API running on `http://localhost:8000`

### Setup

```bash
# 1. Install dependencies
cd ChatOS-v2.0/sandbox-ui
npm install

# 2. Start development server
npm run dev

# 3. Open in browser
open http://localhost:3000/training
```

---

## 📱 Features

### 1. Single Example Submission
**Path:** `/training` → "Single Example" tab

Submit one training example at a time:

```bash
# Example via cURL
curl -X POST http://localhost:8000/api/training/submit-example \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "What is the RSI indicator?",
    "output": "RSI measures momentum on a 0-100 scale...",
    "category": "trading",
    "difficulty": "easy"
  }'
```

**Form Fields:**
- **Instruction/Question**: Your question or prompt
- **Output/Answer**: Detailed response or solution
- **Category**: Trading, Investing, Risk, Crypto, General
- **Difficulty**: Easy, Medium, Hard, Expert

### 2. Batch Submission
**Path:** `/training` → "Batch Submit" tab

Submit multiple examples together (up to 1,000):

```bash
# Example via cURL
curl -X POST http://localhost:8000/api/training/submit-batch \
  -H "Content-Type: application/json" \
  -d '{
    "batch_name": "advanced-strategies",
    "description": "Trading strategies I learned",
    "examples": [
      {
        "instruction": "What is RSI?",
        "output": "RSI measures...",
        "category": "trading",
        "difficulty": "easy"
      },
      {
        "instruction": "What is MACD?",
        "output": "MACD is a momentum indicator...",
        "category": "trading",
        "difficulty": "medium"
      }
    ]
  }'
```

**Benefits:**
- Faster processing
- Grouped by topic/category
- Easier to organize related examples
- Better for importing from external sources

### 3. Real-Time Queue Monitoring
**Stats Panel (Right Sidebar)**

Track submissions in real-time:
- **Total Submissions**: Total examples submitted
- **Pending**: Awaiting processing
- **Processing**: Currently being merged
- **Completed**: Successfully added to training data
- **Failed**: Errors during processing

Refresh stats with the "Refresh Stats" button.

### 4. Submission History
**Recent Submissions Panel**

View your 3 most recent submissions with:
- Unique submission ID
- Number of examples
- Timestamp

---

## 📊 API Endpoints Used

The UI communicates with these endpoints:

```
POST   /api/training/submit-example      Submit single example
POST   /api/training/submit-batch        Submit batch (1-1000)
GET    /api/training/status/{id}         Check submission status
GET    /api/training/queue/status        Get queue statistics
GET    /api/training/health              Health check
```

All endpoints are prefixed with: `http://localhost:8000/api/training`

---

## 🎨 UI Components

### Dark Theme
- **Background**: Gradient from slate-950 → slate-800
- **Primary Color**: Amber (#FBBF24)
- **Accents**: Blue, Green, Red for status indicators
- **Font**: Outfit (headings), system fonts (body)

### Responsive Design
- **Desktop**: 3-column layout (form, stats, history)
- **Tablet**: 2-column layout
- **Mobile**: Single column (form, then stats below)

### Interactive Elements
- **Tabs**: Smooth switching between submission modes
- **Alerts**: Success/error messages with icons
- **Cards**: Grouped information sections
- **Buttons**: Clear call-to-action with loading states
- **Forms**: Auto-save, validation, helpful placeholders

---

## 📚 Example Workflows

### Workflow 1: Quick Single Example
```
1. Navigate to /training
2. Enter instruction (question)
3. Enter output (answer)
4. Select category (default: trading)
5. Select difficulty (default: medium)
6. Click "Submit Example"
7. See success message with submission ID
```

### Workflow 2: Bulk Training Data
```
1. Prepare 100 Q&A pairs in JSON format
2. Click "Batch Submit" tab
3. Enter batch name and description
4. Click "+ Add Example" 99 times (or paste/script)
5. Review all examples in scrollable list
6. Click "Submit Batch"
7. Check queue status to monitor processing
```

### Workflow 3: Continuous Improvement
```
1. Analyze training results
2. Identify gaps in model knowledge
3. Create new examples targeting those gaps
4. Submit as single or batch
5. Wait for next training epoch
6. Evaluate improved predictions
7. Repeat with new findings
```

---

## 🔧 Configuration

### API Base URL
Edit in `/sandbox-ui/src/app/training/page.tsx`:
```typescript
const API_BASE = 'http://localhost:8000/api/training';
```

### Categories
Customizable categories in the same file:
```typescript
const CATEGORIES = [
  { value: 'trading', label: '📈 Trading' },
  { value: 'investing', label: '💼 Investing' },
  { value: 'risk', label: '⚠️ Risk Management' },
  { value: 'crypto', label: '₿ Cryptocurrency' },
  { value: 'general', label: '🎓 General' },
];
```

### Difficulty Levels
```typescript
const DIFFICULTIES = [
  { value: 'easy', label: 'Easy' },
  { value: 'medium', label: 'Medium' },
  { value: 'hard', label: 'Hard' },
  { value: 'expert', label: 'Expert' },
];
```

---

## 💡 Best Practices

### For Training Examples

1. **Be Specific**
   - ❌ Bad: "What is trading?"
   - ✅ Good: "Explain the difference between limit orders and market orders"

2. **Provide Complete Answers**
   - ❌ Bad: "RSI is an indicator"
   - ✅ Good: "RSI (Relative Strength Index) measures momentum between 0-100. Values > 70 indicate overbought (potential sell), < 30 indicate oversold (potential buy). Calculated using price change smoothing..."

3. **Use Accurate Categories**
   - Trading: Technical analysis, strategy execution
   - Investing: Portfolio management, asset allocation
   - Risk: Position sizing, stop losses, risk/reward
   - Crypto: Blockchain, DeFi, crypto-specific topics
   - General: Finance fundamentals, ML concepts

4. **Set Realistic Difficulty**
   - Easy: Basic definitions, simple concepts
   - Medium: Intermediate strategies, common patterns
   - Hard: Advanced techniques, complex scenarios
   - Expert: Cutting-edge research, novel approaches

### For Batch Submissions

1. **Group Related Topics**
   ```json
   {
     "batch_name": "fibonacci-retracements",
     "examples": [
       {"instruction": "What is Fibonacci?", ...},
       {"instruction": "How to use in trading?", ...},
       {"instruction": "Common levels?", ...}
     ]
   }
   ```

2. **Add Descriptive Batch Names**
   - ✅ "bollinger-bands-strategies"
   - ✅ "crypto-market-cycles"
   - ❌ "batch1", "examples"

3. **Keep Examples Independent**
   - Each example should work standalone
   - Don't assume context from previous examples

---

## 🚀 Deployment

### Development
```bash
npm run dev
# Runs on http://localhost:3000
```

### Production Build
```bash
npm run build
npm start
# Optimized build for deployment
```

### Docker (Future)
```bash
docker build -t chatos-ui .
docker run -p 3000:3000 chatos-ui
```

---

## 📊 Data Flow

```
┌─────────────────────────────────────────────────────────┐
│  User submits example/batch in UI                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Validation in form (client-side)                       │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  POST to /api/training/submit-example OR -batch         │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  API validates & saves to /data/persrm/submissions/     │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Background task merges into train_final.jsonl          │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Next training epoch includes new examples              │
└──────────────────┬──────────────────────────────────────┘
                   │
                   ▼
┌─────────────────────────────────────────────────────────┐
│  Model learns patterns → Improves predictions           │
└─────────────────────────────────────────────────────────┘
```

---

## 🐛 Troubleshooting

### "API Error: Network error"
- **Check**: Is `http://localhost:8000/api/training/health` accessible?
- **Fix**: Start the training API server

### "Failed to submit example"
- **Check**: Are instruction and output fields filled?
- **Check**: Is the batch size < 1000?
- **Fix**: Review error message in alert

### Stats not updating
- **Click**: "Refresh Stats" button
- **Check**: Background task may still be processing

### Slow submissions
- **Note**: First submission merges data (slower)
- **Note**: Large batches take longer to process
- **Tip**: Start with single examples, then batch

---

## 📈 Monitoring

### Check Current Training Status
```bash
curl http://localhost:8000/api/training/health | jq .
```

### View Submissions Directory
```bash
ls -lh ~/ChatOS-v2.0/data/persrm/submissions/
```

### Monitor Training Data Growth
```bash
# Count training examples
wc -l ~/ChatOS-v2.0/data/persrm/train_final.jsonl
wc -l ~/ChatOS-v2.0/data/persrm/val_final.jsonl
```

---

## 🔐 Security Notes

- **CORS Enabled**: Accepts requests from any origin (development)
- **No Authentication**: Currently open for local use
- **Data Storage**: Examples saved as JSONL files
- **Validation**: Server-side validation on all inputs

For production deployment, add:
- API key authentication
- Rate limiting
- CORS restrictions
- Input sanitization

---

## 📝 License

Part of ChatOS v2.0 - AI Training Framework

---

## 🤝 Contributing

To improve the training UI:

1. **Bug Reports**: Check `/tmp/api_server.log`
2. **Feature Requests**: Submit to GitHub issues
3. **Improvements**: Create pull requests

---

## 📞 Support

For issues or questions:
- Check logs: `tail -f /tmp/api_server.log`
- Review API docs: `http://localhost:8000/docs`
- Check health: `http://localhost:8000/api/training/health`

---

**Made with ❤️ for better AI training workflows** 🚀

