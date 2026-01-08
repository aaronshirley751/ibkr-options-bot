# Next Session Action Plan - Phase 3 Retry & Production Readiness

**Date Created:** January 8, 2026  
**Target Start Date:** Next available session  
**Priority:** 🔴 CRITICAL - Production blocking issue  
**Status:** Ready for execution  

---

## Overview

This document outlines the specific steps and timeline for the next session to retry Phase 3 with adjusted parameters and implement production-ready safeguards.

---

## Session 1: Phase 3 Retry (Conservative Approach)

**Objective:** Resolve Gateway request timeout issue  
**Target Duration:** 4+ hours continuous operation  
**Key Changes:** Reduce request frequency and symbol count  

### Pre-Flight Checklist

**Before starting Phase 3 retry:**

- [ ] Read ROUND_2_PEER_REVIEW_AND_ASSESSMENT.md (Part 3: Critical Issue)
- [ ] Review SESSION_DOCUMENTATION_2026-01-08.md (Phase 3 Timeline)
- [ ] Confirm Gateway connectivity (run test_ibkr_connection.py)
- [ ] Verify dry-run mode enabled (dry_run: true in settings)
- [ ] Check logs/ directory is writable
- [ ] Ensure 4+ hours of uninterrupted runtime available

### Configuration Changes

**Current Settings (Phase 3 - Failed):**
```yaml
symbols: [SPY, QQQ, AAPL]                 # 3 symbols
schedule:
  interval_seconds: 180                    # 3 minutes
  max_concurrent_symbols: 1                # Sequential
```

**New Settings (Phase 3 Retry - Conservative):**
```yaml
symbols: [SPY]                             # 1 symbol only
schedule:
  interval_seconds: 600                    # 10 minutes (reduced frequency)
  max_concurrent_symbols: 1                # Sequential (unchanged)
```

**Rationale:**
- Reduce request frequency: 1 request per 3 min → 1 per 10 min
- Reduce symbol count: 3 symbols → 1 symbol
- Expected behavior: Should sustain longer without timeout
- Target: 24 cycles × 10 min = 4 hours

### Execution Steps

**Step 1: Prepare Environment (t=0)**
```bash
cd /path/to/ibkr-options-bot

# Verify configuration
cat configs/settings.yaml | grep -A5 "symbols:"
cat configs/settings.yaml | grep -A5 "interval_seconds:"

# Verify Gateway connectivity
python -m tests.test_ibkr_connection

# Clear previous logs
rm -f logs/bot.log logs/bot.jsonl  # Optional: preserve for comparison
```

**Step 2: Launch Phase 3 Retry (t=0)**
```bash
# Start bot with Phase 3 retry settings
python -m src.bot.app

# Monitoring in separate terminal:
tail -f logs/bot.jsonl | grep -E "SUCCESS|TIMEOUT|WARNING"
```

**Step 3: Monitor Real-Time (Continuous)**

Create a monitoring script that tracks:
```
- Cycle count (target: 25+ for 4+ hours)
- Success rate (target: 95%+)
- Request latency (target: <5s per request)
- Timeout frequency (target: 0)
```

Monitoring commands:
```bash
# Watch success/failure pattern
grep -c "Dry-run" logs/bot.jsonl  # Count successful cycles

# Watch for timeouts
grep "Timeout\|TIMEOUT" logs/bot.jsonl

# Watch for errors
grep "ERROR\|WARNING" logs/bot.jsonl

# Monitor in real-time
python monitor_phase3.py  # Use existing monitoring script
```

**Step 4: Expected Milestones**

| Time | Cycles | Expected Result |
|------|--------|-----------------|
| t=10 min | 1 | ✅ SPY processed successfully |
| t=20 min | 2 | ✅ Still processing, no timeout |
| t=30 min | 3 | ✅ Confirm no timeout pattern |
| t=1 hour | 6 | ✅ Sustained operation stable |
| t=2 hours | 12 | ✅ Request latency remains stable |
| t=3 hours | 18 | ✅ No degradation observed |
| t=4 hours | 24+ | ✅ **SUCCESS** - Phase 3 Retry Complete |

**Step 5: Success Criteria**

Phase 3 Retry is **SUCCESSFUL** if:
- ✅ Bot runs continuously for 4+ hours without user intervention
- ✅ Complete 25+ cycles (allow 1-2 failed cycles for transient issues)
- ✅ Success rate: 95%+ (max 2 failed cycles out of 25+)
- ✅ No pattern of degradation (e.g., request latency increase)
- ✅ All timeouts transient (backoff recovery works)
- ✅ No memory leaks (check process memory over time)

