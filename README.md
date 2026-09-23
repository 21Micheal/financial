# Financial System

## Overview

The Financial System is the SSO/identity hub for a multi-system platform. It serves as the primary identity backend, federating authentication to Keycloak via a User Storage SPI, and provides a launcher interface for accessing licensed systems.

## Architecture

### Core Components

1. **Django Backend** (`/backend`)
   - User management and authentication
   - Organization and licensing management
   - Internal IDP API for Keycloak federation
   - Audit logging for all events

2. **React Frontend** (`/frontend`)
   - Config-driven login UI (Keycloak/native)
   - System launcher with SSO redirects
   - Break-glass emergency access support

3. **Keycloak Integration** (`~/Projects/idp`)
   - User Storage SPI federates to financial system
   - Live-claim protocol mappers for role injection
   - OIDC client configuration

### Data Model

- **User**: Platform users with roles and organization assignment
- **ClientOrganization**: Client organizations that license systems
- **SystemLicense**: System licenses per organization
- **UserSystemRole**: User roles within specific systems
- **AuditLog**: Immutable audit trail

## Deployment

### Environment Variables

See `.env.example` for all available variables:

- `AUTH_MODE`: `keycloak` (SSO) or `native` (standalone)
- `DATABASE_URL`: PostgreSQL connection string
- `FINANCIAL_INTERNAL_IDP_API_KEY`: Shared secret for Keycloak SPI
- `FRONTEND_URL`: Frontend URL for redirects

### Docker Services

```bash
# Start all services
docker-compose up -d

# Start specific services
docker-compose up -d db redis backend
```

Services:
- `db`: PostgreSQL (port 5433)
- `redis`: Redis (port 6380)
- `backend`: Django/Daphne (port 8001)
- `frontend`: React/Vite (port 3001)

## Keycloak Integration

### User Storage SPI

The financial system provides an internal IDP API at `/internal/idp/` with endpoints:

- `GET /user/lookup/` - User lookup by email
- `GET /user/search/` - User search
- `POST /user/validate/` - Password validation
- `POST /user/create/` - User creation (write-through)
- `PUT /user/update/` - Profile/password update
- `DELETE /user/delete/` - User deactivation

### Configuration

1. Set `FINANCIAL_INTERNAL_IDP_API_KEY` in both `financial-system/.env` and `idp/.env`
2. Configure Keycloak realm with User Storage SPI pointing to financial system
3. Add protocol mappers for `financial_role`, `organization_id`, `is_staff`

## Launcher System

### System Access Flow

1. User logs into financial system (Keycloak or native)
2. Launcher displays licensed systems for user's organization
3. User clicks a system
4. System checks:
   - Organization has license for system
   - User has role provisioned in system
5. If both checks pass, SSO redirect to target system
6. If checks fail, display appropriate error message

### Access States

- **Licensed + Provisioned**: Access granted, SSO redirect
- **Licensed + Not Provisioned**: Blocked with message "Contact your administrator"
- **Not Licensed**: Blocked with message "Organization not licensed"

## Break-Glass Access

Emergency native authentication for platform administrators when Keycloak is unavailable.

### Access Route

```
http://localhost:8001/operations/console
```

### Security Features

- Intentionally obfuscated URL
- Restricted to platform admins in keycloak mode
- Distinct audit logging
- Full session management

See `BREAK_GLASS_README.md` for complete documentation.

## API Endpoints

### Public API

- `GET /api/v1/config/` - Public configuration (auth_mode, etc.)
- `POST /api/v1/auth/login/` - Native login (initiates OTP)
- `POST /api/v1/auth/verify-otp/` - OTP verification
- `GET /api/v1/auth/me/` - Current user info
- `POST /api/v1/token/refresh/` - JWT refresh

### Launcher API

- `GET /api/v1/launcher/systems/` - List licensed systems
- `POST /api/v1/launcher/sso/<system>/` - Initiate SSO redirect

### Internal IDP API

- `GET /internal/idp/user/lookup/` - User lookup
- `GET /internal/idp/user/search/` - User search
- `POST /internal/idp/user/validate/` - Password validation
- `POST /internal/idp/user/create/` - User creation
- `PUT /internal/idp/user/update/` - Profile update
- `DELETE /internal/idp/user/delete/` - User deactivation

## Development

### Backend Development

```bash
# Run migrations
docker-compose exec backend python manage.py migrate

# Create superuser
docker-compose exec backend python manage.py createsuperuser

# Access Django shell
docker-compose exec backend python manage.py shell
```

### Frontend Development

```bash
# Install dependencies
cd frontend
npm install

# Start dev server
npm run dev

# Build for production
npm run build
```

## Audit Events

All significant events are logged in the audit log:

- Authentication events (login, login_failed, break_glass_login)
- User lifecycle (created, updated, deleted, activated, deactivated)
- Licensing events (license_granted, license_revoked)
- System role events (role_granted, role_revoked)
- SSO events (system_access_granted, system_access_denied)

## Migration from DMS

The financial system is replacing DMS as the identity backend:

1. **Completed**: Financial system backend and frontend
2. **Pending**: Keycloak SPI provider for financial system
3. **Pending**: DMS internal IDP API simplification (role-only endpoint)
4. **Pending**: Keycloak realm reconfiguration to use financial SPI

## Security Considerations

- All internal IDP endpoints protected by shared secret
- Authentication classes explicitly set to empty on internal views
- Break-glass URL intentionally obfuscated
- Audit logging for all authentication events
- Session management with JWT tokens
- Proper CORS configuration

## Troubleshooting

### Database Connection Issues

- Verify PostgreSQL is running: `docker-compose ps db`
- Check DATABASE_URL in .env
- Ensure network connectivity between containers

### Keycloak Federation Issues

- Verify FINANCIAL_INTERNAL_IDP_API_KEY matches in both .env files
- Check internal IDP API is accessible from Keycloak container
- Review Keycloak logs for SPI errors
- Verify protocol mapper configuration

### Frontend Build Issues

- Clear node_modules: `rm -rf node_modules && npm install`
- Check Vite configuration
- Verify API base URL in environment

## Contact

For issues or questions:
- Platform operations team
- Review audit logs for troubleshooting
- Check Keycloak admin console for federation status
