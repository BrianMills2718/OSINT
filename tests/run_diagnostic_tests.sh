#!/bin/bash
# Master test runner - runs all diagnostic tests in order

echo "=========================================="
echo "DEEP RESEARCH DIAGNOSTIC TEST SUITE"
echo "=========================================="
echo ""
echo "This will run 3 tests to diagnose Brave Search integration:"
echo "  1. Environment variable loading (.env file)"
echo "  2. Brave Search API direct test (minimal code)"
echo "  3. Deep Research _search_brave method"
echo ""
echo "Press Enter to start..."
read

cd "$(dirname "$0")/.."
source .venv/bin/activate

# Test 1
echo ""
echo "=========================================="
echo "Running Test 1: Environment Loading"
echo "=========================================="
python3 tests/test_env_loading.py
TEST1_RESULT=$?

# Test 2
echo ""
echo ""
echo "=========================================="
echo "Running Test 2: Brave Search API Direct"
echo "=========================================="
python3 tests/test_brave_search_direct.py
TEST2_RESULT=$?

# Test 3
echo ""
echo ""
echo "=========================================="
echo "Running Test 3: Deep Research _search_brave"
echo "=========================================="
python3 tests/test_deep_research_brave.py
TEST3_RESULT=$?

# Summary
echo ""
echo ""
echo "=========================================="
echo "TEST SUMMARY"
echo "=========================================="
echo ""
if [ $TEST1_RESULT -eq 0 ]; then
    echo "✅ Test 1 (Environment): PASSED"
else
    echo "❌ Test 1 (Environment): FAILED"
fi

if [ $TEST2_RESULT -eq 0 ]; then
    echo "✅ Test 2 (Brave API Direct): PASSED"
else
    echo "❌ Test 2 (Brave API Direct): FAILED"
fi

if [ $TEST3_RESULT -eq 0 ]; then
    echo "✅ Test 3 (Deep Research Brave): PASSED"
else
    echo "❌ Test 3 (Deep Research Brave): FAILED"
fi

echo ""
if [ $TEST1_RESULT -eq 0 ] && [ $TEST2_RESULT -eq 0 ] && [ $TEST3_RESULT -eq 0 ]; then
    echo "=========================================="
    echo "✅ ALL TESTS PASSED"
    echo "=========================================="
    echo ""
    echo "Brave Search integration is working correctly."
    echo "The issue is likely in Streamlit environment loading."
    exit 0
else
    echo "=========================================="
    echo "❌ SOME TESTS FAILED"
    echo "=========================================="
    echo ""
    echo "Check the output above to see which layer failed."
    echo "This will help us fix the root cause."
    exit 1
fi
