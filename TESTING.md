# Test README

## Running Tests

### Backend Tests (pytest)

```bash
cd backend

# Install test dependencies
pip install -r requirements.txt

# Run all tests
python -m pytest tests/ -v

# Run specific test file
python -m pytest tests/test_process_endpoint.py -v

# Run with coverage
python -m pytest tests/ --cov=app --cov-report=html
```

### Frontend Tests (vitest)

```bash
cd frontend

# Install test dependencies
npm install

# Run tests in watch mode
npm test

# Run tests once
npm test -- --run

# Run with UI
npm run test:ui
```

## Test Coverage

### Backend Tests (`tests/test_process_endpoint.py`)

**Endpoint Tests:**
- Health check endpoint availability
- Missing file rejection
- Unsupported file type rejection
- Empty PDF rejection
- Valid PDF processing with claim data
- Missing fields fallback values
- Database persistence graceful skip

**Pipeline Logic Tests:**
- Low risk score calculation and recommendation
- High risk score calculation and recommendation
- Email draft generation with key fields
- WhatsApp message generation with key fields

### Frontend Tests (`src/hooks/__tests__/useClaimAgent.test.js`)

**State Management:**
- Initial state values
- Agent initialization
- Demo mode toggle

**Demo Mode:**
- Processing without file upload
- Demo payload loading
- Terminal log generation

**File Upload:**
- File upload handling
- Rejection without file/demo
- File-based processing

**Processing Flow:**
- Processing state management
- Agent status updates
- Current step updates

**Error Handling:**
- API error graceful handling
- Network error graceful handling
- Error message population

**Reset:**
- Full state reset to initial values

**Terminal Logging:**
- Timestamp injection
- Log level markers (SYSTEM, INFO, SUCCESS)

**Risk Score:**
- Risk score update after processing

## Expected Test Output

```
Backend:
==== test session starts ====
collected 14 items

tests/test_process_endpoint.py::TestProcessEndpoint::test_health_endpoint PASSED
tests/test_process_endpoint.py::TestProcessEndpoint::test_process_missing_file PASSED
...
==== 14 passed in 2.34s ====

Frontend:
 ✓ src/hooks/__tests__/useClaimAgent.test.js (18)
   ✓ useClaimAgent hook
     ✓ Initial State (3)
     ✓ Demo Mode (3)
     ✓ File Upload (3)
     ✓ Processing Flow (3)
     ✓ Error Handling (2)
     ✓ Reset Function (1)
     ✓ Terminal Logging (2)
     ✓ Risk Score Update (1)

 Test Files  1 passed (1)
      Tests  18 passed (18)
```
