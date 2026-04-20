#!/bin/bash
# Autonomous Verification Suite for ncsdl

# Set PYTHONPATH to include current directory
export PYTHONPATH=$PYTHONPATH:.

echo "========================================"
echo "   NCSDL Verification Suite starting    "
echo "========================================"
echo

# 1. Run Logic Tests (Python unittest)
echo "[1/4] Running Unit Logic Tests..."
python3 tests/test_migration_logic.py
if [ $? -ne 0 ]; then echo "Migration logic tests FAILED"; exit 1; fi

python3 tests/test_renamer_logic.py
if [ $? -ne 0 ]; then echo "Renamer logic tests FAILED"; exit 1; fi
echo "Logic tests PASSED."
echo

# 2. Run CLI Smoke Tests
echo "[2/4] Running CLI Smoke Tests..."
python3 tests/test_cli_smoke.py
if [ $? -ne 0 ]; then echo "CLI smoke tests FAILED"; exit 1; fi
echo "CLI smoke tests PASSED."
echo

# 3. Full Software Workflow Integration Test
echo "[3/4] Running FULL WORKFLOW Integration Test (Real Download)..."
mkdir -p test_integration_src test_integration_dst

echo "Step A: Downloading 3 songs (limited for speed)..."
python3 -m ncsdl download --limit 3 --output test_integration_src --retries 3
if [ $? -ne 0 ]; then echo "Download step FAILED"; exit 1; fi

echo "Step B: Running Statistics..."
python3 -m ncsdl stats test_integration_src
if [ $? -ne 0 ]; then echo "Stats step FAILED"; exit 1; fi

echo "Step C: Running Duplicate Check..."
python3 -m ncsdl check-dupes test_integration_src
if [ $? -ne 0 ]; then echo "Check-dupes step FAILED"; exit 1; fi

echo "Step D: Running In-place Renamer..."
python3 -m ncsdl rename test_integration_src --max-workers 5
if [ $? -ne 0 ]; then echo "Rename step FAILED"; exit 1; fi

echo "Step E: Migrating to New Library (Copy Mode)..."
python3 -m ncsdl migrate test_integration_src test_integration_dst --mode copy
if [ $? -ne 0 ]; then echo "Migrate step FAILED"; exit 1; fi

echo "Step F: Verifying Migration..."
python3 -m ncsdl stats test_integration_dst
if [ $? -ne 0 ]; then echo "Migration verification FAILED"; exit 1; fi

echo "Integration Test PASSED."
echo

# 4. Clean environment check
echo "[4/4] Checking for codebase cleanliness..."
JUNK_PRINTS=$(grep -r "print(" ncsdl/cmd/ | grep -v "_shared.py")
if [ ! -z "$JUNK_PRINTS" ]; then
    echo "Warning: Direct print() calls found in commands:"
    echo "$JUNK_PRINTS"
fi

# Cleanup integration folders
rm -rf test_integration_src test_integration_dst

echo "========================================"
echo "   All tests passed successfully!      "
echo "========================================"
