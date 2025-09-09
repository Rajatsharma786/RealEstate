# Real Estate Agent

A production-ready AI-powered real estate analysis system built with LangGraph. This system can analyze property data, generate SQL queries from natural language, and provide comprehensive reports with email functionality.

## Features

- 🏠 **Natural Language Queries**: Ask questions about properties in plain English
- 🔍 **Intelligent SQL Generation**: Automatically converts questions to SQL queries
- 📊 **Comprehensive Reports**: Generates detailed property analysis reports
- 📧 **Email Integration**: Send reports directly to email addresses
- 🚀 **Caching System**: Redis-based caching for improved performance
- 🧠 **Context-Aware**: Uses vector search for relevant property information
- 💾 **Data Processing**: Automatic data cleaning and type inference
- 🌐 **Web Interface**: Beautiful Streamlit-based web application
- 🔐 **Authentication**: Secure user authentication with JWT tokens and PostgreSQL storage
- 💬 **Conversation History**: Redis-based persistent conversation storage per user
- 👤 **User Management**: Sign up functionality and admin panel for user management
- 🔒 **Security**: Admin accounts cannot be created through the interface - only default admin exists
- 📱 **Real-time Streaming**: Live response streaming for better UX

## Architecture

The system is built using a clean, modular architecture:

```
real_estate_agent/
├── app.py                 # Main Streamlit web application
├── data.py                # All data operations (cleaning, setup, loading)
├── config.py              # Configuration management
├── auth.py                # Authentication system
├── cache.py               # Caching functionality
├── src/
│   ├── graph/
│   │   ├── workflow.py    # LangGraph workflow definition
│   │   ├── state.py       # State definitions
│   │   ├── conditions.py  # Conditional logic
│   │   └── nodes/         # Graph node implementations
│   │       ├── retrieve.py    # Document retrieval
│   │       ├── rewrite.py     # Query rewriting
│   │       ├── sql_write.py   # SQL generation
│   │       ├── sql_run.py     # SQL execution
│   │       ├── report.py      # Report generation
│   │       └── email.py       # Email functionality
│   └── services/
│       ├── agent.py       # Agent service interface
│       └── db/
│           └── sql.py     # Database operations
└── data/                  # Data files
    ├── data_dictionary.csv
    └── properties_augmented_vic.csv
```

## Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd RealEstate_agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up PostgreSQL database**:
   - Install PostgreSQL
   - Create a database named `langchain`
   - Update connection details in `src/notebook_app/config.py` or set environment variables

4. **Set up environment variables**:
   ```bash
   # Copy the example environment file
   cp env.example .env
   
   # Edit .env with your actual values
   export OPENAI_API_KEY="your-openai-api-key"
   export DB_HOST="localhost"
   export DB_PORT="6024"
   export DB_NAME="langchain"
   export DB_USER="langchain"
   export DB_PASSWORD="your-db-password"
   export REDIS_URL="redis://localhost:6379"
   export SECRET_KEY="your-secret-key-for-jwt-tokens"
   export EMAIL_SENDER="your-email@gmail.com"
   export EMAIL_PASSWORD="your-app-password"
   ```

5. **Start Redis server**:
   ```bash
   # On Windows (using Docker)
   docker run -d -p 6379:6379 --name redis redis:latest
   
   # On macOS (using Homebrew)
   brew install redis
   brew services start redis
   
   # On Linux (Ubuntu/Debian)
   sudo apt-get install redis-server
   sudo systemctl start redis-server
   ```

## Usage

### Web Interface

**Start the Application**:
```bash
# Simple startup (recommended)
python start.py

# Or directly with Streamlit
streamlit run app.py
```

The web interface provides:
- 🔐 Secure user authentication
- 💬 Real-time conversation streaming
- 📱 Responsive design for all devices
- 💾 Persistent conversation history
- 🎯 Quick action buttons for common queries

**Default Login Credentials**:
- Username: `admin`
- Password: `admin123`

### Admin Panel

**Access Admin Panel**:
- Login as admin user
- Click "🔧 User Management" in the sidebar
- Access the admin panel with full user management capabilities

**Admin Features**:
- 👥 **View All Users**: See all registered users with their details
- ➕ **Create Users**: Add new users with custom roles (user/admin)
- 🔐 **Change Passwords**: Update user passwords securely
- 🧪 **Test Logins**: Verify user credentials
- 🗑️ **Delete Users**: Remove users (admin user protected)

### Data Setup

**Setup/Load Data**:
```bash
python data.py
```

This will:
- Load and clean property data
- Setup the database tables
- Initialize the vector store
- Test all connections

### Programmatic Usage

```python
from src.notebook_app.services.agent import call_agent, get_agent_response

# Get a full response with streaming output
result = call_agent("Properties in Melbourne with 3+ bedrooms", "user_123")

# Get just the final report
report = get_agent_response("Average prices by suburb in VIC")
```

### Example Queries

