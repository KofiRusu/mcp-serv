#!/usr/bin/env python3
"""
Continuous Crypto Backtesting Loop
===================================

Runs backtesting continuously and generates training data
for PersRM model improvement over time.
"""

import time
import json
from datetime import datetime
from pathlib import Path
from crypto_backtest_trainer import run_continuous_backtesting

HOME = Path.home()
LOG_DIR = HOME / "ChatOS-v0.2" / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

LOG_FILE = LOG_DIR / "backtest_continuous.log"


def log_message(msg):
    """Log message to file."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_entry = f"[{timestamp}] {msg}"
    print(log_entry)
    
    with open(LOG_FILE, 'a') as f:
        f.write(log_entry + "\n")


def main():
    """Run continuous backtesting loop."""
    
    log_message("="*60)
    log_message("Starting Continuous Crypto Backtesting Loop")
    log_message("="*60)
    
    cycle = 0
    
    while True:
        cycle += 1
        log_message(f"\n📊 CYCLE {cycle} - {datetime.now().strftime('%H:%M:%S')}")
        
        try:
            # Run backtesting
            examples = run_continuous_backtesting(num_runs=3)
            
            log_message(f"✅ Cycle {cycle}: Generated {len(examples)} training examples")
            
            # Sleep before next cycle
            log_message(f"⏳ Waiting 300 seconds before next cycle...")
            time.sleep(300)  # 5 minutes between cycles
            
        except Exception as e:
            log_message(f"❌ Error in cycle {cycle}: {str(e)}")
            time.sleep(60)  # Wait before retry


if __name__ == "__main__":
    main()

