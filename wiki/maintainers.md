# Maintainers

Subsystem ownership and contact information for Social AI Reply.

## Ownership matrix

| Subsystem | Primary owner | Secondary owner | Last active |
|-----------|---------------|-----------------|-------------|
| Backend API | sakshammittal | - | Current |
| Frontend | sakshammittal | - | Current |
| Database | sakshammittal | - | Current |
| LLM Integration | sakshammittal | - | Current |
| Agents | sakshammittal | - | Current |
| Deployment | sakshammittal | - | Current |
| Documentation | sakshammittal | - | Current |

## Contact

### Primary maintainer
- **Name**: sakshammittal
- **GitHub**: @sakshammittal
- **Email**: (check GitHub profile)

### Response times
- **Critical issues**: 24 hours
- **Bug fixes**: 1-2 business days
- **Feature requests**: 1 week
- **Documentation**: 1 week

## Responsibilities

### Code review
- All pull requests require review
- Focus on correctness, security, and maintainability
- Ensure tests pass and documentation updates

### Issue triage
- Label issues appropriately
- Prioritize bugs and security issues
- Close stale issues

### Release management
- Version bumps follow semantic versioning
- Changelog updates for user-facing changes
- Deployment coordination

## Subsystem expertise

### Backend API
- FastAPI routes and middleware
- Authentication and authorization
- API design and documentation

### Frontend
- Next.js App Router
- React 19 patterns
- Tailwind CSS and shadcn/ui

### Database
- Supabase Postgres
- Schema design and migrations
- Query optimization

### LLM Integration
- Provider abstraction
- Model selection and fallback
- Cost optimization

### Agents
- Multi-agent architecture
- Scheduling and orchestration
- Agent-specific logic

### Deployment
- Railway backend deployment
- Netlify frontend deployment
- Environment configuration

## Onboarding

### New contributors
1. Read `wiki/overview/getting-started.md`
2. Review `wiki/how-to-contribute/index.md`
3. Check `wiki/how-to-contribute/patterns-and-conventions.md`
4. Look at existing code for patterns

### Code review process
1. Fork repository
2. Create feature branch
3. Make changes with tests
4. Submit pull request
5. Address review feedback
6. Merge when approved

## Communication

### GitHub
- Issues for bugs and feature requests
- Pull requests for code changes
- Discussions for questions and ideas

### Response expectations
- Acknowledge issues within 24 hours
- Review PRs within 1 week
- Close stale issues after 30 days

## Release process

### Versioning
- **Major**: Breaking changes
- **Minor**: New features
- **Patch**: Bug fixes

### Release steps
1. Update version in `pyproject.toml` and `package.json`
2. Update changelog
3. Create git tag
4. Deploy to production
5. Monitor for issues

## Emergency procedures

### Critical bugs
1. Create hotfix branch
2. Fix the issue
3. Add tests
4. Deploy immediately
5. Notify users if needed

### Security incidents
1. Assess impact
2. Contain the issue
3. Fix and patch
4. Notify affected users
5. Post-mortem review

## Code ownership

### CODEOWNERS file
Not currently configured. Contact sakshammittal for subsystem-specific questions.

### Git history
Recent contributors can be identified via:
```bash
git log --format='%aN' | sort | uniq -c | sort -rn
```

## Maintenance schedule

### Regular maintenance
- **Weekly**: Dependency updates review
- **Monthly**: Security audit
- **Quarterly**: Performance review
- **Annually**: Architecture review

### Documentation updates
- Update wiki with code changes
- Review and update README
- Update API documentation

---

*360 Flatmates Platform Documentation*