- "Show me properties in VIC state listed this year"
- "What's the average price by suburb in Melbourne?"
- "Find houses with at least 3 bedrooms under $800,000"
- "Send me a report on properties near hospitals to my email"
- "What properties are available in Richmond?"

## Configuration

The system uses a configuration system that supports both environment variables and direct configuration. Key settings include:

- **Database**: PostgreSQL connection details
- **LLM**: OpenAI model configuration
- **Embeddings**: Sentence transformer model
- **Cache**: TTL and namespace settings
- **Email**: SMTP configuration for sending reports
- **Authentication**: JWT token configuration
- **Streamlit**: Web interface settings

See `src/notebook_app/config.py` for all available configuration options and `env.example` for environment variable reference.

## Security

### Default Admin Account
- **Username**: `admin`
- **Password**: `admin123`
- **Role**: `admin`

⚠️ **Important Security Notes**:
- The default admin account is created automatically on first run
- **Admin accounts cannot be created through the web interface** - only regular users can sign up
- Only the default admin can access the admin panel for user management
- Change the default admin password immediately after first login
- The admin panel allows viewing all users, changing passwords, and deleting users (except admin)

### User Roles
- **Admin**: Full access to admin panel, can manage all users
- **User**: Standard access to chat interface, can only manage their own conversations

### Authentication
- JWT tokens with configurable expiration (default: 24 hours)
- Passwords are hashed using bcrypt
- User data stored securely in PostgreSQL database
- Session management through Streamlit session state

## Data Setup

1. **Load Property Data**:
   ```python
   from src.notebook_app.data.cleaning import clean_dataframe, DataTypeInferencer
   from src.notebook_app.services.db.sql import db_service
   import pandas as pd
   
   # Load and clean data
   df = pd.read_csv("data/properties_augmented_vic.csv")
   cleaned_df = clean_dataframe(df)
   
   # Infer data types
   inferencer = DataTypeInferencer()
   converted_df, report = inferencer.analyze_and_convert_dataframe(cleaned_df)
   
   # Load into database
   db_service.create_properties_table(converted_df)
   ```

2. **Load Data Dictionary**:
   ```python
   from langchain_postgres import PGVector
   from langchain_community.embeddings import HuggingFaceEmbeddings
   from langchain_core.documents import Document
   import pandas as pd
   
   # Setup vector store
   embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
   vs = PGVector(
       connection="postgresql+psycopg://langchain:langchain@localhost:6024/langchain",
       embeddings=embeddings,
       collection_name="real_estate_dict",
       use_jsonb=True,
   )
   
   # Load dictionary
   df_dict = pd.read_csv("data/data_dictionary.csv")
   docs, ids = [], []
   for i, row in df_dict.iterrows():
       field = str(row["field_name"]).strip()
       desc = str(row["description"]).strip()
       if field and desc:
           page_content = f"{field}: {desc}"
           docs.append(Document(page_content=page_content, metadata={"field": field}))
           ids.append(f"dict::{field}")
   
   vs.add_documents(docs, ids=ids)
   ```

## Workflow

The system follows this workflow:

1. **Retrieve**: Get relevant context from vector store
2. **Rewrite**: Improve query clarity and specificity
3. **Plan SQL**: Generate SQL query from natural language
4. **Run SQL**: Execute query against database
5. **Report**: Generate comprehensive analysis report
6. **Email**: Send report via email if requested

## Caching

The system includes a sophisticated Redis-based caching mechanism:

- **SQL Results**: Cached to avoid repeated database queries
- **Vector Search**: Cached similarity search results
- **Conversations**: Cached conversation states for continuity
- **Schema Info**: Cached database schema information
- **Performance**: Redis provides ultra-fast in-memory caching
- **Automatic TTL**: Built-in expiration without manual cleanup

## Email Functionality

The system can send reports via email with PDF attachments:

- Automatic email extraction from user queries
- PDF report generation using ReportLab
- SMTP integration for email delivery
- Error handling and status reporting

## Development

### Running Tests

```bash
pytest tests/
```

### Code Formatting

```bash
black src/
flake8 src/
mypy src/
```

### Adding New Features

1. Create new nodes in `src/notebook_app/graph/nodes/`
2. Update the graph in `src/notebook_app/app.py`
3. Add configuration options in `src/notebook_app/config.py`
4. Update tests and documentation

## Memory Integration

The system uses LangGraph's memory system to maintain conversation context across interactions, enabling follow-up questions and contextual responses.

## Performance Considerations

- **Caching**: Reduces API calls and database queries
- **Streaming**: Real-time response generation
- **Indexing**: Automatic database indexing for performance
- **Connection Pooling**: Efficient database connections

## Troubleshooting

### Common Issues

1. **Database Connection**: Ensure PostgreSQL is running and accessible
2. **API Keys**: Verify OpenAI API key is set correctly
3. **Dependencies**: Ensure all requirements are installed
4. **Data Loading**: Verify property data and dictionary are loaded

### Debug Mode

Enable debug output by setting environment variable:
```bash
export DEBUG=1
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## Support

For support and questions, please open an issue in the repository or contact the development team.
