# Redis Setup - Alternative Options

Since the sandbox has limitations, here are your options to get Redis working:

## Option 1: Start Docker Daemon (Recommended)
You have Docker installed but the daemon needs to be started:

```bash
# Start Docker daemon
open /Applications/Docker.app

# Wait ~30 seconds, then run:
docker run -d --name redis-cache -p 6379:6379 redis:latest

# Test connection:
redis-cli ping
# Should return: PONG
```

## Option 2: Redis Cloud (Free, No Installation)
The easiest path forward:

1. Go to https://app.redis.com/
2. Create free account
3. Create free database
4. Copy connection string (looks like: redis://:password@hostname:port)
5. Add to `.env`:
   ```bash
   REDIS_URL=redis://:your-password@your-hostname:port
   ```

## Option 3: Compile from Source (Advanced)
```bash
# Download Redis
curl -fsSL http://download.redis.io/redis-7.0.0.tar.gz -o redis.tar.gz
tar xzf redis.tar.gz
cd redis-7.0.0
make
```

## Current Status
- ❌ Homebrew: Permission issues (need to fix Homebrew ownership)
- ❌ Docker: Daemon not running
- ✅ Redis Cloud: Works immediately (no setup needed)

## Recommendation
**Use Redis Cloud for now** - it's the fastest path and works from anywhere.
Then later you can optimize with local Redis if needed.

---

## Quick Redis Cloud Setup (2 minutes):

1. Visit: https://app.redis.com/
2. Sign up (GitHub or email)
3. Click "Create database"
4. Choose "Fixed" plan (free tier)
5. Copy your connection string
6. Paste into `.env`:
   ```
   REDIS_URL=redis://:YOUR_PASSWORD@YOUR_ENDPOINT:6379
   ```

Done! Your cache is enabled globally without any local setup.
