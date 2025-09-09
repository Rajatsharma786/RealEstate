# Real Estate Agent - Setup Guide

## Quick Start

### 1. Environment Setup

1. **Copy environment template**:
   ```bash
   cp env.example .env
   ```

2. **Edit `.env` file** with your actual values:
   ```bash
   # Required
   OPENAI_API_KEY=your-openai-api-key-here
   DB_PASSWORD=your-database-password
   SECRET_KEY=your-secret-key-for-jwt-tokens
   
   # Optional (with defaults)
   EMAIL_SENDER=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   REDIS_URL=redis://localhost:6379
   ```

3. **Test environment configuration**:
   ```bash
   python test_env.py
   ```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Start the Application

**Option A: Use startup script**
```bash
# Windows
start.bat

# Linux/Mac
./start.sh
```

**Option B: Direct command**
```bash
python run_streamlit.py
```

### 4. Access the Web Interface

1. Open your browser
2. Navigate to `http://localhost:8501`
3. Login with default credentials:
   - Username: `admin`
   - Password: `admin123`

## Features Overview

### 🔐 Authentication
- Secure JWT-based authentication
- User session management
- Password hashing with bcrypt

### 💬 Conversation Management
- Persistent conversation history per user
- Real-time streaming responses
- Conversation switching and management

### 🏠 Real Estate Analysis
- Natural language property queries
- SQL generation and execution
- Comprehensive property reports
- Email report delivery

### 🚀 Performance
- Redis-based caching [[memory:8431746]]
- Connection pooling
- Streaming responses

## User Management

### Create New Users
```bash
python manage_users.py
```

### Default Admin Account
- Username: `admin`
- Password: `admin123`
- Role: `admin`

## Configuration Options

### Database
- PostgreSQL connection settings
- Connection pooling
- Automatic schema management

### LLM
- OpenAI model configuration
- Temperature and streaming settings
- API key management

### Caching
- Redis configuration
- TTL settings
- Namespace management

### Email
- SMTP server configuration
- PDF report generation
- Email delivery settings

## Troubleshooting

### Common Issues

1. **"SECRET_KEY not configured"**
   - Set `SECRET_KEY` in your `.env` file
   - Use a strong, random string

2. **Database connection errors**
   - Verify PostgreSQL is running
   - Check connection details in `.env`
   - Ensure database exists

3. **Redis connection errors**
   - Start Redis server
   - Check `REDIS_URL` in `.env`
   - Verify Redis is accessible

4. **OpenAI API errors**
   - Verify `OPENAI_API_KEY` is set
   - Check API key validity
   - Ensure sufficient credits

### Debug Mode

Enable debug output:
```bash
export DEBUG=1
python run_streamlit.py
```

## Security Notes

1. **Change default passwords** immediately
2. **Use strong SECRET_KEY** for JWT tokens
3. **Secure your database** with proper credentials
4. **Use HTTPS** in production
5. **Regular security updates** for dependencies

## Production Deployment

### Environment Variables
- Set all required environment variables
- Use secure, random values for secrets
- Configure proper database credentials

### Database Setup
- Create production database
- Run migrations if needed
- Set up proper backups

### Redis Setup
- Configure Redis for production
- Set up persistence
- Configure memory limits

### Web Server
- Use reverse proxy (nginx)
- Enable HTTPS
- Configure proper headers

## Support

For issues and questions:
1. Check this setup guide
2. Review the main README.md
3. Check environment configuration
4. Verify all services are running
5. Open an issue in the repository
