# Debugging

Logs, common errors, and troubleshooting runbook for Social AI Reply.

## Logging

### Backend logging
- Structured JSON logging via `app/core/logging.py`
- Logs to stdout for containerized deployment
- Log levels: DEBUG, INFO, WARNING, ERROR, CRITICAL

**Configuration:**
```python
# In app/main.py
setup_logging("INFO")
logger = logging.getLogger(__name__)
```

**Usage:**
```python
logger.info("Starting RedditFlow API...")
logger.warning("Running with multiple workers...")
logger.error("Supabase health check failed: %s", e)
```

### Frontend logging
- Browser console logging
- Error boundaries capture React errors
- Network request logging in dev tools

## Common errors

### Backend errors

**Database connection errors:**
```
ValueError: SUPABASE_URL is not configured
```
**Solution:** Check `.env` file has correct Supabase URL

**Authentication errors:**
```
401 Unauthorized
```
**Solution:** Verify JWT token is valid and not expired

**Rate limiting errors:**
```
429 Too Many Requests
```
**Solution:** Wait or adjust rate limits in `app/middleware.py`

**LLM provider errors:**
```
RuntimeError: No LLM provider available
```
**Solution:** Configure `GEMINI_API_KEY` or set `LLM_PROVIDER` to available provider

### Frontend errors

**API connection errors:**
```
Failed to fetch
```
**Solution:** Check `NEXT_PUBLIC_API_BASE_URL` in `.env.local`

**Authentication errors:**
```
Auth session missing
```
**Solution:** Clear browser storage and re-login

**TypeScript errors:**
```
Type 'string' is not assignable to type 'number'
```
**Solution:** Fix type mismatch in code

## Troubleshooting runbook

### Backend won't start

1. **Check environment variables:**
   ```bash
   cat .env | grep -E "SUPABASE|GEMINI"
   ```

2. **Check Supabase connection:**
   ```bash
   curl http://localhost:8000/health
   ```

3. **Check logs:**
   ```bash
   uv run uvicorn app.main:app --reload 2>&1 | tee logs.txt
   ```

### Frontend won't start

1. **Check Node.js version:**
   ```bash
   node --version  # Should be 20+
   ```

2. **Check dependencies:**
   ```bash
   cd web && npm install
   ```

3. **Check environment:**
   ```bash
   cat .env.local | grep -E "NEXT_PUBLIC"
   ```

### Database issues

1. **Check migrations applied:**
   - Go to Supabase dashboard
   - Check if tables exist in SQL Editor

2. **Check permissions:**
   - Verify RLS policies
   - Check API keys in Supabase

3. **Check connection:**
   ```bash
   # Test Supabase connection
   python -c "from supabase import create_client; client = create_client('URL', 'KEY'); print(client.table('test').select('*').execute())"
   ```

### LLM issues

1. **Check API key is set (without printing the value):**
   ```bash
   [ -z "$GEMINI_API_KEY" ] && echo "GEMINI_API_KEY is not set" || echo "GEMINI_API_KEY is set"
   ```

2. **Check provider configuration:**
   ```bash
   cat .env | grep -E "GEMINI|OPENAI|LLM_PROVIDER"
   ```

3. **Test LLM connection:**
   ```bash
   curl -X POST http://localhost:8000/v1/test-llm
   ```

### Performance issues

1. **Check database queries:**
   - Use Supabase dashboard to monitor queries
   - Check for slow queries

2. **Check memory usage:**
   ```bash
   ps aux | grep uvicorn
   ```

3. **Check network:**
   ```bash
   curl -w "@curl-format.txt" -o /dev/null -s http://localhost:8000/health
   ```

## Debugging tools

### Backend debugging
- **Python debugger:** `pdb` or `ipdb`
- **Logging:** `logger.debug()` statements
- **API testing:** `curl` or Postman
- **Database:** Supabase dashboard

### Frontend debugging
- **Browser dev tools:** Console, Network, Elements
- **React DevTools:** Component inspection
- **TypeScript:** Compile-time error checking
- **Network:** Check API requests

## Error reporting

### Backend errors
- Structured logging with context
- Error codes in responses
- Stack traces in logs

### Frontend errors
- Error boundaries catch React errors
- Console errors with stack traces
- Network request failures

## Monitoring

### Health checks
```bash
# Backend health
curl http://localhost:8000/health

# Database connectivity
curl http://localhost:8000/ready
```

### Logs
```bash
# Backend logs
tail -f logs.txt

# Frontend logs
# Check browser console
```

## Common pitfalls

### Environment variables
- Variables not loaded (check `.env` file)
- Variables not prefixed correctly (`NEXT_PUBLIC_` for frontend)
- Variables not set in deployment environment

### Database
- Missing migrations
- Incorrect RLS policies
- Connection pool exhaustion

### Authentication
- JWT token expired
- Incorrect secret key
- CORS issues

### LLM
- API key invalid or expired
- Provider not configured
- Rate limits exceeded

## Getting help

- Check existing documentation in `wiki/`
- Review error messages carefully
- Search GitHub issues
- Ask in community discussions

---

*360 Flatmates Platform Documentation*
