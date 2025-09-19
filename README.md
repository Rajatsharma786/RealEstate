# RealEstate

An AI-powered real estate analytics and reporting platform built with Python, LangGraph, and Streamlit.  
It converts natural-language questions into safe SQL queries, retrieves and analyzes property data, and generates on-demand reports.

## Key Features
- **Natural language to SQL** – users can ask questions like “average price by suburb in VIC” and get live database answers.  
- **Vector search context** – enriches responses with property definitions and metadata.  
- **Report generation** – produces structured analytical reports and can email them to users.  
- **Streamlit interface** – clean UI with real-time streaming answers and conversation history.  
- **Caching & state** – Redis for query and conversation caching to speed up repeated requests.  
- **Secure auth** – JWT-based user authentication with an admin panel.

## Project Structure

<img width="850" height="557" alt="image" src="https://github.com/user-attachments/assets/1de31d6e-41b2-4931-b436-7641777d80da" />
<img width="839" height="509" alt="image" src="https://github.com/user-attachments/assets/25b957d2-20d6-47b8-9df1-92b76a2b5ced" />

## Setup

### Prerequisites
- Python 3.10+
- PostgreSQL (or compatible DB)
- Redis (for caching)
- OpenAI API key (for LLM calls)

### Installation
```bash
git clone https://github.com/Rajatsharma786/RealEstate.git
cd RealEstate
pip install -r requirements.txt
```

### Configuration
1. Copy the environment template and update values:
   ```bash
   cp env.example .env
   ```
2. Edit `.env` with database credentials, `OPENAI_API_KEY`, Redis URL, and email settings if using report delivery.

### Run the App
Start Redis (or ensure it’s running), then:
```bash
streamlit run app.py
```
or
```bash
python start.py
```

Default admin credentials (change on first login):
```
Username: admin
Password: admin123
```

## Usage
- Ask property questions such as:
  - “Show properties in Melbourne with 3+ bedrooms under $800,000.”
  - “Average price by suburb for the last 3 months.”
- Download or email detailed reports directly from the interface.
- All queries, answers, and SQL statements are stored in conversation history for reference.

## Roadmap
- Full Docker Compose for one-command deployment (PostgreSQL, Redis, Streamlit).
- Advanced scheduled reporting and email notifications.
- Extended RAG pipeline for richer property market insights.