**Step 6: Failure Scenarios & Responses**

**Scenario A: Timeout still occurs after 5 minutes**
```
Response:
  1. Stop bot immediately
  2. Record exact timeout pattern
  3. Compare with Phase 3 original (both at 5 min mark?)
  4. If identical pattern: Gateway rate limiting confirmed
  5. Escalate to root cause investigation
     - Research IBKR rate limits
     - Consider alternative: caching, queuing, etc.
```

**Scenario B: Timeouts occur but at longer intervals**
```
Response:
  1. Continue monitoring to establish pattern
  2. If timeouts decrease with longer interval, adjust further
  3. If timeouts still occur but recovery works: acceptable
  4. Proceed with production safeguards (circuit breaker, health checks)
```

**Scenario C: Phase 3 Retry succeeds**
```
Response:
  1. ✅ Document success with detailed metrics
  2. Proceed to Session 2: Production Readiness
  3. Implement production safeguards
  4. Plan deployment timeline
```

### Documentation During Phase 3 Retry

Create a detailed log file with:

```markdown
# Phase 3 Retry Log - January [DATE], 2026

## Configuration
- Symbols: SPY
- Interval: 600 seconds
- Target: 4+ hours

## Execution Timeline
[Record for entire 4+ hour duration]

### Success Metrics
- Start time: [record]
- End time: [record]
- Total cycles: [count from logs]
- Successful cycles: [count]
- Failed cycles: [count]
- Success rate: [percentage]

### Key Observations
- Timeout pattern: [describe]
- Request latency trend: [stable/increasing/decreasing]
- Memory usage: [stable/increasing]
- Notable errors: [list]

### Conclusion
[Summary of findings]
```

---

## Session 2: Production Readiness Implementation

**Objective:** Implement production-grade safeguards  
**Duration:** 2-4 hours  
**Prerequisite:** Phase 3 Retry successful  

### Implementation Tasks

**Task 1: Circuit Breaker Pattern** (Priority: HIGH)
```python
# Add to src/bot/scheduler.py

class CircuitBreaker:
    """Prevent repeated requests during sustained failures"""
    def __init__(self, failure_threshold=5, timeout_seconds=300):
        self.failure_count = 0
        self.failure_threshold = failure_threshold
        self.timeout_seconds = timeout_seconds
        self.last_failure_time = None
        
    def record_success(self):
        self.failure_count = 0
        self.last_failure_time = None
        
    def record_failure(self):
        self.failure_count += 1
        self.last_failure_time = time.time()
        
    def is_open(self):
        """Return True if circuit should be open (stop requests)"""
        if self.failure_count >= self.failure_threshold:
            elapsed = time.time() - self.last_failure_time
            if elapsed < self.timeout_seconds:
                return True
        return False
```

**Task 2: Request Latency Monitoring** (Priority: HIGH)
```python
# Add to src/bot/broker/ibkr.py

import time
from .log import logger

def historical_prices(self, contract, ...) -> Optional[pd.DataFrame]:
    """Retrieve historical prices with latency tracking"""
    start_time = time.time()
    
    try:
        # Existing logic
        bars = self.ib.reqHistoricalData(...)
        
        latency = time.time() - start_time
        logger.bind(
            action="historical_prices",
            symbol=contract.symbol,
            latency_seconds=round(latency, 2),
            bar_count=len(bars) if bars else 0
        ).info("Historical data retrieved")
        
        return _to_df(bars)
        
    except Exception as e:
        latency = time.time() - start_time
        logger.bind(
            action="historical_prices",
            symbol=contract.symbol,
            latency_seconds=round(latency, 2),
            error=str(e)
        ).error("Historical data failed")
        return None
```

**Task 3: Gateway Health Checks** (Priority: MEDIUM)
```python
# Add to src/bot/monitoring.py

def check_gateway_health(broker: Broker) -> Dict[str, Any]:
    """Quick health check for Gateway connectivity"""
    health = {
        "timestamp": datetime.utcnow().isoformat(),
        "gateway_responsive": False,
        "request_latency": None,
        "last_error": None
    }
    
    try:
        start = time.time()
        
        # Quick market data request (no historical data)
        contract = Stock("SPY", "SMART", "USD")
        ticker = broker.market_data(contract)
        
        latency = time.time() - start
        health["gateway_responsive"] = ticker.last > 0
        health["request_latency"] = round(latency, 2)
        
    except Exception as e:
        health["last_error"] = str(e)
    
    return health
```

