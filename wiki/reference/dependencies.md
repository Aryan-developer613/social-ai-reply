# Dependencies

Python and Node.js dependencies for Social AI Reply. See `pyproject.toml` and `web/package.json` for exact versions.

## Python dependencies

### Core dependencies

| Package | Purpose |
|---------|---------|
| fastapi | Web framework |
| uvicorn | ASGI server |
| pydantic | Data validation |
| pydantic-settings | Configuration management |
| supabase | Supabase client |
| httpx | HTTP client |

### LLM providers

| Package | Purpose |
|---------|---------|
| google-generativeai | Gemini provider |
| openai | OpenAI provider |
| anthropic | Claude provider |
| perplexity | Perplexity provider |

### Machine learning

| Package | Version | Purpose |
|---------|---------|---------|
| scikit-learn | 1.5.0 | TF-IDF embeddings |
| sentence-transformers | 3.0.0 | Neural embeddings (optional) |

### Development dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| pytest | 8.0.0 | Testing framework |
| pytest-cov | 5.0.0 | Coverage reporting |
| ruff | 0.6.0 | Linting and formatting |
| mypy | 1.10.0 | Type checking |

## Node.js dependencies

### Core dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| next | 16.0.0 | React framework |
| react | 19.0.0 | UI library |
| react-dom | 19.0.0 | React DOM |

### UI libraries

| Package | Version | Purpose |
|---------|---------|---------|
| tailwindcss | 4.0.0 | CSS framework |
| @base-ui/react | 1.0.0 | Component primitives |
| class-variance-authority | 0.7.0 | Component variants |
| clsx | 2.1.0 | Class name utility |
| tailwind-merge | 2.3.0 | Tailwind class merging |

### State management

| Package | Version | Purpose |
|---------|---------|---------|
| zustand | 4.5.0 | State management |

### Development dependencies

| Package | Version | Purpose |
|---------|---------|---------|
| typescript | 5.4.0 | Type checking |
| vitest | 1.6.0 | Testing framework |
| eslint | 8.57.0 | Linting |
| prettier | 3.2.0 | Code formatting |

## Dependency management

### Python

```bash
# Install dependencies
uv sync --extra dev

# Add new dependency
uv add package-name

# Update dependencies
uv lock --upgrade

# Export requirements
uv pip compile pyproject.toml -o requirements.txt
```

### Node.js

```bash
# Install dependencies
npm install

# Add new dependency
npm install package-name

# Update dependencies
npm update

# Audit for vulnerabilities
npm audit
```

## Version pinning

### Python
- Uses `uv.lock` for exact versions
- `pyproject.toml` specifies ranges
- Lock file committed to git

### Node.js
- Uses `package-lock.json` for exact versions
- `package.json` specifies ranges
- Lock file committed to git

## Security

### Vulnerability scanning

```bash
# Python
uv pip audit

# Node.js
npm audit
```

### Dependabot
- Automated dependency updates
- Security patch notifications
- PR creation for updates

## Performance

### Bundle size
- Frontend bundle analyzed with `next/bundle-analyzer`
- Tree shaking for unused code
- Code splitting for routes

### Python dependencies
- Minimal dependencies for fast startup
- Optional dependencies for advanced features
- Lazy loading for heavy libraries

## Compatibility

### Python
- Requires Python 3.11+
- Tested on 3.11, 3.12
- CI runs on multiple versions

### Node.js
- Requires Node.js 20+
- Tested on 20, 22
- CI runs on multiple versions

## License

### Open source licenses
- MIT License (most dependencies)
- Apache 2.0 (some dependencies)
- BSD License (some dependencies)

### Commercial licenses
- Some LLM providers require commercial licenses
- Supabase has free and paid tiers

## Updates

### Regular updates
- Monthly dependency reviews
- Security patch immediate updates
- Major version updates quarterly

### Update process
1. Review changelog
2. Test in development
3. Update lock files
4. Run full test suite
5. Deploy to staging
6. Monitor for issues

---

*360 Flatmates Platform Documentation*
