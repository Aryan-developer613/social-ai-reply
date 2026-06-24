# Cleanup opportunities

Dead code, TODOs, complexity hotspots, and maintenance tasks.

## Overview

This section identifies areas of the codebase that could benefit from cleanup, refactoring, or maintenance. These are not bugs, but opportunities to improve code quality.

## Dead code

### Unused files
- `app/services/product/relevance.py` - Legacy scoring logic
- Some test fixtures may be unused
- Deprecated API endpoints

### Unused exports
- Some utility functions may not be imported
- Old configuration options
- Deprecated model fields

## TODOs and FIXMEs

### Code comments
Search for TODO, FIXME, HACK comments:
```bash
grep -r "TODO" app/ --include="*.py"
grep -r "FIXME" app/ --include="*.py"
grep -r "HACK" app/ --include="*.py"
```

### Common patterns
- "TODO: Add error handling"
- "FIXME: This is a temporary workaround"
- "HACK: Quick fix for now"

## Complexity hotspots

### Large files
- `app/services/product/relevance.py` - 38,580 bytes
- `app/services/product/relevance_v2.py` - 28,083 bytes
- `app/services/product/scanner.py` - 19,660 bytes

### Complex functions
- Scoring algorithms
- LLM integration code
- Database query builders

### Deep nesting
- Some route handlers have deep nesting
- Complex conditional logic
- Multiple levels of callbacks

## Dependency freshness

### Python dependencies
Check for outdated packages:
```bash
uv pip list --outdated
```

### Node.js dependencies
Check for outdated packages:
```bash
npm outdated
```

### Security updates
- Monitor Dependabot alerts
- Review security advisories
- Update vulnerable packages

## Code quality

### Linting issues
Run linting to find issues:
```bash
uv run ruff check app/ tests/
```

### Type coverage
- Add type hints to functions
- Remove `: any` types
- Improve type safety

### Documentation
- Add missing docstrings
- Update outdated comments
- Improve API documentation

## Testing gaps

### Missing tests
- Some services lack unit tests
- Integration tests limited
- E2E tests manual

### Test quality
- Flaky tests need fixing
- Slow tests need optimization
- Mocking improvements needed

## Performance issues

### Database queries
- N+1 query problems
- Missing indexes
- Slow queries

### Memory usage
- Large object creation
- Memory leaks
- Cache optimization

### API response times
- Slow endpoints
- Large payload sizes
- Missing caching

## Refactoring opportunities

### Code duplication
- Similar patterns across agents
- Repeated database queries
- Common utility functions

### Module organization
- Some modules are too large
- Poor separation of concerns
- Circular dependencies

### API design
- Inconsistent naming
- Missing validation
- Error handling gaps

## Maintenance tasks

### Regular updates
- Dependency updates
- Security patches
- Documentation updates

### Monitoring
- Add more logging
- Improve metrics
- Better error tracking

### Automation
- More test automation
- CI/CD improvements
- Code generation

## Priority matrix

### High priority
- Security vulnerabilities
- Critical bugs
- Performance issues

### Medium priority
- Code quality improvements
- Test coverage
- Documentation

### Low priority
- Style consistency
- Minor refactoring
- Nice-to-have features

---

*360 Flatmates Platform Documentation*
