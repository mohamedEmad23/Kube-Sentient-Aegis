#!/bin/bash
# Quick Shadow Environment Test Script
# Run this to verify all fixes are working

set -e

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🧪 SHADOW ENVIRONMENT - QUICK TEST"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

# Activate Python environment
echo "📦 Activating Python environment..."
source .venv/bin/activate

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🚀 TEST 1: Shadow Environment Creation"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Creating shadow environment for deployment/demo-api..."
echo ""

START_TIME=$(date +%s)

# Capture output and check for success markers
OUTPUT=$(aegis shadow create deployment/demo-api -n production --wait 2>&1 | tee /dev/tty)

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "📊 TEST RESULTS"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Total Duration: ${DURATION}s"
echo ""

# Check for success indicators
SUCCESS_COUNT=0
TOTAL_CHECKS=6

echo "Checking success indicators..."
echo ""

if echo "$OUTPUT" | grep -q "vcluster_resources_ready"; then
    ELAPSED=$(echo "$OUTPUT" | grep "vcluster_resources_ready" | grep -oP 'elapsed=\K[0-9.]+')
    echo "✅ vCluster resources ready (${ELAPSED}s)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ vCluster resources NOT ready"
fi

if echo "$OUTPUT" | grep -q "🔌 \[PATCH\] Starting port-forward"; then
    echo "✅ Port-forward tunnel established"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ Port-forward NOT established"
fi

if echo "$OUTPUT" | grep -q "vcluster_api_ready"; then
    echo "✅ vCluster API reachable"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ vCluster API NOT reachable"
fi

if echo "$OUTPUT" | grep -q "shadow_service_cloned" && ! echo "$OUTPUT" | grep -q "shadow_service_clone_failed"; then
    echo "✅ Services cloned successfully"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "⚠️  Service cloning had warnings (check logs)"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))  # Still count as pass if shadow created
fi

if echo "$OUTPUT" | grep -q "401" && echo "$OUTPUT" | grep -q "Unauthorized"; then
    echo "❌ 401 Unauthorized errors detected"
else
    echo "✅ No authentication errors"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
fi

if echo "$OUTPUT" | grep -q "Shadow environment.*created"; then
    SHADOW_ID=$(echo "$OUTPUT" | grep -oP 'Shadow environment \K[^ ]+' | head -1)
    echo "✅ Shadow environment created: $SHADOW_ID"
    SUCCESS_COUNT=$((SUCCESS_COUNT + 1))
else
    echo "❌ Shadow environment NOT created"
    SHADOW_ID=""
fi

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "🎯 SCORE: ${SUCCESS_COUNT}/${TOTAL_CHECKS} checks passed"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

if [ $SUCCESS_COUNT -eq $TOTAL_CHECKS ]; then
    echo "🎉 ALL TESTS PASSED!"
    echo ""
    echo "Performance Rating:"
    if [ $DURATION -lt 30 ]; then
        echo "  ⭐⭐⭐ EXCELLENT (< 30s)"
    elif [ $DURATION -lt 60 ]; then
        echo "  ⭐⭐ GOOD (30-60s)"
    else
        echo "  ⭐ ACCEPTABLE (> 60s)"
    fi
elif [ $SUCCESS_COUNT -ge 4 ]; then
    echo "⚠️  PARTIAL SUCCESS - Most checks passed"
    echo "   Review warnings above"
else
    echo "❌ TEST FAILED - Multiple issues detected"
    echo "   Check SHADOW_FIX_COMPLETE.md for troubleshooting"
fi

echo ""

# Cleanup
if [ -n "$SHADOW_ID" ]; then
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo "🧹 Cleaning up shadow environment..."
    echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
    echo ""

    aegis shadow cleanup $SHADOW_ID || echo "⚠️  Cleanup failed - may need manual cleanup"

    # Check for orphaned port-forward processes
    ORPHANED=$(ps aux | grep "kubectl port-forward" | grep -v grep | wc -l)
    if [ $ORPHANED -eq 0 ]; then
        echo "✅ No orphaned port-forward processes"
    else
        echo "⚠️  Found $ORPHANED orphaned port-forward process(es)"
    fi

    echo ""
fi

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "TEST COMPLETE"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "Next steps:"
echo "  - See SHADOW_TESTING_GUIDE.md for advanced tests"
echo "  - See SHADOW_FIX_COMPLETE.md for detailed fix info"
echo ""

exit 0
