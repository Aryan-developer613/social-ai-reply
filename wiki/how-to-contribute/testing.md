# Testing

Testing frameworks, patterns, and how to run tests in Social AI Reply.

## Testing philosophy

- Test behavior, not implementation details
- Write meaningful tests that catch real bugs
- Keep tests fast and reliable
- Focus on edge cases and error conditions

## Backend testing

### Framework
- **pytest** for Python testing
- **Supabase local development** for database testing
- **Test fixtures** in `conftest.py` for common setup

### Running tests
```bash
# Run all tests
uv run pytest -q

# Run specific test file
uv run pytest tests/unit/test_security.py -v

# Run with verbose output
uv run pytest -v

# Run with coverage
uv run pytest --cov=app tests/
```

### Test structure
```
tests/
├── conftest.py          # Test fixtures and configuration
├── unit/               # Unit tests
│   ├── test_security.py
│   ├── test_relevance_v2.py
│   └── ...
├── integration/        # Integration tests
└── ...
```

### Writing backend tests

**Basic test structure:**
```python
import pytest
from app.services.product.relevance_v2 import RelevanceEngine

def test_relevance_scoring():
    """Test that relevance scoring works correctly."""
    engine = RelevanceEngine()
    score = engine.calculate_score(
        keywords=["python", "fastapi"],
        text="I need help with FastAPI in Python"
    )
    assert score >= 70  # Should be relevant
```

**Using fixtures:**
```python
@pytest.fixture
def sample_opportunity():
    return {
        "title": "Need help with FastAPI",
        "body": "I'm building a REST API with FastAPI and need guidance",
        "subreddit": "r/Python",
        "score": 15
    }

def test_opportunity_processing(sample_opportunity):
    """Test opportunity processing with sample data."""
    result = process_opportunity(sample_opportunity)
    assert result["status"] == "processed"
```

**Database tests:**
```python
def test_database_operations(supabase_client):
    """Test database operations with test client."""
    # Create
    result = supabase_client.table("projects").insert({
        "name": "Test Project",
        "workspace_id": 1
    }).execute()
    assert result.data[0]["name"] == "Test Project"
    
    # Read
    project = supabase_client.table("projects").select("*").eq("id", result.data[0]["id"]).execute()
    assert len(project.data) == 1
    
    # Cleanup
    supabase_client.table("projects").delete().eq("id", result.data[0]["id"]).execute()
```

### Test fixtures (conftest.py)
```python
import pytest
from fastapi.testclient import TestClient
from app.main import app

@pytest.fixture
def client():
    """Unauthenticated test client."""
    return TestClient(app)

@pytest.fixture
def authed_client(authed_headers):
    """Authenticated test client."""
    return TestClient(app, headers=authed_headers)

@pytest.fixture
def authed_headers():
    """Headers with valid authentication."""
    # Generate test JWT token
    token = create_test_token()
    return {"Authorization": f"Bearer {token}"}
```

## Frontend testing

### Framework
- **Vitest** for unit testing
- **React Testing Library** for component testing
- **TypeScript** for type safety

### Running tests
```bash
# Type check and build (serves as test)
cd web && npm run build

# Run unit tests
cd web && npm run test
```

### Writing frontend tests

**Component test:**
```typescript
import { render, screen } from '@testing-library/react';
import { Button } from '@/components/ui/button';

test('renders button with text', () => {
  render(<Button>Click me</Button>);
  expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
});
```

**Hook test:**
```typescript
import { renderHook } from '@testing-library/react';
import { useAuth } from '@/hooks/use-auth';

test('useAuth returns auth state', () => {
  const { result } = renderHook(() => useAuth());
  expect(result.current.user).toBeDefined();
});
```

### Testing patterns

**Testing API calls:**
```typescript
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/projects', (req, res, ctx) => {
    return res(ctx.json([{ id: 1, name: 'Test Project' }]));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());

test('fetches projects', async () => {
  render(<ProjectList />);
  expect(await screen.findByText('Test Project')).toBeInTheDocument();
});
```

## Integration testing

### API integration tests
```python
def test_api_endpoint_integration(client):
    """Test API endpoint with real database."""
    # Create test data
    response = client.post("/v1/projects", json={
        "name": "Test Project",
        "workspace_id": 1
    })
    assert response.status_code == 201
    
    # Verify response
    data = response.json()
    assert data["name"] == "Test Project"
```

### End-to-end testing
- Manual testing for critical user flows
- Automated testing for API endpoints
- Performance testing for scoring algorithms

## Test data management

### Test databases
- Use Supabase local development for testing
- Separate test database from production
- Clean up test data after tests

### Mocking
- Mock external services (LLM, Reddit API)
- Use test fixtures for consistent data
- Avoid mocking database operations when possible

## Continuous integration

### GitHub Actions
- Run tests on every push
- Run linting on every PR
- Build verification for frontend
- Code coverage reporting

### Pre-commit hooks
- Run linting before commit
- Run type checks
- Verify test passing

## Test coverage

### Measuring coverage
```bash
# Backend coverage
uv run pytest --cov=app tests/

# Generate HTML report
uv run pytest --cov=app --cov-report=html tests/
```

### Coverage goals
- Aim for meaningful coverage, not just line coverage
- Focus on critical business logic
- Test error conditions and edge cases
- Keep tests maintainable

## Debugging tests

### Common issues
- **Flaky tests**: Check for timing issues or shared state
- **Slow tests**: Optimize database queries or mock external services
- **False positives**: Verify test assertions are correct

### Debugging tools
- Use `print()` or `logging` in tests
- Use `pytest --pdb` for debugging
- Use browser developer tools for frontend tests

## Performance testing

### Backend performance
- Load testing with `locust` or similar
- Database query optimization
- Caching strategies

### Frontend performance
- Bundle size analysis
- Rendering performance
- Memory leak detection

---

*360 Flatmates Platform Documentation*
