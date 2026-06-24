# Development workflow

Step-by-step guide for developing in Social AI Reply.

## Setting up your environment

### 1. Fork and clone
```bash
# Fork on GitHub, then clone
git clone git@github.com:YOUR_USERNAME/social-ai-reply.git
cd social-ai-reply
```

### 2. Configure environment
```bash
cp .env.example .env
# Edit .env with your Supabase credentials
```

### 3. Install dependencies
```bash
# Backend
uv sync --extra dev

# Frontend
cd web
npm install
```

### 4. Apply database migrations
Run the SQL in `app/db/migrations/001_multi_agent_platform.sql` in your Supabase SQL Editor.

### 5. Start development servers
```bash
# Terminal 1: Backend
uv run uvicorn app.main:app --reload

# Terminal 2: Frontend
cd web
npm run dev
```

## Daily development routine

### Morning setup
1. Pull latest changes: `git pull origin main`
2. Update dependencies if needed
3. Start development servers
4. Verify everything works

### Making changes
1. **Create feature branch**: `git checkout -b feature/your-feature`
2. **Make changes** in small, focused commits
3. **Test frequently** - don't wait until the end
4. **Run linters** before committing
5. **Commit often** with clear messages

### Before pushing
1. Run backend tests: `uv run pytest -q`
2. Run frontend build: `cd web && npm run build`
3. Check linting: `uv run ruff check app/ tests/`
4. Review your changes: `git diff`

## Git workflow

### Branch strategy
- `main` - Production-ready code
- `feature/*` - New features
- `fix/*` - Bug fixes
- `docs/*` - Documentation changes

### Commit workflow
```bash
# Stage changes
git add .

# Commit with message
git commit -m "Add feature: description"

# Push to your fork
git push origin feature/your-feature
```

### Pull request workflow
1. Create pull request on GitHub
2. Fill out PR template
3. Link related issues
4. Request review from maintainers
5. Address feedback
6. Merge when approved

## Code review process

### As a reviewer
- Review code for correctness and style
- Check for security issues
- Verify test coverage
- Provide constructive feedback
- Approve when satisfied

### As an author
- Respond to feedback promptly
- Make requested changes
- Re-request review after updates
- Keep PR description updated

## Testing workflow

### Backend testing
```bash
# Run all tests
uv run pytest -q

# Run specific test file
uv run pytest tests/unit/test_security.py -v

# Run with coverage
uv run pytest --cov=app tests/
```

### Frontend testing
```bash
# Type check and build
cd web && npm run build

# Run unit tests
cd web && npm run test
```

## Debugging workflow

### Backend debugging
1. Check logs in terminal
2. Use `print()` or `logging` for debugging
3. Test API endpoints with `curl` or Postman
4. Check database state in Supabase dashboard

### Frontend debugging
1. Use browser developer tools
2. Check console for errors
3. Use React DevTools
4. Test network requests

## Deployment workflow

### Staging deployment
1. Push to `main` branch
2. Automatic deployment to staging
3. Test in staging environment
4. Verify all features work

### Production deployment
1. Create release tag
2. Deploy to production
3. Monitor for issues
4. Rollback if needed

## Common tasks

### Adding a new API endpoint
1. Create route in `app/api/v1/routes/`
2. Add table operations in `app/db/tables/`
3. Create Pydantic schemas in `app/schemas/v1/`
4. Add tests for the endpoint
5. Update API documentation

### Adding a new frontend page
1. Create page in `web/app/app/`
2. Add API client functions in `web/lib/api/`
3. Create components in `web/components/`
4. Add navigation in app shell
5. Test responsive design

### Adding a new agent
1. Create agent in `app/services/agents/`
2. Add agent routes in `app/api/v1/routes/`
3. Register agent in scheduler
4. Add frontend controls
5. Document agent functionality

## Getting help

- Check existing code patterns
- Review documentation in `wiki/`
- Ask in GitHub issues
- Join community discussions

---

*360 Flatmates Platform Documentation*
