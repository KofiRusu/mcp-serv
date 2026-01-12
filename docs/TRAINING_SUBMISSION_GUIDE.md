# 📚 Training Submission Guide for Mac Users

## 🎯 Overview

Mac users can now submit training examples and exercises directly to ChatOS-v2.0 running on Docker. Your submissions are automatically:
- ✅ Saved to the training queue
- ✅ Merged with existing training data
- ✅ Included in the next PersRM training epoch
- ✅ Incorporated into model learning

## 🚀 Quick Start

### 1. Start ChatOS on Mac

```bash
cd ChatOS-v2.0
docker-compose up -d chatos
```

The API will be available at: `http://localhost:8000`

### 2. Check API Health

```bash
curl http://localhost:8000/api/training/health
```

Expected response:
```json
{
  "status": "healthy",
  "submissions_dir_exists": true,
  "training_data_dir_exists": true
}
```

## 📤 Submitting Training Examples

### Single Example

Submit one training example:

```bash
curl -X POST http://localhost:8000/api/training/submit-example \
  -H "Content-Type: application/json" \
  -d '{
    "instruction": "What is the RSI indicator and how to use it in trading?",
    "output": "The Relative Strength Index (RSI) is a momentum oscillator that measures the speed and change of price movements on a scale of 0-100. Values above 70 indicate overbought conditions, below 30 indicate oversold. Traders use it to identify potential reversal points.",
    "category": "trading",
    "difficulty": "medium",
    "source": "mac-user-submission"
  }'
```

**Parameters:**
- `instruction` (required): User question or task
- `output` (required): Expected answer or solution
- `category` (optional): trading, investing, risk, crypto, general
- `difficulty` (optional): easy, medium, hard, expert
- `source` (optional): Where this came from
- `notes` (optional): Additional context

**Response:**
```json
{
  "success": true,
  "submission_id": "a1b2c3d4",
  "message": "Example submitted successfully. Will be included in next training epoch.",
  "status_url": "/api/training/status/a1b2c3d4"
}
```

### Batch Submission

Submit multiple examples at once:

```bash
curl -X POST http://localhost:8000/api/training/submit-batch \
  -H "Content-Type: application/json" \
  -d '{
    "batch_name": "crypto-strategies-mac-batch-1",
    "description": "Crypto trading strategies with historical examples",
    "examples": [
      {
        "instruction": "Explain a momentum trading strategy for crypto",
        "output": "Momentum strategy: Buy when price breaks above 50-day MA with volume, sell when RSI > 70. Target 5-15% gains, stop loss at entry -3%.",
        "category": "crypto",
        "difficulty": "medium"
      },
      {
        "instruction": "What is mean reversion trading?",
        "output": "Mean reversion assumes prices revert to average. Buy when price drops 2σ below MA, sell at MA. Works in ranging markets, fails in trends.",
        "category": "trading",
        "difficulty": "hard"
      },
      {
        "instruction": "How to manage risk in crypto trading?",
        "output": "Use position sizing: 1-2% risk per trade. Set stop losses. Diversify across uncorrelated assets. Use DCA for accumulation.",
        "category": "risk",
        "difficulty": "easy"
      }
    ]
  }'
```

**Response:**
```json
{
  "success": true,
  "submission_id": "x9y8z7w6",
  "batch_name": "crypto-strategies-mac-batch-1",
  "example_count": 3,
  "message": "Batch of 3 examples submitted successfully",
  "status_url": "/api/training/status/x9y8z7w6"
}
```

### Training Exercises

Submit exercises that users should complete:

