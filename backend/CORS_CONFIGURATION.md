# CORS Configuration Guide

## Overview

The application now uses environment variables for CORS (Cross-Origin Resource Sharing) configuration, providing flexibility for different deployment environments.

## Environment Variables

### CORS_ORIGINS
**Type**: String (comma-separated list)  
**Default**: `http://localhost:5173,http://localhost:5174,http://localhost:3000`  
**Description**: List of allowed origins that can access the API

**Examples**:
```bash
# Development (multiple local ports)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000

# Production (single domain)
CORS_ORIGINS=https://myapp.com

# Production (multiple domains)
CORS_ORIGINS=https://myapp.com,https://www.myapp.com,https://admin.myapp.com

# Mixed environments
CORS_ORIGINS=http://localhost:5173,https://staging.myapp.com,https://myapp.com
```

### CORS_ALLOW_CREDENTIALS
**Type**: Boolean  
**Default**: `true`  
**Description**: Whether to allow credentials (cookies, authorization headers) in CORS requests

**Examples**:
```bash
# Allow credentials (recommended for authenticated apps)
CORS_ALLOW_CREDENTIALS=true

# Disable credentials
CORS_ALLOW_CREDENTIALS=false
```

### CORS_ALLOW_METHODS
**Type**: String (comma-separated list or "*")  
**Default**: `*`  
**Description**: HTTP methods allowed in CORS requests

**Examples**:
```bash
# Allow all methods (default)
CORS_ALLOW_METHODS=*

# Restrict to specific methods
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE

# Read-only API
CORS_ALLOW_METHODS=GET,OPTIONS
```

### CORS_ALLOW_HEADERS
**Type**: String (comma-separated list or "*")  
**Default**: `*`  
**Description**: HTTP headers allowed in CORS requests

**Examples**:
```bash
# Allow all headers (default)
CORS_ALLOW_HEADERS=*

# Restrict to specific headers
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Requested-With

# Custom headers
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-API-Key,X-Custom-Header
```

## Configuration Examples

### Development Environment

```bash
# .env (development)
CORS_ORIGINS=http://localhost:5173,http://localhost:5174,http://localhost:3000
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*
```

### Staging Environment

```bash
# .env (staging)
CORS_ORIGINS=https://staging-frontend.myapp.com,https://staging-admin.myapp.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=*
CORS_ALLOW_HEADERS=*
```

### Production Environment

```bash
# .env (production)
CORS_ORIGINS=https://myapp.com,https://www.myapp.com
CORS_ALLOW_CREDENTIALS=true
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,OPTIONS
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Requested-With
```

### Restrictive Production (API-only)

```bash
# .env (production - API only)
CORS_ORIGINS=https://api.myapp.com
CORS_ALLOW_CREDENTIALS=false
CORS_ALLOW_METHODS=GET,POST
CORS_ALLOW_HEADERS=Content-Type,Authorization
```

## Security Best Practices

### 1. Restrict Origins in Production
```bash
# ❌ BAD - Too permissive
CORS_ORIGINS=*

# ✅ GOOD - Specific domains
CORS_ORIGINS=https://myapp.com,https://www.myapp.com
```

### 2. Use HTTPS in Production
```bash
# ❌ BAD - HTTP in production
CORS_ORIGINS=http://myapp.com

# ✅ GOOD - HTTPS only
CORS_ORIGINS=https://myapp.com
```

### 3. Limit Methods When Possible
```bash
# ❌ BAD - All methods allowed
CORS_ALLOW_METHODS=*

# ✅ GOOD - Only needed methods
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE
```

### 4. Restrict Headers When Possible
```bash
# ❌ BAD - All headers allowed
CORS_ALLOW_HEADERS=*

# ✅ GOOD - Only needed headers
CORS_ALLOW_HEADERS=Content-Type,Authorization
```

### 5. Disable Credentials for Public APIs
```bash
# For public APIs without authentication
CORS_ALLOW_CREDENTIALS=false
```

## Testing CORS Configuration

### Test with cURL

```bash
# Test preflight request
curl -X OPTIONS http://localhost:8000/api/orders \
  -H "Origin: http://localhost:5173" \
  -H "Access-Control-Request-Method: POST" \
  -v

# Test actual request
curl -X GET http://localhost:8000/api/orders \
  -H "Origin: http://localhost:5173" \
  -v
```

### Test with Browser Console

```javascript
// Test CORS from browser console
fetch('http://localhost:8000/api/orders', {
  method: 'GET',
  headers: {
    'Content-Type': 'application/json'
  },
  credentials: 'include'
})
.then(response => response.json())
.then(data => console.log('Success:', data))
.catch(error => console.error('CORS Error:', error));
```

## Troubleshooting

### Error: "CORS policy: No 'Access-Control-Allow-Origin' header"

**Cause**: The requesting origin is not in CORS_ORIGINS list

**Solution**:
```bash
# Add the origin to CORS_ORIGINS
CORS_ORIGINS=http://localhost:5173,http://your-new-origin.com
```

### Error: "CORS policy: Credentials flag is 'true'"

**Cause**: Credentials are being sent but CORS_ALLOW_CREDENTIALS is false

**Solution**:
```bash
# Enable credentials
CORS_ALLOW_CREDENTIALS=true
```

### Error: "Method not allowed by CORS"

**Cause**: The HTTP method is not in CORS_ALLOW_METHODS

**Solution**:
```bash
# Add the method or use wildcard
CORS_ALLOW_METHODS=GET,POST,PUT,DELETE,PATCH
# or
CORS_ALLOW_METHODS=*
```

### Error: "Request header not allowed by CORS"

**Cause**: A custom header is not in CORS_ALLOW_HEADERS

**Solution**:
```bash
# Add the header or use wildcard
CORS_ALLOW_HEADERS=Content-Type,Authorization,X-Custom-Header
# or
CORS_ALLOW_HEADERS=*
```

## Deployment Checklist

- [ ] Set CORS_ORIGINS to production domain(s)
- [ ] Use HTTPS URLs in CORS_ORIGINS
- [ ] Review CORS_ALLOW_METHODS (restrict if possible)
- [ ] Review CORS_ALLOW_HEADERS (restrict if possible)
- [ ] Set CORS_ALLOW_CREDENTIALS appropriately
- [ ] Test CORS from production frontend
- [ ] Verify preflight requests work
- [ ] Check browser console for CORS errors

## Code Implementation

The CORS configuration is implemented in:

1. **config.py** - Settings definition
```python
class Settings(BaseSettings):
    cors_origins: str = "http://localhost:5173,..."
    cors_allow_credentials: bool = True
    cors_allow_methods: str = "*"
    cors_allow_headers: str = "*"
    
    @property
    def cors_origins_list(self) -> List[str]:
        return [origin.strip() for origin in self.cors_origins.split(",")]
```

2. **main.py** - CORS middleware setup
```python
from config import settings

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins_list,
    allow_credentials=settings.cors_allow_credentials,
    allow_methods=[settings.cors_allow_methods] if settings.cors_allow_methods != "*" else ["*"],
    allow_headers=[settings.cors_allow_headers] if settings.cors_allow_headers != "*" else ["*"],
)
```

## Additional Resources

- [MDN CORS Documentation](https://developer.mozilla.org/en-US/docs/Web/HTTP/CORS)
- [FastAPI CORS Middleware](https://fastapi.tiangolo.com/tutorial/cors/)
- [OWASP CORS Security](https://owasp.org/www-community/attacks/CORS_OriginHeaderScrutiny)

---

**Last Updated**: February 20, 2026  
**Version**: 2.0.0
