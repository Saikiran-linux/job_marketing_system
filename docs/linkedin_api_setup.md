# LinkedIn API Integration Setup Guide

This guide will walk you through setting up the LinkedIn API integration for your job marketing system, allowing agents to search for jobs and apply to them directly through LinkedIn's API.

## Prerequisites

- LinkedIn account
- Python 3.8+
- Required Python packages (see requirements.txt)

## Step 1: LinkedIn Developer Account Setup

### 1.1 Create LinkedIn Developer Account

1. Go to [LinkedIn Developers](https://www.linkedin.com/developers/)
2. Click "Create App"
3. Fill in the required information:
   - App name: `Job Marketing System` (or your preferred name)
   - LinkedIn Page: Select your LinkedIn page or create one
   - App Logo: Upload a logo (optional)
4. Click "Create App"

### 1.2 Configure App Settings

1. In your app dashboard, go to "Auth" tab
2. Add the following OAuth 2.0 redirect URLs:
   - `http://localhost:8000/callback`
   - `http://localhost:3000/callback`
   - `urn:ietf:wg:oauth:2.0:oob` (for development)

### 1.3 Request API Access

1. Go to "Products" tab
2. Request access to "Marketing Developer Platform"
3. Request access to "Jobs API" (if available)
4. Wait for approval (may take 24-48 hours)

### 1.4 Get API Credentials

1. Go to "Auth" tab
2. Copy your **Client ID** and **Client Secret**
3. These will be used in your environment variables

## Step 2: OAuth 2.0 Authentication Flow

### 2.1 Generate Authorization URL

The LinkedIn API uses OAuth 2.0 for authentication. You'll need to implement the authorization flow to get access tokens.

```python
import requests
from urllib.parse import urlencode

def get_linkedin_auth_url(client_id, redirect_uri, scope):
    """Generate LinkedIn authorization URL."""
    
    auth_params = {
        'response_type': 'code',
        'client_id': client_id,
        'redirect_uri': redirect_uri,
        'scope': scope,
        'state': 'random_state_string'
    }
    
    auth_url = 'https://www.linkedin.com/oauth/v2/authorization'
    return f"{auth_url}?{urlencode(auth_params)}"

# Example usage
client_id = 'your_client_id'
redirect_uri = 'http://localhost:8000/callback'
scope = 'r_liteprofile r_emailaddress w_member_social'

auth_url = get_linkedin_auth_url(client_id, redirect_uri, scope)
print(f"Visit this URL to authorize: {auth_url}")
```

### 2.2 Exchange Authorization Code for Tokens

After user authorization, you'll receive an authorization code that needs to be exchanged for access and refresh tokens.

```python
def exchange_code_for_tokens(authorization_code, client_id, client_secret, redirect_uri):
    """Exchange authorization code for access and refresh tokens."""
    
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    
    token_data = {
        'grant_type': 'authorization_code',
        'code': authorization_code,
        'client_id': client_id,
        'client_secret': client_secret,
        'redirect_uri': redirect_uri
    }
    
    response = requests.post(token_url, data=token_data)
    
    if response.status_code == 200:
        tokens = response.json()
        return {
            'access_token': tokens.get('access_token'),
            'refresh_token': tokens.get('refresh_token'),
            'expires_in': tokens.get('expires_in')
        }
    else:
        raise Exception(f"Token exchange failed: {response.text}")
```

### 2.3 Refresh Access Token

Access tokens expire after a certain time (usually 1 hour). Use the refresh token to get a new access token.

```python
def refresh_access_token(refresh_token, client_id, client_secret):
    """Refresh access token using refresh token."""
    
    token_url = 'https://www.linkedin.com/oauth/v2/accessToken'
    
    token_data = {
        'grant_type': 'refresh_token',
        'refresh_token': refresh_token,
        'client_id': client_id,
        'client_secret': client_secret
    }
    
    response = requests.post(token_url, data=token_data)
    
    if response.status_code == 200:
        tokens = response.json()
        return {
            'access_token': tokens.get('access_token'),
            'expires_in': tokens.get('expires_in')
        }
    else:
        raise Exception(f"Token refresh failed: {response.text}")
```

## Step 3: Environment Configuration

### 3.1 Update Environment Variables

Copy the `env_template.txt` to `.env` and fill in your LinkedIn API credentials:

```bash
# LinkedIn API Configuration
LINKEDIN_CLIENT_ID=your_linkedin_client_id_here
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret_here
LINKEDIN_REFRESH_TOKEN=your_linkedin_refresh_token_here
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token_here

# LinkedIn API Settings
LINKEDIN_API_TIMEOUT=30
LINKEDIN_MAX_RETRIES=3
LINKEDIN_RATE_LIMIT_DELAY=1.0
```

### 3.2 Test Configuration

Run the configuration validation to ensure all required fields are set:

```python
from config import Config

if Config.validate_config():
    print("✅ Configuration is valid")
else:
    print("❌ Configuration validation failed")
```

## Step 4: Testing the Integration

### 4.1 Run the LinkedIn Integration Example

```bash
python examples/linkedin_integration_example.py
```

This will test:
- LinkedIn API connectivity
- Job search functionality
- Job details retrieval
- Application submission (simulated)

### 4.2 Test Individual Components

```python
import asyncio
from agents.linkedin_agent import LinkedInAgent

async def test_linkedin_search():
    """Test LinkedIn job search."""
    
    linkedin_agent = LinkedInAgent()
    
    try:
        result = await linkedin_agent.execute({
            "operation": "search",
            "keywords": "Python Developer",
            "location": "Remote",
            "max_results": 5
        })
        
        if result.get("status") == "success":
            jobs = result.get("jobs", [])
            print(f"Found {len(jobs)} jobs")
            
            for job in jobs:
                print(f"- {job.get('title')} at {job.get('company')}")
        else:
            print(f"Search failed: {result.get('message')}")
            
    finally:
        await linkedin_agent.close()

# Run the test
asyncio.run(test_linkedin_search())
```

## Step 5: Production Considerations

### 5.1 Rate Limiting

LinkedIn API has rate limits. Implement proper delays between requests:

```python
import asyncio
from config import Config

async def rate_limited_request(func, *args, **kwargs):
    """Execute function with rate limiting."""
    
    result = await func(*args, **kwargs)
    
    # Wait between requests to respect rate limits
    await asyncio.sleep(Config.LINKEDIN_RATE_LIMIT_DELAY)
    
    return result
```

### 5.2 Error Handling

Implement robust error handling for API failures:

```python
async def safe_linkedin_operation(operation_func, max_retries=3):
    """Execute LinkedIn operation with retry logic."""
    
    for attempt in range(max_retries):
        try:
            return await operation_func()
        except Exception as e:
            if attempt == max_retries - 1:
                raise e
            
            # Wait before retry (exponential backoff)
            wait_time = 2 ** attempt
            await asyncio.sleep(wait_time)
```

### 5.3 Token Management

Implement automatic token refresh:

```python
class LinkedInTokenManager:
    """Manages LinkedIn API tokens with automatic refresh."""
    
    def __init__(self, client_id, client_secret, refresh_token):
        self.client_id = client_id
        self.client_secret = client_secret
        self.refresh_token = refresh_token
        self.access_token = None
        self.token_expiry = None
    
    async def get_valid_token(self):
        """Get a valid access token, refreshing if necessary."""
        
        if (self.access_token and self.token_expiry and 
            datetime.now() < self.token_expiry):
            return self.access_token
        
        # Refresh token
        tokens = await self._refresh_token()
        self.access_token = tokens['access_token']
        self.token_expiry = datetime.now() + timedelta(seconds=tokens['expires_in'] - 300)
        
        return self.access_token
```

## Step 6: Troubleshooting

### 6.1 Common Issues

**"Invalid credentials" error:**
- Verify your Client ID and Client Secret
- Ensure your app is approved for the required APIs
- Check if your refresh token is still valid

**"Rate limit exceeded" error:**
- Implement proper delays between requests
- Reduce the number of concurrent requests
- Use exponential backoff for retries

**"Permission denied" error:**
- Check if your app has the required scopes
- Verify API access approval status
- Ensure user has granted necessary permissions

### 6.2 Debug Mode

Enable debug logging to troubleshoot issues:

```python
import logging

# Enable debug logging
logging.basicConfig(level=logging.DEBUG)

# LinkedIn agent will now log detailed information
linkedin_agent = LinkedInAgent()
```

## Step 7: Security Best Practices

### 7.1 Secure Credential Storage

- Never commit API credentials to version control
- Use environment variables or secure secret management
- Rotate refresh tokens regularly
- Implement proper access controls

### 7.2 API Usage Monitoring

- Monitor API usage and rate limits
- Implement request logging for debugging
- Set up alerts for API failures
- Track application success rates

## Next Steps

1. **Test the integration** with the provided examples
2. **Customize the agents** for your specific use case
3. **Implement monitoring** and error handling
4. **Scale the system** based on your needs
5. **Monitor LinkedIn's API changes** and update accordingly

## Support

If you encounter issues:

1. Check the [LinkedIn API Documentation](https://developer.linkedin.com/docs)
2. Review the error logs and debug output
3. Verify your API credentials and permissions
4. Test with the provided examples first
5. Check for rate limiting or API changes

## Additional Resources

- [LinkedIn API Reference](https://developer.linkedin.com/api-reference)
- [OAuth 2.0 Flow Documentation](https://developer.linkedin.com/docs/oauth2)
- [Jobs API Documentation](https://developer.linkedin.com/docs/jobs-api)
- [Rate Limiting Guidelines](https://developer.linkedin.com/docs/rest-api#rate-limiting)
