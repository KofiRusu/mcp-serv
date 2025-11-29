"""
Tests for ChatOS.training.monitor module.
"""

import json
import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestMonitor:
    """Test cases for the monitoring module."""
    
    @pytest.fixture
    def temp_output_dir(self):
        """Create a temporary output directory with metrics."""
        with tempfile.TemporaryDirectory() as tmpdir:
            output_dir = Path(tmpdir)
            
            # Create metrics file
            metrics_path = output_dir / "metrics.jsonl"
            metrics = [
                {"job_id": "test_001", "event": "job_started", "model_name": "test/model"},
                {"job_id": "test_001", "step": 10, "train_loss": 2.5},
                {"job_id": "test_001", "step": 20, "train_loss": 2.0},
                {"job_id": "test_001", "step": 30, "train_loss": 1.5, "eval_loss": 1.8},
            ]
            with open(metrics_path, "w") as f:
                for m in metrics:
                    f.write(json.dumps(m) + "\n")
            
            yield output_dir
    
    @pytest.fixture
    def temp_log_dir(self):
        """Create a temporary directory with log files."""
        with tempfile.TemporaryDirectory() as tmpdir:
            log_dir = Path(tmpdir)
            
            # Create a log file with error
            log_path = log_dir / "error.log"
            log_path.write_text("""
Starting training...
Loading model...
Step 10: loss=2.5
ERROR: CUDA out of memory
Traceback (most recent call last):
  File "train.py", line 100
RuntimeError: CUDA out of memory
""")
            
            # Create a log file without error
            ok_log = log_dir / "ok.log"
            ok_log.write_text("""
Starting training...
Loading model...
Step 10: loss=2.5
Step 20: loss=2.0
Training complete!
""")
            
            yield log_dir
    
    def test_is_process_alive_current_process(self):
        """Test is_process_alive with current process."""
        from ChatOS.training.monitor import is_process_alive
        
        # Current process should be alive
        assert is_process_alive(os.getpid()) is True
        
        # Invalid PID
        assert is_process_alive(-1) is False
        assert is_process_alive(0) is False
    
    def test_read_latest_metrics(self, temp_output_dir):
        """Test reading latest metrics."""
        from ChatOS.training.monitor import read_latest_metrics
        
        metrics = read_latest_metrics(str(temp_output_dir))
        
        assert metrics is not None
        assert metrics["step"] == 30
        assert metrics["train_loss"] == 1.5
    
    def test_read_latest_metrics_empty(self, tmp_path):
        """Test reading metrics from non-existent file."""
        from ChatOS.training.monitor import read_latest_metrics
        
        metrics = read_latest_metrics(str(tmp_path))
        assert metrics is None
    
    def test_read_all_metrics(self, temp_output_dir):
        """Test reading all metrics."""
        from ChatOS.training.monitor import read_all_metrics
        
        metrics = read_all_metrics(str(temp_output_dir))
        
        assert len(metrics) == 4
        assert metrics[0]["event"] == "job_started"
    
    def test_get_training_metrics_summary(self, temp_output_dir):
        """Test getting metrics summary."""
        from ChatOS.training.monitor import get_training_metrics_summary
        
        summary = get_training_metrics_summary(str(temp_output_dir))
        
        assert summary["has_metrics"] is True
        assert summary["latest_train_loss"] == 1.5
        assert summary["min_train_loss"] == 1.5
        assert len(summary["train_loss_history"]) > 0
    
    def test_read_log_tail(self, temp_log_dir):
        """Test reading log tail."""
        from ChatOS.training.monitor import read_log_tail
        
        log_path = temp_log_dir / "ok.log"
        lines = read_log_tail(str(log_path), lines=3)
        
        assert len(lines) == 3
        assert "Training complete" in lines[-1]
    
    def test_check_log_for_errors_with_error(self, temp_log_dir):
        """Test error detection in logs."""
        from ChatOS.training.monitor import check_log_for_errors
        
        log_path = temp_log_dir / "error.log"
        error = check_log_for_errors(str(log_path))
        
        assert error is not None
        assert "CUDA" in error or "out of memory" in error
    
    def test_check_log_for_errors_no_error(self, temp_log_dir):
        """Test no error detection in clean logs."""
        from ChatOS.training.monitor import check_log_for_errors
        
        log_path = temp_log_dir / "ok.log"
        error = check_log_for_errors(str(log_path))
        
        # Should return last lines as context
        assert error is not None  # Returns context if no explicit error


class TestMetricsHistory:
    """Test cases for metrics history handling."""
    
    @pytest.fixture
    def metrics_with_history(self, tmp_path):
        """Create metrics with loss history."""
        output_dir = tmp_path
        metrics_path = output_dir / "metrics.jsonl"
        
        metrics = []
        for i in range(50):
            metrics.append({
                "job_id": "test_001",
                "step": i * 10,
                "train_loss": 3.0 - (i * 0.05),  # Decreasing loss
            })
        
        # Add eval metrics
        for i in range(0, 50, 5):
            metrics[i]["eval_loss"] = 3.2 - (i * 0.05)
        
        # Add finish event
        metrics.append({
            "job_id": "test_001",
            "event": "job_finished",
            "status": "completed",
            "total_steps": 500,
        })
        
        with open(metrics_path, "w") as f:
            for m in metrics:
                f.write(json.dumps(m) + "\n")
        
        return output_dir
    
    def test_loss_history_extraction(self, metrics_with_history):
        """Test loss history extraction from metrics."""
        from ChatOS.training.monitor import get_training_metrics_summary
        
        summary = get_training_metrics_summary(str(metrics_with_history))
        
        assert len(summary["train_loss_history"]) > 0
        assert len(summary["eval_loss_history"]) > 0
        
        # Loss should be decreasing
        train_losses = [h["loss"] for h in summary["train_loss_history"]]
        # Check that minimum is less than maximum
        assert min(train_losses) < max(train_losses)
    
    def test_finished_event_detection(self, metrics_with_history):
        """Test finished event detection."""
        from ChatOS.training.monitor import get_training_metrics_summary
        
        summary = get_training_metrics_summary(str(metrics_with_history))
        
        assert summary.get("final_status") == "completed"
        assert summary.get("total_steps") == 500

