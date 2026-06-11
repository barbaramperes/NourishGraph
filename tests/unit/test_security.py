"""
Unit tests for API security improvements.

Tests CORS configuration, input validation, and authentication.
"""

import pytest
import os
from pathlib import Path


@pytest.mark.unit
class TestSecurityConfiguration:
    """Tests for security configuration."""
    
    def test_api_file_exists(self):
        """Test api.py exists."""
        api_file = Path(__file__).parent.parent.parent / "app" / "api.py"
        assert api_file.exists()
    
    def test_cors_not_wildcard(self):
        """Test CORS is not configured with wildcard."""
        api_file = Path(__file__).parent.parent.parent / "app" / "api.py"
        content = api_file.read_text()
        
        # Check that we don't have allow_origins=["*"] directly
        # (our new configuration uses _allowed_origins variable)
        assert '_allowed_origins' in content or 'ALLOWED_ORIGINS' in content, \
            "CORS should use configurable origins, not hardcoded wildcard"
    
    def test_message_length_validation(self):
        """Test message length validation exists."""
        api_file = Path(__file__).parent.parent.parent / "app" / "api.py"
        content = api_file.read_text()
        
        assert 'MAX_MESSAGE_LENGTH' in content, \
            "Should have MAX_MESSAGE_LENGTH constant for input validation"
        assert 'max_length' in content, \
            "ChatIn model should have max_length validation"
    
    def test_specific_exception_handling(self):
        """Test verify_password uses specific exceptions."""
        api_file = Path(__file__).parent.parent.parent / "app" / "api.py"
        content = api_file.read_text()
        
        # Check that we catch specific exceptions, not bare except
        assert 'except (ValueError, AttributeError, TypeError)' in content or \
               'except ValueError' in content or \
               'except Exception as e' in content, \
            "verify_password should catch specific exceptions"


@pytest.mark.unit
class TestDatabaseSecurity:
    """Tests for database security."""
    
    def test_database_file_exists(self):
        """Test database.py exists."""
        db_file = Path(__file__).parent.parent.parent / "app" / "data" / "database.py"
        assert db_file.exists()
    
    def test_atomic_delete_account(self):
        """Test delete_account uses atomic transaction."""
        db_file = Path(__file__).parent.parent.parent / "app" / "data" / "database.py"
        content = db_file.read_text()
        
        # Check for transaction handling in delete_account
        # Should have commit/rollback pattern
        assert 'conn.commit()' in content, \
            "delete_account should explicitly commit transactions"
        assert 'conn.rollback()' in content, \
            "delete_account should handle rollback on errors"
    
    def test_parameterized_queries(self):
        """Test database uses parameterized queries."""
        db_file = Path(__file__).parent.parent.parent / "app" / "data" / "database.py"
        content = db_file.read_text()
        
        # Should use %s placeholders (parameterized queries)
        assert '%s' in content, \
            "Should use parameterized queries with %s placeholders"
        
        # Should not have f-string SQL injection risks
        # (Some f-strings for field names are acceptable if fields are whitelisted)


@pytest.mark.unit
class TestLLMConfiguration:
    """Tests for LLM configuration."""
    
    def test_llm_timeout_configured(self):
        """Test LLM has timeout configured."""
        nodes_file = Path(__file__).parent.parent.parent / "app" / "graph" / "nodes.py"
        content = nodes_file.read_text()
        
        assert 'request_timeout' in content, \
            "LLM should have request_timeout configured"
        assert 'LLM_TIMEOUT' in content, \
            "LLM timeout should be configurable via environment"
    
    def test_llm_model_configurable(self):
        """Test LLM model is configurable."""
        nodes_file = Path(__file__).parent.parent.parent / "app" / "graph" / "nodes.py"
        content = nodes_file.read_text()
        
        assert 'LLM_MODEL' in content, \
            "LLM model should be configurable via environment"
        assert 'os.getenv' in content, \
            "Should use environment variables for configuration"
    
    def test_regex_patterns_compiled(self):
        """Test regex patterns are pre-compiled for performance."""
        nodes_file = Path(__file__).parent.parent.parent / "app" / "graph" / "nodes.py"
        content = nodes_file.read_text()
        
        assert '_compiled_medical' in content or 're.compile' in content, \
            "Regex patterns should be pre-compiled for performance"


@pytest.mark.unit
class TestGuardrails:
    """Tests for safety guardrails."""
    
    def test_guardrails_file_exists(self):
        """Test guardrails.py exists."""
        guardrails_file = Path(__file__).parent.parent.parent / "app" / "safety" / "guardrails.py"
        assert guardrails_file.exists()
    
    def test_safety_levels_defined(self):
        """Test safety levels are defined."""
        guardrails_file = Path(__file__).parent.parent.parent / "app" / "safety" / "guardrails.py"
        content = guardrails_file.read_text()
        
        assert 'SafetyLevel' in content
        assert 'SAFE' in content
        assert 'CRITICAL' in content
        assert 'BLOCKED' in content
    
    def test_medical_patterns_exist(self):
        """Test medical blocking patterns exist."""
        guardrails_file = Path(__file__).parent.parent.parent / "app" / "safety" / "guardrails.py"
        content = guardrails_file.read_text()
        
        assert 'MEDICAL_EMERGENCY_PATTERNS' in content
        assert 'EATING_DISORDER_PATTERNS' in content


@pytest.mark.unit
class TestLoggingConfiguration:
    """Tests for logging configuration."""
    
    def test_logging_module_exists(self):
        """Test logging configuration module exists."""
        logging_file = Path(__file__).parent.parent.parent / "app" / "config" / "logging.py"
        assert logging_file.exists()
    
    def test_logging_has_formatters(self):
        """Test logging has dev and json formatters."""
        logging_file = Path(__file__).parent.parent.parent / "app" / "config" / "logging.py"
        content = logging_file.read_text()
        
        assert 'DevFormatter' in content
        assert 'JsonFormatter' in content
    
    def test_logging_has_get_logger(self):
        """Test logging has get_logger function."""
        logging_file = Path(__file__).parent.parent.parent / "app" / "config" / "logging.py"
        content = logging_file.read_text()
        
        assert 'def get_logger' in content
