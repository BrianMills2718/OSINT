"""Test suite to verify all imports work without circular dependencies"""
import pytest
import importlib
import sys

def test_no_circular_imports():
    """EVIDENCE: All modules must import without circular dependency errors"""
    
    modules_to_test = [
        'twitterexplorer.config',
        'twitterexplorer.investigation_engine',
        'twitterexplorer.graph_aware_llm_coordinator',
        'twitterexplorer.investigation_graph',
        'twitterexplorer.api_client',
        # Skip app.py as it's a Streamlit app that requires runtime context
        # 'twitterexplorer.app'
    ]
    
    # Clear module cache to ensure fresh imports
    for module_name in modules_to_test:
        if module_name in sys.modules:
            del sys.modules[module_name]
    
    # Test each module imports successfully
    for module_name in modules_to_test:
        try:
            module = importlib.import_module(module_name)
            assert module is not None
            print(f"[PASS] {module_name} imported successfully")
        except ImportError as e:
            assert False, f"Circular import in {module_name}: {e}"

def test_config_has_all_attributes():
    """EVIDENCE: Config must have all required attributes"""
    from twitterexplorer import config
    
    required = [
        'RAPIDAPI_TWITTER_HOST',
        'RAPIDAPI_BASE_URL', 
        'GEMINI_MODEL_NAME',
        'DEFAULT_MAX_PAGES_FALLBACK',
        'API_TIMEOUT_SECONDS',
        'ENDPOINTS_FILE',
        'ONTOLOGY_FILE'
    ]
    
    for attr in required:
        assert hasattr(config, attr), f"Missing: {attr}"
        value = getattr(config, attr)
        assert value is not None, f"{attr} is None"
        print(f"[PASS] config.{attr} = {value}")

if __name__ == "__main__":
    test_no_circular_imports()
    test_config_has_all_attributes()
    print("\n[SUCCESS] All import tests passed!")