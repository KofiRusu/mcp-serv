"""
Auto Trainer tests for ChatOS.

Tests the automated training pipeline including data preparation,
training readiness checks, and configuration validation.
"""

import json
import tempfile
from pathlib import Path
from datetime import datetime, timedelta
from unittest.mock import patch, MagicMock

import pytest

from ChatOS.controllers.auto_trainer import (
    TrainingConfig,
    TrainingRun,
    TrainingDataPreparer,
    AutoTrainer,
    MIN_SAMPLES_FOR_TRAINING,
    MIN_QUALITY_RATIO,
    TRAINING_COOLDOWN_HOURS,
    get_auto_trainer,
)


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def temp_training_dir(tmp_path):
    """Create temporary directories for training."""
    training_dir = tmp_path / "training_data"
    models_dir = tmp_path / "models"
    checkpoints_dir = models_dir / "checkpoints"
    
    for d in [training_dir, models_dir, checkpoints_dir]:
        d.mkdir(parents=True, exist_ok=True)
    
    return {
        "base": tmp_path,
        "training": training_dir,
        "models": models_dir,
        "checkpoints": checkpoints_dir,
    }


@pytest.fixture
def sample_training_data(temp_training_dir):
    """Create sample training data files."""
    training_dir = temp_training_dir["training"]
    
    # Good quality samples
    good_samples = [
        {
            "messages": [
                {"role": "user", "content": "What is Python?"},
                {"role": "assistant", "content": "Python is a high-level programming language known for its simplicity and readability."}
            ],
            "metadata": {"quality": "good", "mode": "normal", "model": "test"}
        },
        {
            "messages": [
                {"role": "user", "content": "How do I create a list in Python?"},
                {"role": "assistant", "content": "You can create a list using square brackets: my_list = [1, 2, 3]"}
            ],
            "metadata": {"quality": "excellent", "mode": "code", "model": "test"}
        },
    ]
    
    # Poor quality samples
    poor_samples = [
        {
            "messages": [
                {"role": "user", "content": "Help"},
                {"role": "assistant", "content": "Error occurred"}
            ],
            "metadata": {"quality": "poor", "mode": "normal", "model": "test"}
        },
    ]
    
    # Write to file
    data_file = training_dir / "training_2024-01-01.jsonl"
    with open(data_file, "w") as f:
        for sample in good_samples + poor_samples:
            f.write(json.dumps(sample) + "\n")
    
    return {
        "file": data_file,
        "good_count": len(good_samples),
        "poor_count": len(poor_samples),
        "total": len(good_samples) + len(poor_samples),
    }


@pytest.fixture
def data_preparer(temp_training_dir):
    """Create TrainingDataPreparer with temp directory."""
    with patch("ChatOS.controllers.auto_trainer.TRAINING_DIR", temp_training_dir["training"]):
        preparer = TrainingDataPreparer()
        preparer.training_dir = temp_training_dir["training"]
        yield preparer


@pytest.fixture
def auto_trainer(temp_training_dir):
    """Create AutoTrainer with temp directories."""
    with patch("ChatOS.controllers.auto_trainer.TRAINING_DIR", temp_training_dir["training"]), \
         patch("ChatOS.controllers.auto_trainer.MODELS_DIR", temp_training_dir["models"]), \
         patch("ChatOS.controllers.auto_trainer.CHECKPOINTS_DIR", temp_training_dir["checkpoints"]):
        trainer = AutoTrainer()
        trainer.data_preparer.training_dir = temp_training_dir["training"]
        yield trainer


# =============================================================================
# TrainingConfig Tests
# =============================================================================

