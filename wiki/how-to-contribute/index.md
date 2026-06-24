# How to contribute

Guidelines for contributing to Social AI Reply.

## Getting started

1. **Fork the repository** on GitHub
2. **Clone your fork** locally
3. **Set up the development environment** following [Getting started](../overview/getting-started.md)
4. **Create a feature branch** from `main`
5. **Make your changes** following the patterns in [Patterns and conventions](patterns-and-conventions.md)
6. **Test your changes** thoroughly
7. **Submit a pull request** with a clear description

## Development workflow

### Branch naming
- `feature/description` - New features
- `fix/description` - Bug fixes
- `docs/description` - Documentation changes
- `refactor/description` - Code refactoring

### Commit messages
- Use present tense: "Add feature" not "Added feature"
- Use imperative mood: "Fix bug" not "Fixes bug"
- Keep first line under 72 characters
- Reference issues when applicable: "Fix #123"

### Code review process
1. Submit pull request with clear description
2. Ensure all tests pass
3. Address review feedback
4. Get approval from maintainers
5. Merge using squash and merge

## Testing requirements

### Backend
- Write tests for new functionality
- Ensure existing tests still pass
- Run `uv run pytest -q` before submitting
- Aim for meaningful coverage, not just line coverage

### Frontend
- Test component behavior, not implementation details
- Use Vitest for unit tests
- Run `cd web && npm run build` to check types
- Test responsive design on different screen sizes

## Documentation

### When to update docs
- Adding new features or endpoints
- Changing environment variables
- Modifying setup instructions
- Adding new configuration options

### What to document
- API endpoints and parameters
- Environment variables and their effects
- Configuration options
- Troubleshooting guides

## Code quality

### Linting
- Run linters before committing
- Fix all linting errors
- Use consistent formatting

### Type safety
- Add type hints to Python code
- Use TypeScript types in frontend
- Avoid `: any` types
- Handle error types properly

## Pull request checklist

Before submitting a pull request:

- [ ] Code follows project conventions
- [ ] Tests pass locally
- [ ] Linting passes
- [ ] Documentation updated (if applicable)
- [ ] Commit messages are clear
- [ ] PR description explains the changes
- [ ] No sensitive data or secrets included
- [ ] No breaking changes (or clearly documented)

## Getting help

- Check existing documentation in `wiki/`
- Review code patterns in existing files
- Ask questions in GitHub issues
- Join community discussions

## Code of conduct

- Be respectful and inclusive
- Focus on constructive feedback
- Help others learn and grow
- Maintain a positive environment

---

*360 Flatmates Platform Documentation*
