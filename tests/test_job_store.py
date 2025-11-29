"""
Tests for ChatOS.training.job_store module.
"""

import json
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest


class TestJobStore:
    """Test cases for the job store module."""
    
    @pytest.fixture
    def mock_settings(self, tmp_path):
        """Create mock settings with temporary directories."""
        mock = type('Settings', (), {
            'training_jobs_dir': tmp_path / 'training_jobs',
        })()
        mock.training_jobs_dir.mkdir(parents=True, exist_ok=True)
        return mock
    
    @pytest.fixture
    def mock_job_spec(self):
        """Create a mock job spec."""
        from ChatOS.training.job_spec import TrainingJobSpec
        return TrainingJobSpec(
            id="test_job_001",
            base_model_name="test/model",
            dataset_train_path="/path/to/train.jsonl",
            dataset_eval_path="/path/to/eval.jsonl",
            output_dir="/path/to/output",
        )
    
    def test_create_job(self, mock_settings, mock_job_spec):
        """Test job creation."""
        with patch('ChatOS.training.job_store.settings', mock_settings):
            from ChatOS.training.job_store import create_job, get_job
            
            job = create_job(
                job_spec=mock_job_spec,
                pid=12345,
                config_path=Path("/path/to/config.yaml"),
                log_path=Path("/path/to/log.txt"),
            )
            
            assert job["id"] == "test_job_001"
            assert job["status"] == "running"
            assert job["pid"] == 12345
            
            # Verify it can be retrieved
            retrieved = get_job("test_job_001")
            assert retrieved is not None
            assert retrieved["id"] == "test_job_001"
    
    def test_update_job(self, mock_settings, mock_job_spec):
        """Test job update."""
        with patch('ChatOS.training.job_store.settings', mock_settings):
            from ChatOS.training.job_store import create_job, update_job, get_job
            
            create_job(
                job_spec=mock_job_spec,
                pid=12345,
                config_path=Path("/path/to/config.yaml"),
                log_path=Path("/path/to/log.txt"),
            )
            
            updated = update_job(
                "test_job_001",
                status="completed",
                latest_metrics={"train_loss": 0.5},
            )
            
            assert updated["status"] == "completed"
            assert updated["latest_metrics"]["train_loss"] == 0.5
    
    def test_list_jobs(self, mock_settings, mock_job_spec):
        """Test listing jobs."""
        with patch('ChatOS.training.job_store.settings', mock_settings):
            from ChatOS.training.job_store import create_job, list_jobs
            
            # Create multiple jobs
            for i in range(3):
                spec = type('Spec', (), {
                    'id': f"test_job_{i:03d}",
                    'base_model_name': "test/model",
                    'dataset_train_path': "/path/train.jsonl",
                    'dataset_eval_path': "/path/eval.jsonl",
                    'output_dir': f"/path/output_{i}",
                    'description': None,
                    'learning_rate': 2e-4,
                    'num_epochs': 2,
                    'max_steps': None,
                    'per_device_batch_size': 1,
                    'gradient_accumulation_steps': 8,
                    'lora_r': 16,
                    'lora_alpha': 16,
                })()
                create_job(
                    job_spec=spec,
                    pid=12345 + i,
                    config_path=Path(f"/path/config_{i}.yaml"),
                    log_path=Path(f"/path/log_{i}.txt"),
                )
            
            jobs = list_jobs()
            assert len(jobs) == 3
    
    def test_mark_job_completed(self, mock_settings, mock_job_spec):
        """Test marking job as completed."""
        with patch('ChatOS.training.job_store.settings', mock_settings):
            from ChatOS.training.job_store import (
                create_job, mark_job_completed, get_job
            )
            
            create_job(
                job_spec=mock_job_spec,
                pid=12345,
                config_path=Path("/path/to/config.yaml"),
                log_path=Path("/path/to/log.txt"),
            )
            
            mark_job_completed(
                "test_job_001",
                metrics={"final_loss": 0.3, "total_steps": 100}
            )
            
            job = get_job("test_job_001")
            assert job["status"] == "completed"
            assert job["finished_at"] is not None
    
    def test_mark_job_failed(self, mock_settings, mock_job_spec):
        """Test marking job as failed."""
        with patch('ChatOS.training.job_store.settings', mock_settings):
            from ChatOS.training.job_store import (
                create_job, mark_job_failed, get_job
            )
            
            create_job(
                job_spec=mock_job_spec,
                pid=12345,
                config_path=Path("/path/to/config.yaml"),
                log_path=Path("/path/to/log.txt"),
            )
            
            mark_job_failed(
                "test_job_001",
                error_snippet="CUDA out of memory"
            )
            
            job = get_job("test_job_001")
            assert job["status"] == "failed"
            assert "CUDA" in job["error_snippet"]
    
    def test_get_running_jobs(self, mock_settings):
        """Test getting running jobs."""
        with patch('ChatOS.training.job_store.settings', mock_settings):
            from ChatOS.training.job_store import (
                create_job, get_running_jobs, mark_job_completed
            )
            
            # Create two jobs
            for i in range(2):
                spec = type('Spec', (), {
                    'id': f"test_job_{i:03d}",
                    'base_model_name': "test/model",
                    'dataset_train_path': "/path/train.jsonl",
                    'dataset_eval_path': "/path/eval.jsonl",
                    'output_dir': f"/path/output_{i}",
                    'description': None,
                    'learning_rate': 2e-4,
                    'num_epochs': 2,
                    'max_steps': None,
                    'per_device_batch_size': 1,
                    'gradient_accumulation_steps': 8,
                    'lora_r': 16,
                    'lora_alpha': 16,
                })()
                create_job(
                    job_spec=spec,
                    pid=12345 + i,
                    config_path=Path(f"/path/config_{i}.yaml"),
                    log_path=Path(f"/path/log_{i}.txt"),
                )
            
            # Both should be running
            running = get_running_jobs()
            assert len(running) == 2
            
            # Complete one
            mark_job_completed("test_job_000")
            
            # Only one should be running
            running = get_running_jobs()
            assert len(running) == 1


class TestJobSpec:
    """Test cases for TrainingJobSpec."""
    
    def test_default_spec(self):
        """Test creating spec with defaults."""
        from ChatOS.training.job_spec import TrainingJobSpec
        
        spec = TrainingJobSpec()
        
        assert spec.id is not None
        assert spec.base_model_name == "unsloth/Qwen2.5-7B-Instruct-bnb-4bit"
        assert spec.learning_rate == 2e-4
    
    def test_from_defaults(self):
        """Test from_defaults factory method."""
        from ChatOS.training.job_spec import TrainingJobSpec
        
        spec = TrainingJobSpec.from_defaults(
            model_name="unsloth/mistral-7b-instruct-v0.3-bnb-4bit",
            train_path="/data/train.jsonl",
            eval_path="/data/eval.jsonl",
            description="Test training run",
        )
        
        assert "mistral" in spec.base_model_name.lower()
        assert spec.chat_template == "mistral"
        assert spec.description == "Test training run"
    
    def test_to_config_override(self):
        """Test config override generation."""
        from ChatOS.training.job_spec import TrainingJobSpec
        
        spec = TrainingJobSpec(
            id="test_001",
            base_model_name="test/model",
            learning_rate=1e-4,
            num_epochs=3,
        )
        
        override = spec.to_config_override()
        
        assert override["job_id"] == "test_001"
        assert override["model"]["name"] == "test/model"
        assert override["training"]["learning_rate"] == 1e-4
        assert override["training"]["num_train_epochs"] == 3