**Task 4: Implement Health Check Calls** (Priority: MEDIUM)
```python
# Add to src/bot/scheduler.py, before each cycle

if should_check_gateway_health():
    health = check_gateway_health(broker)
    
    if not health["gateway_responsive"]:
        logger.warning("Gateway health check failed")
        return  # Skip cycle, try again next interval
    
    if health["request_latency"] > 10:
        logger.warning("Gateway latency high: {}s", health["request_latency"])
        # Continue but log for alerting
```

**Task 5: Request Rate Limiting Configuration** (Priority: MEDIUM)
```yaml
# Add to configs/settings.yaml

request_limiting:
  enabled: true
  max_requests_per_minute: 6  # 1 every 10 seconds max
  queue_enabled: true
  queue_max_size: 50
```

**Task 6: Alerting System** (Priority: LOW for first deployment)
```python
# Add to src/bot/monitoring.py

def alert_on_conditions(broker: Broker, cycle_metrics: Dict) -> None:
    """Send alerts for production issues"""
    
    # High request latency alert
    if cycle_metrics["avg_latency"] > 8:
        send_alert(f"HIGH LATENCY: {cycle_metrics['avg_latency']}s")
    
    # Repeated failures alert
    if cycle_metrics["consecutive_failures"] > 3:
        send_alert(f"REPEATED FAILURES: {cycle_metrics['consecutive_failures']}")
    
    # Daily loss limit approaching
    if cycle_metrics["loss_percentage"] > 0.75:  # 75% of daily limit
        send_alert(f"Daily loss limit approaching: {cycle_metrics['loss_percentage']}%")
```

### Implementation Checklist

- [ ] Add CircuitBreaker class
- [ ] Add request latency tracking
- [ ] Add Gateway health checks
- [ ] Add health check calls to scheduler
- [ ] Update settings.yaml with request limits
- [ ] Add alerting functions (optional for first deployment)
- [ ] Add unit tests for new components
- [ ] Test with Phase 3 settings (SPY, 600s interval)

### Testing After Implementation

```bash
# 1. Unit tests for new components
pytest tests/test_circuit_breaker.py -v
pytest tests/test_gateway_health.py -v

# 2. Integration test with StubBroker
pytest tests/test_scheduler_stubbed.py -v

# 3. Quick 1-hour test with live Gateway
python -m src.bot.app  # With production safeguards

# 4. Code review
# - Check circuit breaker triggers
# - Verify latency monitoring works
# - Confirm health checks execute
```

---

## Session 3: Final Validation & Deployment

**Objective:** Validate production readiness  
**Duration:** 2-4 hours  
**Prerequisite:** Session 2 complete  

### Final Validation Checklist

**Code Quality:**
- [ ] All new code passes linting (black, ruff)
- [ ] Test coverage maintained (>90%)
- [ ] No deprecated patterns
- [ ] Docstrings complete

**Functionality:**
- [ ] Phase 3 retry successful (4+ hours)
- [ ] Circuit breaker prevents request storms
- [ ] Health checks run before cycles
- [ ] Latency monitoring accurate
- [ ] Alerting system works

**Safety:**
- [ ] Dry-run mode prevents real orders
- [ ] Daily loss limits respected
- [ ] Position sizing correct
- [ ] Stop-loss/take-profit working
- [ ] Backoff mechanism functional

**Production Readiness:**
- [ ] All configuration documented
- [ ] Monitoring dashboard ready
- [ ] Alerting configured
- [ ] Rollback procedure documented
- [ ] Runbook created

### Deployment Preparation

1. **Create Deployment Checklist**
   ```markdown
   # Production Deployment Checklist
   
   Pre-Deployment:
   - [ ] Phase 3 retry successful
   - [ ] Production safeguards implemented
   - [ ] All tests passing
   - [ ] Code reviewed
   - [ ] Monitoring ready
   
   Deployment:
   - [ ] Start bot in paper mode
   - [ ] Verify 1 hour stable
   - [ ] Verify alerting works
   - [ ] Confirm no errors
   
   Post-Deployment:
   - [ ] Monitor 24+ hours
   - [ ] Check daily loss tracking
   - [ ] Verify position sizing
   - [ ] Have rollback ready
   ```

