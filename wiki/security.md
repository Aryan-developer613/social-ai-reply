# Security

Authentication, authorization, secrets management, and security practices.

## Authentication

### Supabase Auth
- JWT Bearer tokens
- Email/password registration
- Password reset flow
- Session management

### Token structure
```json
{
  "sub": "user_id",
  "email": "user@example.com",
  "workspace_id": 1,
  "role": "member",
  "exp": 1234567890
}
```

### Token validation
- Signature verification
- Expiration checking
- Audience validation
- Secret key rotation

## Authorization

### Multi-tenancy
- Workspace-scoped access
- Project-level permissions
- Role-based control

### Roles
- **Owner** - Full control, billing
- **Admin** - User and project management
- **Member** - Feature access

### Access patterns
```python
# Authentication check
user = get_current_user(token)

# Workspace membership check
ensure_workspace_membership(supabase, workspace_id, user_id)

# Role-based check
if user["role"] != "owner":
    raise ForbiddenError("Owner required")
```

## Secrets management

### Environment variables
- Never commit secrets to git
- Use `.env` files locally
- Set in deployment dashboard

### Required secrets
```bash
SUPABASE_SECRET_KEY=service_role_key
SUPABASE_JWT_SECRET=jwt_secret
ENCRYPTION_KEY=encryption_key
GEMINI_API_KEY=llm_api_key
```

### Secret rotation
- Rotate Supabase keys periodically
- Update encryption key if compromised
- Rotate API keys regularly

## Data protection

### Encryption at rest
- Supabase encrypts data at rest
- Sensitive fields encrypted with Fernet
- Encryption key managed separately

### Encryption in transit
- HTTPS enforced in production
- TLS for all API communication
- Secure WebSocket connections

### PII handling
- Email addresses stored securely
- API keys encrypted
- No unnecessary data collection

## API security

### Rate limiting
- Prevents abuse
- Per-endpoint limits
- IP-based tracking

### Input validation
- Pydantic models validate input
- SQL injection prevention
- XSS protection

### CORS configuration
- Restricted origins
- Credential handling
- Method limitations

## Database security

### Row Level Security
- Supabase RLS policies
- Workspace-scoped queries
- Automatic filtering

### Query safety
- Parameterized queries
- No raw SQL in routes
- Supabase SDK only

### Access control
- Service role key for admin
- Anon key for public
- JWT for authenticated

## Logging and monitoring

### Security logging
- Authentication attempts
- Permission failures
- Suspicious activity

### Audit trail
- User actions logged
- Data changes tracked
- API access recorded

## Vulnerability management

### Dependencies
- Regular updates
- Security scanning
- Automated alerts

### Code scanning
- Linting for security issues
- Static analysis
- Manual review

## Incident response

### Detection
- Monitor error rates
- Track unusual patterns
- User reports

### Response
- Immediate containment
- Investigation
- Remediation
- Communication

### Recovery
- Restore from backups
- Rotate compromised secrets
- Update security measures

## Compliance

### Data retention
- User data retention policies
- Automatic cleanup
- Right to deletion

### Privacy
- Minimal data collection
- No unnecessary tracking
- User consent

## Best practices

### Development
- Never hardcode secrets
- Use environment variables
- Validate all input
- Handle errors securely

### Deployment
- Use HTTPS
- Enable rate limiting
- Monitor logs
- Regular backups

### Operations
- Rotate secrets regularly
- Review access logs
- Update dependencies
- Security training

---

*360 Flatmates Platform Documentation*