class TestTrainingConfig:
    """Tests for TrainingConfig dataclass."""

    def test_default_values(self):
        """Should have sensible default values."""
        config = TrainingConfig()
        
        assert config.base_model == "Qwen/Qwen2.5-7B-Instruct"
        assert config.output_name == "chatos-qwen-enhanced"
        assert config.lora_r == 16
        assert config.lora_alpha == 32
        assert config.epochs == 2
        assert config.use_4bit is True

    def test_custom_values(self):
        """Should accept custom values."""
        config = TrainingConfig(
            base_model="custom/model",
            lora_r=32,
            epochs=5,
        )
        
        assert config.base_model == "custom/model"
        assert config.lora_r == 32
        assert config.epochs == 5

    def test_target_modules_default(self):
        """Should have default target modules for Qwen."""
        config = TrainingConfig()
        
        expected_modules = ["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"]
        assert config.target_modules == expected_modules

    def test_to_dict(self):
        """Should convert to dictionary."""
        config = TrainingConfig()
        d = config.to_dict()
        
        assert isinstance(d, dict)
        assert "base_model" in d
        assert "lora_r" in d
        assert "epochs" in d
        assert d["use_4bit"] is True


# =============================================================================
# TrainingRun Tests
# =============================================================================

class TestTrainingRun:
    """Tests for TrainingRun dataclass."""

    def test_default_status(self):
        """Should default to pending status."""
        run = TrainingRun(
            run_id="test123",
            started_at=datetime.now().isoformat(),
            config={}
        )
        
        assert run.status == "pending"

    def test_all_fields_stored(self):
        """Should store all provided fields."""
        run = TrainingRun(
            run_id="test456",
            started_at="2024-01-01T12:00:00",
            config={"epochs": 2},
            num_samples=100,
            status="running",
        )
        
        assert run.run_id == "test456"
        assert run.num_samples == 100
        assert run.status == "running"


# =============================================================================
# TrainingDataPreparer Tests
# =============================================================================

class TestTrainingDataPreparer:
    """Tests for TrainingDataPreparer class."""

    def test_get_data_stats_empty(self, data_preparer):
        """Should return zero stats for empty directory."""
        stats = data_preparer.get_data_stats()
        
        assert stats["total_files"] == 0
        assert stats["total_samples"] == 0

    def test_get_data_stats_with_data(self, data_preparer, sample_training_data):
        """Should count samples correctly."""
        stats = data_preparer.get_data_stats()
        
        assert stats["total_files"] == 1
        assert stats["total_samples"] == sample_training_data["total"]

    def test_get_data_stats_quality_distribution(self, data_preparer, sample_training_data):
        """Should track quality distribution."""
        stats = data_preparer.get_data_stats()
        
        assert "quality_distribution" in stats
        assert stats["quality_distribution"].get("good", 0) == 1
        assert stats["quality_distribution"].get("excellent", 0) == 1
        assert stats["quality_distribution"].get("poor", 0) == 1

    def test_prepare_dataset_basic(self, data_preparer, sample_training_data, temp_training_dir):
        """Should prepare dataset from training data."""
        output_file = temp_training_dir["training"] / "prepared.json"
        stats = data_preparer.prepare_dataset(output_file)
        
        assert output_file.exists()
        assert stats["final_samples"] >= 1

    def test_prepare_dataset_filters_by_quality(self, data_preparer, sample_training_data, temp_training_dir):
        """Should filter out low quality samples."""
        output_file = temp_training_dir["training"] / "filtered.json"
        stats = data_preparer.prepare_dataset(output_file, min_quality="acceptable")
        
        # Poor quality should be filtered
        assert stats["quality_filtered"] >= 1

    def test_prepare_dataset_max_samples(self, data_preparer, sample_training_data, temp_training_dir):
        """Should limit samples if max_samples specified."""
        output_file = temp_training_dir["training"] / "limited.json"
        stats = data_preparer.prepare_dataset(output_file, max_samples=1)
        
        assert stats["final_samples"] == 1
        
        with open(output_file) as f:
            data = json.load(f)
            assert len(data) == 1

    def test_validate_messages_valid(self, data_preparer):
        """Should accept valid message format."""
        messages = [
            {"role": "user", "content": "This is a valid question"},
            {"role": "assistant", "content": "This is a valid response"}
        ]
        
        assert data_preparer._validate_messages(messages) is True

    def test_validate_messages_too_few(self, data_preparer):
        """Should reject single message."""
        messages = [{"role": "user", "content": "Just one message"}]
        
        assert data_preparer._validate_messages(messages) is False

    def test_validate_messages_missing_roles(self, data_preparer):
        """Should reject if missing user or assistant."""
        messages = [
            {"role": "system", "content": "System message"},
            {"role": "system", "content": "Another system message"}
        ]
        
        assert data_preparer._validate_messages(messages) is False

    def test_validate_messages_too_short(self, data_preparer):
        """Should reject very short content."""
        messages = [
            {"role": "user", "content": "Hi"},  # Too short
            {"role": "assistant", "content": "OK"}  # Too short
        ]
        
        assert data_preparer._validate_messages(messages) is False

    def test_validate_messages_too_long(self, data_preparer):
        """Should reject very long content."""
        messages = [
            {"role": "user", "content": "a" * 15000},  # Too long
            {"role": "assistant", "content": "Normal response"}
        ]
        
        assert data_preparer._validate_messages(messages) is False


