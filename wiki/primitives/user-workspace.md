# User and Workspace

User accounts, authentication, workspace organization, and multi-tenancy.

## User

### Fields
- `id` - Unique identifier
- `email` - User email
- `name` - Display name
- `created_at` - Account creation time
- `updated_at` - Last update time

### Authentication
- Supabase Auth with JWT Bearer tokens
- Token carries `sub` (Supabase user ID)
- Email/password registration
- Password reset flow

### User lifecycle
1. Registration creates Supabase identity
2. Local AccountUser record created
3. Workspace and membership created
4. JWT token issued

## Workspace

### Fields
- `id` - Unique identifier
- `name` - Workspace name
- `slug` - URL-friendly identifier
- `created_at` - Creation time
- `updated_at` - Last update time

### Purpose
- Top-level organizational unit
- Users belong to workspaces
- Projects belong to workspaces
- Billing and subscription scope

### Multi-tenancy
Everything is scoped by `workspace_id`:
- Projects
- Opportunities
- Settings
- Usage metrics

## Membership

### Fields
- `id` - Unique identifier
- `user_id` - References User
- `workspace_id` - References Workspace
- `role` - User role (owner, admin, member)
- `created_at` - Membership creation time

### Roles
- **Owner** - Full control, billing management
- **Admin** - Manage users and projects
- **Member** - Access projects and features

### Access control
Most routes require:
1. Authentication (valid JWT)
2. Workspace membership
3. Role-based permissions

## Invitation

### Fields
- `id` - Unique identifier
- `email` - Invited email
- `workspace_id` - Target workspace
- `role` - Assigned role
- `status` - pending/accepted/expired
- `created_at` - Invitation time

### Flow
1. Owner/admin sends invitation
2. Invitee receives email
3. Invitee accepts and creates account
4. Membership created

## Usage patterns

### Creating a user
```python
from app.services.product.supabase_auth import SupabaseAuthService

auth = SupabaseAuthService()
user = auth.register(email, password)
```

### Checking membership
```python
from app.api.v1.deps import ensure_workspace_membership

ensure_workspace_membership(supabase, workspace_id, user_id)
```

### Getting current workspace
```python
from app.api.v1.deps import get_current_workspace

workspace = get_current_workspace(token)
```

## Database tables

- `account_users` - User records
- `workspaces` - Workspace records
- `memberships` - User-workspace relationships
- `invitations` - Pending invitations

## API endpoints

- `POST /v1/auth/register` - User registration
- `POST /v1/auth/login` - User login
- `GET /v1/workspace` - Get current workspace
- `POST /v1/workspace/invite` - Send invitation

## Security

### JWT validation
- Token expiration checking
- Secret key verification
- Audience validation

### Row Level Security
- Supabase RLS policies
- Workspace-scoped queries
- Role-based access

## Performance

### Caching
- User sessions cached
- Workspace membership cached
- Token validation cached

### Indexes
- User email unique index
- Membership composite index
- Workspace slug unique index

---

*360 Flatmates Platform Documentation*