```bash
curl -X POST http://localhost:8000/api/training/submit-exercise \
  -H "Content-Type: application/json" \
  -d '{
    "problem": "You have $10,000 and want to trade BTC. Design a trading plan including entry, exit, and risk management.",
    "expected_outcome": "Entry: Buy at support levels with RSI < 30. Exit: Sell at resistance or 5% profit. Risk: 2% per trade ($200 stop loss). Position size: $2,000-3,000 per trade to limit risk exposure.",
    "hints": [
      "Think about entry signals",
      "Define take-profit levels",
      "Calculate position size from risk"
    ],
    "category": "trading",
    "difficulty": "hard"
  }'
```

### Upload JSONL File

Submit multiple examples via file upload:

```bash
# Create a JSONL file
cat > training_batch.jsonl << 'EOF'
{"instruction": "What is Bitcoin?", "output": "Bitcoin is a decentralized digital currency created in 2009. It uses blockchain technology and proof-of-work consensus.", "metadata": {"category": "crypto"}}
{"instruction": "Explain Ethereum", "output": "Ethereum is a blockchain platform enabling smart contracts. It uses PoS consensus (after merge) and has virtual machine (EVM).", "metadata": {"category": "crypto"}}
{"instruction": "What are NFTs?", "output": "NFTs (non-fungible tokens) are unique digital assets on blockchain with ownership proof. Used for art, collectibles, gaming.", "metadata": {"category": "crypto"}}
EOF

# Upload the file
curl -X POST http://localhost:8000/api/training/submit-file \
  -F "file=@training_batch.jsonl" \
  -F "batch_name=crypto-basics-batch"
```

**JSONL Format (required fields):**
```json
{"instruction": "question", "output": "answer", "metadata": {"optional": "data"}}
```

## 📊 Checking Status

### Single Submission Status

```bash
curl http://localhost:8000/api/training/status/a1b2c3d4
```

Response:
```json
{
  "submission_id": "a1b2c3d4",
  "status": "received",
  "file": "a1b2c3d4_single-example.jsonl",
  "example_count": 1,
  "created_at": "2025-12-05T15:30:45.123456"
}
```

### Training Queue Status

```bash
curl http://localhost:8000/api/training/queue/status
```

Response:
```json
{
  "training_examples": 2742,
  "validation_examples": 305,
  "total_queued": 3047,
  "pending_submissions": 5,
  "submission_dir": "/home/user/ChatOS-v2.0/data/persrm/submissions",
  "training_data_dir": "/home/user/ChatOS-v2.0/data/persrm"
}
```

## 🔄 Automatic Merging

Submissions are automatically merged into training data when:
1. You submit examples (automatic background task)
2. You manually trigger merge

### Manual Merge

Force merge all submissions into training data:

```bash
curl -X POST http://localhost:8000/api/training/merge-submissions
```

Response:
```json
{
  "success": true,
  "message": "Submissions merged into training data",
  "train_examples": 2745,
  "val_examples": 310,
  "total": 3055
}
```

## 💻 Python Script Example

Submit examples programmatically:

```python
import requests
import json

BASE_URL = "http://localhost:8000/api/training"

# Single example
example = {
    "instruction": "What is a candlestick chart?",
    "output": "A candlestick chart shows open, high, low, close prices. Green = price up, red = price down. Used in technical analysis.",
    "category": "trading",
    "difficulty": "easy"
}

response = requests.post(f"{BASE_URL}/submit-example", json=example)
print(response.json())

# Batch submission
batch = {
    "batch_name": "technical-analysis-batch",
    "description": "Technical analysis indicators",
    "examples": [
        {
            "instruction": "Explain MACD indicator",
            "output": "MACD (Moving Average Convergence Divergence) shows momentum. Two lines: MACD line (12-26 MA) and signal (9-day MA). Crossovers signal buy/sell.",
            "category": "trading",
            "difficulty": "medium"
        }
    ]
}

response = requests.post(f"{BASE_URL}/submit-batch", json=batch)
print(response.json())

# Check queue status
response = requests.get(f"{BASE_URL}/queue/status")
print(json.dumps(response.json(), indent=2))
```

## 🐳 Docker Integration

### Check Training Status