# =============================================================================
# AutoTrainer Tests
# =============================================================================

class TestAutoTrainer:
    """Tests for AutoTrainer class."""

    def test_should_train_insufficient_samples(self, auto_trainer):
        """Should not train with insufficient samples."""
        result = auto_trainer.should_train()
        
        assert result["should_train"] is False
        assert "Insufficient samples" in result["reason"]

    def test_should_train_with_enough_samples(self, auto_trainer, temp_training_dir):
        """Should recommend training with enough good samples."""
        # Create enough samples
        training_dir = temp_training_dir["training"]
        data_file = training_dir / "training_2024-01-01.jsonl"
        
        samples = []
        for i in range(MIN_SAMPLES_FOR_TRAINING + 10):
            samples.append({
                "messages": [
                    {"role": "user", "content": f"Question number {i} with enough text"},
                    {"role": "assistant", "content": f"Answer number {i} with sufficient content"}
                ],
                "metadata": {"quality": "good" if i % 2 == 0 else "excellent", "mode": "normal"}
            })
        
        with open(data_file, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")
        
        result = auto_trainer.should_train()
        
        assert result["should_train"] is True
        assert result["reason"] == "Ready for training"

    def test_should_train_low_quality_ratio(self, auto_trainer, temp_training_dir):
        """Should not train if quality ratio is too low."""
        training_dir = temp_training_dir["training"]
        data_file = training_dir / "training_2024-01-01.jsonl"
        
        # Create samples with mostly poor quality
        samples = []
        for i in range(MIN_SAMPLES_FOR_TRAINING + 10):
            quality = "poor" if i < MIN_SAMPLES_FOR_TRAINING else "good"
            samples.append({
                "messages": [
                    {"role": "user", "content": f"Question {i} with enough text here"},
                    {"role": "assistant", "content": f"Answer {i} with enough text here"}
                ],
                "metadata": {"quality": quality, "mode": "normal"}
            })
        
        with open(data_file, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")
        
        result = auto_trainer.should_train()
        
        # Should fail quality check
        assert result["should_train"] is False
        assert "Quality ratio" in result["reason"] or "Insufficient" in result["reason"]

    def test_should_train_cooldown(self, auto_trainer, temp_training_dir):
        """Should not train during cooldown period."""
        # Simulate a recent completed run
        auto_trainer.runs.append(TrainingRun(
            run_id="recent",
            started_at=(datetime.now() - timedelta(hours=1)).isoformat(),
            config={},
            status="completed",
            completed_at=datetime.now().isoformat(),
        ))
        
        # Create enough good samples
        training_dir = temp_training_dir["training"]
        data_file = training_dir / "training_2024-01-01.jsonl"
        
        samples = []
        for i in range(MIN_SAMPLES_FOR_TRAINING + 10):
            samples.append({
                "messages": [
                    {"role": "user", "content": f"Question {i} with enough content"},
                    {"role": "assistant", "content": f"Answer {i} with enough content"}
                ],
                "metadata": {"quality": "good", "mode": "normal"}
            })
        
        with open(data_file, "w") as f:
            for sample in samples:
                f.write(json.dumps(sample) + "\n")
        
        result = auto_trainer.should_train()
        
        assert result["should_train"] is False
        assert "Cooldown" in result["reason"]

    def test_get_training_status(self, auto_trainer):
        """Should return training status."""
        status = auto_trainer.get_training_status()
        
        assert "total_runs" in status
        assert "completed_runs" in status
        assert "failed_runs" in status
        assert "active_runs" in status
        assert "readiness" in status

    def test_list_models_empty(self, auto_trainer):
        """Should return empty list when no trained models."""
        models = auto_trainer.list_models()
        
        assert isinstance(models, list)
        assert len(models) == 0

    def test_list_models_with_completed_runs(self, auto_trainer, temp_training_dir):
        """Should list completed training runs."""
        # Add a completed run
        output_path = temp_training_dir["checkpoints"] / "test_run"
        output_path.mkdir()
        
        auto_trainer.runs.append(TrainingRun(
            run_id="completed_test",
            started_at="2024-01-01T12:00:00",
            config={},
            status="completed",
            completed_at="2024-01-01T14:00:00",
            output_path=str(output_path),
            num_samples=100,
        ))
        
        models = auto_trainer.list_models()
        
        assert len(models) == 1
        assert models[0]["run_id"] == "completed_test"
        assert models[0]["samples"] == 100


# =============================================================================
# Training Script Generation Tests
# =============================================================================

class TestTrainingScriptGeneration:
    """Tests for training script generation."""

    def test_generate_training_script(self, auto_trainer, temp_training_dir):
        """Should generate valid training script."""
        config = TrainingConfig(epochs=3, lora_r=32)
        data_file = temp_training_dir["training"] / "test_data.json"
        output_dir = temp_training_dir["checkpoints"] / "test_output"
        
        script = auto_trainer._generate_training_script(config, data_file, output_dir)
        
        # Check script contains key elements
        assert "import torch" in script
        assert "BitsAndBytesConfig" in script
        assert "LoraConfig" in script
        assert "SFTTrainer" in script
        assert f"num_train_epochs={config.epochs}" in script
        assert f"r={config.lora_r}" in script

    def test_script_contains_data_path(self, auto_trainer, temp_training_dir):
        """Script should reference the data file."""
        config = TrainingConfig()
        data_file = temp_training_dir["training"] / "my_data.json"
        output_dir = temp_training_dir["checkpoints"] / "output"
        
        script = auto_trainer._generate_training_script(config, data_file, output_dir)
        
        assert str(data_file) in script


# =============================================================================
# History Persistence Tests
# =============================================================================

class TestHistoryPersistence:
    """Tests for training history saving/loading."""

    def test_save_and_load_history(self, temp_training_dir):
        """Should persist training history."""
        with patch("ChatOS.controllers.auto_trainer.TRAINING_DIR", temp_training_dir["training"]), \
             patch("ChatOS.controllers.auto_trainer.MODELS_DIR", temp_training_dir["models"]), \
             patch("ChatOS.controllers.auto_trainer.CHECKPOINTS_DIR", temp_training_dir["checkpoints"]):
            
            trainer1 = AutoTrainer()
            trainer1.runs.append(TrainingRun(
                run_id="persist_test",
                started_at="2024-01-01T12:00:00",
                config={"epochs": 2},
                status="completed",
            ))
            trainer1._save_history()
            
            # Create new instance
            trainer2 = AutoTrainer()
            trainer2._load_history()
            
            assert len(trainer2.runs) >= 1
            assert trainer2.runs[-1].run_id == "persist_test"


# =============================================================================
# Singleton Tests
# =============================================================================

class TestAutoTrainerSingleton:
    """Tests for singleton pattern."""

    def test_get_auto_trainer_returns_instance(self):
        """get_auto_trainer should return AutoTrainer instance."""
        with patch("ChatOS.controllers.auto_trainer._trainer", None):
            trainer = get_auto_trainer()
            assert isinstance(trainer, AutoTrainer)

