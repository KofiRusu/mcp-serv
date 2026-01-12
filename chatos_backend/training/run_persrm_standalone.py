#!/usr/bin/env python3
"""
run_persrm_standalone.py - Run PersRM Standalone Model Training

This script ties together the entire pipeline:
1. Generate/collect training data
2. Configure training job
3. Start Unsloth fine-tuning

Usage:
    # Generate data and start training
    python -m ChatOS.training.run_persrm_standalone --train
    
    # Just generate data (no training)
    python -m ChatOS.training.run_persrm_standalone --generate-only
    
    # Check current data stats
    python -m ChatOS.training.run_persrm_standalone --stats
"""

import argparse
import asyncio
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional

# Add parent to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from chatos_backend.config.settings import settings
from chatos_backend.training.persrm_standalone_generator import (
    PersRMStandaloneGenerator,
    generate_persrm_standalone_dataset,
    get_training_data_stats,
)
from chatos_backend.training.job_spec import TrainingJobSpec
from chatos_backend.training.unsloth_runner import write_temp_config, start_training_process
from chatos_backend.training import job_store


def print_header(title: str):
    """Print a formatted header."""
    print("\n" + "=" * 60)
    print(f"  {title}")
    print("=" * 60 + "\n")


def print_stats(stats: Dict[str, Any]):
    """Print formatted statistics."""
    print(f"  ChatOS Logs:      {stats.get('chatlog_examples', 0):>6} examples")
    print(f"  PersRM Data:      {stats.get('persrm_examples', 0):>6} examples")
    print(f"  Total Available:  {stats.get('total_examples', 0):>6} examples")
    print(f"  Minimum Required: {stats.get('minimum_required', 100):>6}")
    print(f"  Recommended:      {stats.get('recommended', 1000):>6}")
    print()
    
    if stats.get('ready_for_training'):
        print("  ✓ Ready for training!")
    else:
        print("  ✗ Need more data before training")
        print(f"    Collect {stats['minimum_required'] - stats['total_examples']} more examples")


def generate_data(output_dir: Optional[Path] = None) -> Dict[str, Any]:
    """Generate training data from all sources."""
    print_header("Generating PersRM Standalone Training Data")
    
    result = generate_persrm_standalone_dataset(
        output_dir=output_dir,
        min_quality=0.5,
        eval_ratio=0.1,
    )
    
    print("\nGeneration complete!")
    print(f"  Train set: {result['stats'].train_count} examples")
    print(f"  Eval set:  {result['stats'].eval_count} examples")
    print(f"\nFiles written to: {result['paths']['train'].parent}")
    
    return result


def copy_data_to_unsloth(result: Dict[str, Any]) -> Dict[str, Path]:
    """Copy generated data to Unsloth datasets directory."""
    print("\nCopying to Unsloth datasets directory...")
    
    unsloth_datasets = settings.unsloth_datasets_dir
    unsloth_datasets.mkdir(parents=True, exist_ok=True)
    
    # Copy train file
    train_src = result['paths']['train']
    train_dst = unsloth_datasets / "persrm_standalone_train_latest.jsonl"
    shutil.copy2(train_src, train_dst)
    
    # Copy eval file
    eval_src = result['paths']['eval']
    eval_dst = unsloth_datasets / "persrm_standalone_eval_latest.jsonl"
    shutil.copy2(eval_src, eval_dst)
    
    print(f"  ✓ Copied to {unsloth_datasets}")
    
    return {
        "train": train_dst,
        "eval": eval_dst,
    }


def start_training(
    train_path: Path,
    eval_path: Path,
    preset: str = "STANDALONE",
    model: str = "mistral-7b",
) -> str:
    """Start the training job."""
    print_header("Starting PersRM Standalone Training")
    
    # Create job specification
    job_spec = TrainingJobSpec.for_persrm_standalone(
        train_path=str(train_path),
        eval_path=str(eval_path),
        preset_name=preset,
        model_key=model,
        description=f"PersRM Standalone Training - {datetime.now().strftime('%Y-%m-%d %H:%M')}",
    )
    
    print(f"Job ID: {job_spec.id}")
    print(f"Model:  {job_spec.base_model_name}")
    print(f"Preset: {job_spec.preset_name}")
    print(f"Epochs: {job_spec.num_epochs}")
    print(f"LoRA r: {job_spec.lora_r}")
    print()
    
    # Generate config file
    config_path = write_temp_config(job_spec)
    print(f"Config written to: {config_path}")
    
    # Start training process
    print("\nStarting training process...")
    print("⚠️  REQUIRES GPU - Training will fail without CUDA")
    print()
    
    try:
        pid, log_path = start_training_process(job_spec, config_path)
        
        print(f"  ✓ Training started!")
        print(f"  Process ID: {pid}")
        print(f"  Log file:   {log_path}")
        print()
        print("Monitor progress with:")
        print(f"  tail -f {log_path}")
        print()
        print("Or in ChatOS Training Lab UI")
        
        return job_spec.id
        
    except Exception as e:
        print(f"  ✗ Failed to start training: {e}")
        print()
        print("Make sure:")
        print("  1. NVIDIA GPU is available")
        print("  2. Unsloth environment is set up")
        print("  3. CUDA drivers are installed")
        return ""


def main():
    parser = argparse.ArgumentParser(
        description="PersRM Standalone Model Training Pipeline",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Check available training data
  python -m ChatOS.training.run_persrm_standalone --stats
  
  # Generate training data only
  python -m ChatOS.training.run_persrm_standalone --generate-only
  
  # Generate data and start training
  python -m ChatOS.training.run_persrm_standalone --train
  
  # Start training with existing data
  python -m ChatOS.training.run_persrm_standalone --train --skip-generate
        """
    )
    
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show training data statistics and exit",
    )
    parser.add_argument(
        "--generate-only",
        action="store_true",
        help="Generate training data without starting training",
    )
    parser.add_argument(
        "--train",
        action="store_true",
        help="Start training (generates data first unless --skip-generate)",
    )
    parser.add_argument(
        "--skip-generate",
        action="store_true",
        help="Skip data generation, use existing data",
    )
    parser.add_argument(
        "--preset",
        type=str,
        default="STANDALONE",
        choices=["FAST", "REASONING", "QUALITY", "STANDALONE"],
        help="Training preset (default: STANDALONE)",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="mistral-7b",
        help="Model to train (default: mistral-7b)",
    )
    
    args = parser.parse_args()
    
    # Default action if none specified
    if not args.stats and not args.generate_only and not args.train:
        args.stats = True
    
    if args.stats:
        print_header("PersRM Standalone Training Data Statistics")
        stats = get_training_data_stats()
        print_stats(stats)
        return 0
    
    if args.generate_only or (args.train and not args.skip_generate):
        result = generate_data()
        paths = copy_data_to_unsloth(result)
        
        if args.generate_only:
            print("\nData generation complete. Ready for training.")
            print(f"Run with --train to start training.")
            return 0
    
    if args.train:
        if args.skip_generate:
            # Use existing data
            unsloth_datasets = settings.unsloth_datasets_dir
            paths = {
                "train": unsloth_datasets / "persrm_standalone_train_latest.jsonl",
                "eval": unsloth_datasets / "persrm_standalone_eval_latest.jsonl",
            }
            
            if not paths["train"].exists():
                print("Error: No existing training data found.")
                print("Run without --skip-generate to generate data first.")
                return 1
        
        job_id = start_training(
            train_path=paths["train"],
            eval_path=paths["eval"],
            preset=args.preset,
            model=args.model,
        )
        
        return 0 if job_id else 1
    
    return 0


if __name__ == "__main__":
    sys.exit(main())