```bash
# From your Mac terminal
docker exec -it chatos-server ./bin/trading persrm status
```

### View Training Logs

```bash
docker logs chatos-server
```

### Access Container Shell

```bash
docker exec -it chatos-server bash
```

## 📋 Categories

Valid categories for submissions:

| Category | Description |
|----------|-------------|
| `trading` | Trading strategies, technical analysis |
| `investing` | Investment strategies, portfolio management |
| `risk` | Risk management, position sizing |
| `crypto` | Cryptocurrency specific topics |
| `general` | General finance/ML knowledge |

## 🎚️ Difficulty Levels

| Level | Description |
|-------|-------------|
| `easy` | Basic concepts, definitions |
| `medium` | Intermediate strategies, concepts |
| `hard` | Advanced strategies, complex scenarios |
| `expert` | Cutting-edge research, novel approaches |

## 🔍 Best Practices

### Quality Guidelines

1. **Clear Instruction**: Make the question specific and unambiguous
   - ❌ "Tell me about trading"
   - ✅ "Explain the RSI indicator and how to use it for mean reversion trading"

2. **Accurate Output**: Provide correct, actionable answers
   - ❌ "Trading is complicated"
   - ✅ "RSI > 70 suggests overbought; < 30 suggests oversold. Use with other signals."

3. **Metadata**: Provide context where helpful
   - Include domain, difficulty, source
   - Add notes about edge cases or limitations

4. **Batch Organization**: Group related examples
   - Don't mix crypto and forex strategies in one batch
   - Name batches descriptively

### Examples to Submit

Great candidates for submissions:
- ✅ Specific trading rules you've developed
- ✅ Market analysis frameworks
- ✅ Risk management approaches
- ✅ Cryptocurrency strategy examples
- ✅ Investment decision criteria
- ✅ Pattern recognition rules
- ✅ Common market scenarios and solutions

Avoid:
- ❌ Vague or subjective content
- ❌ Duplicates of existing examples
- ❌ Unvalidated/speculative strategies
- ❌ Very similar variations without distinction

## 🚨 Troubleshooting

### "Connection refused"
```bash
# Make sure Docker is running
docker ps

# Check if ChatOS container is running
docker ps | grep chatos

# Start if not running
docker-compose up -d chatos
```

### "Invalid JSONL format"
```bash
# Validate your JSONL file
python3 -c "
import json
with open('training_batch.jsonl') as f:
    for i, line in enumerate(f, 1):
        try:
            json.loads(line)
        except:
            print(f'Line {i}: Invalid JSON')
"
```

### "Missing required fields"
Ensure each JSON object has:
- `instruction` (string, required)
- `output` (string, required)
- `metadata` (optional dict)

### Check Available Endpoints

```bash
curl http://localhost:8000/docs
```

This opens interactive API documentation where you can test endpoints.

## 📈 Impact on Training

Each submission:
- ✅ Increases model's understanding of trading domain
- ✅ Improves accuracy on crypto/trading queries
- ✅ Adds specialized knowledge to PersRM
- ✅ Contributes to next training epoch

**Current Status:**
- Total training examples: 2,742
- Each new batch: 1-1000 examples
- Training cycles: 10 epochs

## 🔗 Related Commands

```bash
# Start Docker services
docker-compose up -d

# Stop services
docker-compose down

# View logs
docker-compose logs -f chatos

# Check training progress
docker exec chatos-server ./bin/trading persrm status

# Merge submissions manually
docker exec chatos-server python -c "from ChatOS.api.routes_training_submission import merge_submissions_to_training; print(merge_submissions_to_training())"
```

## 📞 Support

For issues:
1. Check Docker is running: `docker ps`
2. Verify API health: `curl http://localhost:8000/api/training/health`
3. Check container logs: `docker-compose logs chatos`
4. Review submission format in `/api/training/docs`

---

**Ready to submit your training examples!** 🚀