2. **Create Runbook**
   ```markdown
   # Operations Runbook
   
   Starting Bot:
   - Activate venv: source .venv/bin/activate
   - Run: python -m src.bot.app
   - Monitor: tail -f logs/bot.jsonl
   
   Stopping Bot:
   - Graceful: Ctrl+C (closes positions)
   - Emergency: Kill process (positions remain open)
   
   Troubleshooting:
   - [List common issues and solutions]
   ```

3. **Create Monitoring Dashboard**
   - Real-time cycle success rate
   - Request latency trends
   - Daily P&L tracking
   - Error frequency
   - Memory usage

### Deployment Timeline

**Recommended Schedule:**
- Session 1 (Phase 3 Retry): 1-2 days from now
- Session 2 (Production Readiness): 3-4 days from now
- Session 3 (Final Validation): 5-7 days from now
- **Production Deployment: Week 2**

---

## Risk Mitigation

### Identified Risks & Mitigations

| Risk | Severity | Mitigation |
|------|----------|-----------|
| Gateway still times out after 600s interval | HIGH | Have Phase 3 alternative plan (1800s interval, cache bars) |
| Request latency increases during trading hours | MEDIUM | Implement request queuing |
| Memory leaks over 24+ hours | MEDIUM | Monitor memory, implement periodic restart if needed |
| Unexpected order placement | CRITICAL | Keep dry-run enabled until 100% confident |
| Lost connectivity mid-trade | HIGH | Implement connection recovery, OCO as fallback |

### Rollback Procedure

If production deployment fails:
```
1. Stop bot (Ctrl+C)
2. Close all open positions (via IBKR manually if needed)
3. Review logs: tail -f logs/bot.jsonl
4. Identify root cause
5. Fix code or configuration
6. Re-test with StubBroker
7. Retry deployment
```

---

## Documentation Requirements

**Documents to Create/Update:**

1. **Phase 3 Retry Report**
   - Execution timeline
   - Success/failure metrics
   - Comparison with original Phase 3
   - Conclusions and next steps

2. **Production Readiness Report**
   - Implementation status
   - Test results
   - Risk assessment
   - Deployment recommendations

3. **Operations Runbook**
   - Starting/stopping bot
   - Monitoring procedures
   - Troubleshooting guide
   - Emergency procedures

4. **Deployment Plan**
   - Timeline
   - Configuration
   - Monitoring setup
   - Rollback procedures

---

## Success Criteria

### Session 1 Success (Phase 3 Retry)
✅ Bot runs 4+ hours without timeout  
✅ Complete 25+ cycles (SPY @ 600s interval)  
✅ Success rate 95%+  
✅ No memory leaks  

### Session 2 Success (Production Readiness)
✅ Circuit breaker implemented and tested  
✅ Health checks working  
✅ Latency monitoring accurate  
✅ All tests passing  

### Session 3 Success (Final Validation)
✅ All safeguards verified working  
✅ Production documentation complete  
✅ Monitoring dashboard ready  
✅ Ready to deploy  

---

## Questions for Peer Reviewer

1. **Phase 3 Retry Settings:** Are 600s interval + 1 symbol (SPY) reasonable?
2. **Circuit Breaker Threshold:** Is 5 consecutive failures a good threshold?
3. **Health Check Frequency:** Should we check Gateway health every cycle or every 10 cycles?
4. **Request Latency Alert:** Is 8-second threshold reasonable for historical data?
5. **Deployment Timeline:** Is 2-week timeline realistic for production deployment?

---

## Timeline Summary

```
Today (Jan 8):       ✅ Phase 3 analysis complete, peer review ready
Next 1-2 Days:       Phase 3 Retry (Session 1)
  → Adjust settings to 600s + SPY only
  → Run 4+ hours continuous
  → Document results

Days 3-4:             Production Readiness (Session 2)
  → Implement circuit breaker
  → Add health checks
  → Implement latency monitoring
  → Run integration tests

Days 5-7:             Final Validation (Session 3)
  → Complete testing
  → Create runbook
  → Prepare monitoring
  → Ready for deployment

Week 2:               Production Deployment
  → Start in paper mode
  → Monitor 24+ hours
  → Transition to live (if confident)
```

---

## Contact & Questions

For questions about next steps:
- Review ROUND_2_PEER_REVIEW_AND_ASSESSMENT.md (Part 4: Peer Review Questions)
- Review SESSION_DOCUMENTATION_2026-01-08.md (Phase 3 detailed analysis)
- Reference this document for specific action items

---

**Document Created:** January 8, 2026  
**Target Start:** Next available session  
**Status:** Ready for execution  
**Priority:** 🔴 CRITICAL  

