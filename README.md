# Job Application System

A sophisticated multi-agent system for automated job searching and application, built with **LangGraph** for robust workflow orchestration. This system uses web automation to interact with job boards using your regular email/password credentials - no API tokens required!

## 🚀 What's New in LangGraph Version

This system has been completely rewritten to use **LangGraph** instead of LangChain, providing:

- **Declarative Workflow Definition**: Clear, visual workflow graphs
- **Built-in State Management**: Automatic state flow between agents
- **Better Error Handling**: Robust error recovery and state persistence
- **Scalable Architecture**: Easy to add new agents and workflow steps
- **Modern Async Support**: Full async/await support throughout
- **🆕 Web Automation**: **NEW!** Use email/password for LinkedIn and Glassdoor - no API tokens needed!

## 🏗️ Architecture Overview

The system uses LangGraph's workflow approach with a modular, agent-based architecture that coordinates multiple specialized AI agents to automate the job search and application process.

### Workflow Structure

```
resume_analysis → job_search → process_jobs → generate_report
```

### Architecture Layers

#### **Orchestration Layer**
- **SmartOrchestratorAgent**: Main workflow coordinator using LangGraph
- **Workflow Engine**: State management and flow control
- **Session Manager**: Tracking and recovery mechanisms

#### **Agent Layer**
- **Core Agents**: Specialized agents for specific tasks
  - **Resume Analysis Agent**: AI-powered resume parsing and analysis
  - **Job Search Agent**: Multi-source job discovery
  - **Skills Analysis Agent**: AI-powered skill extraction and matching
  - **Resume Modification Agent**: AI resume optimization
  - **Application Agent**: Web automation and job submission
- **Base Infrastructure**: Error handling, retries, and logging

#### **Data Layer**
- **Storage**: SQLite database (fallback) and Supabase integration
- **File System**: Resumes, logs, and output files
- **External APIs**: OpenAI GPT API for AI-powered analysis

#### **Utility Layer**
- **Core Utilities**: Report generation, database operations, logging
- **Analysis Tools**: Skill matching, resume optimization, trend analysis

#### **Safety & Monitoring**
- **Rate Limiting**: Request rate limiting and job site protection
- **Monitoring**: Performance metrics, error alerts, audit trails

## 🎯 Key Features

- **Web Automation**: No API tokens needed - just email/password
- **Multi-Platform Support**: LinkedIn, Glassdoor, and Indeed integration
- **AI-Powered Analysis**: OpenAI integration for resume analysis and job matching
- **Smart Filtering**: Automatic job filtering based on your preferences
- **Auto-Application**: Automated job applications (when enabled)
- **Resume Optimization**: AI-powered resume analysis and suggestions
- **Workflow Orchestration**: LangGraph-based workflow management
- **Comprehensive Logging**: Detailed logging and reporting

## 🛠️ Installation

### Prerequisites

1. **Python 3.7+** with required packages
2. **Chrome Browser** (for Selenium automation)
3. **LinkedIn Account** (for job searching)
4. **Glassdoor Account** (for job searching)
5. **OpenAI API Key** (for AI-powered features)

### Setup Steps

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd marketin_jobs_
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**:
   ```bash
   cp env_template.txt .env
   # Edit .env with your credentials
   ```

## 🔑 Configuration

### Environment Variables (.env)

The `.env` file contains your credentials and system settings:

```bash
# OpenAI API for AI-powered features
OPENAI_API_KEY=your_openai_api_key

# Job Board Credentials (no API tokens needed!)
LINKEDIN_EMAIL=your_linkedin_email@example.com
LINKEDIN_PASSWORD=your_linkedin_password
GLASSDOOR_EMAIL=your_glassdoor_email@example.com
GLASSDOOR_PASSWORD=your_glassdoor_password
INDEED_EMAIL=your_indeed_email@example.com
INDEED_PASSWORD=your_indeed_password

# Web Automation Settings
WEB_AUTOMATION_TIMEOUT=30
WEB_AUTOMATION_MAX_RETRIES=3
WEB_AUTOMATION_DELAY=2.0

# File Paths
RESUME_TEMPLATE_PATH=./data/resume_template.docx
OUTPUT_RESUME_DIR=./output/resumes/
APPLICATION_LOG_DIR=./logs/

# Database Configuration (Optional)
SUPABASE_URL=your_supabase_project_url
SUPABASE_ANON_KEY=your_supabase_anon_key
SUPABASE_SERVICE_ROLE_KEY=your_supabase_service_role_key
USE_SUPABASE=true
```

### Job Search Configuration (job_config.py)

Job search settings are now managed in `job_config.py` for easier customization:

```python
class JobConfig:
    # Job Search Preferences
    ROLE = "Software Engineer"
    LOCATION = "Remote"
    MAX_JOBS = 10
    AUTO_APPLY = False
    
    # Keywords and Filters
    KEYWORDS = ["python", "machine learning", "AI", "data science"]
    EXCLUDE_KEYWORDS = ["senior", "lead", "manager", "director"]
    
    # Salary Range
    MIN_SALARY = 80000
    MAX_SALARY = 150000
    
    # Job Types and Experience
    JOB_TYPES = ["full-time", "remote"]
    EXPERIENCE_LEVELS = ["entry", "mid-level"]
    
    # Application Settings
    APPLICATION_DELAY = 30
    MAX_DAILY_APPLICATIONS = 10
    SKILL_MATCH_THRESHOLD = 0.7
```

#### Customizing Job Search Settings

**Option 1: Direct File Editing**
Edit `job_config.py` directly to change settings.

**Option 2: Use Presets**
```python
from job_config import apply_job_preset

# Apply a preset
apply_job_preset("data_scientist")
apply_job_preset("frontend_developer")
apply_job_preset("machine_learning_engineer")
```

**Option 3: Programmatic Updates**
```python
from job_config import JobConfig

JobConfig.ROLE = "Product Manager"
JobConfig.KEYWORDS = ["product management", "agile", "scrum"]
JobConfig.LOCATION = "New York, NY"
```

#### Available Presets

- `software_engineer`: Full-stack development focus
- `data_scientist`: ML/AI and statistics focus
- `frontend_developer`: Frontend technologies focus
- `machine_learning_engineer`: Deep learning and ML focus

## 🚀 Quick Start

### 1. Basic Setup

```bash
# Set up your credentials
cp env_template.txt .env
# Edit .env with your LinkedIn/Glassdoor email/password

# Download ChromeDriver (if you have browser automation issues)
python download_chromedriver.py

# Run the web automation example
python examples/web_automation_example.py
```

### 2. Run the Full Workflow

```bash
python main.py
```

### 3. Run Example Workflow

```bash
python main.py --example
```

### 4. Run LangGraph Demo

```bash
python examples/langgraph_example.py
```

## 📋 Usage Examples

### Web Automation Example

```python
from agents.smart_orchestrator_agent import SmartOrchestratorAgent
from agents.base_agent import AgentState
from job_config import JobConfig

# Initialize the orchestrator
orchestrator = SmartOrchestratorAgent()

# Create initial state
initial_state = AgentState(
    role=JobConfig.ROLE,
    resume_path=JobConfig.RESUME_PATH,
    location=JobConfig.LOCATION,
    max_jobs=JobConfig.MAX_JOBS,
    auto_apply=JobConfig.AUTO_APPLY,
    # ... other state properties
)

# Execute the workflow
final_state = await orchestrator.execute(initial_state)
```

### Basic Job Search

```python
from agents.job_search_agent import JobSearchAgent

agent = JobSearchAgent()
jobs = await agent.search_jobs(
    role="Software Engineer",
    location="Remote",
    keywords=["python", "machine learning"]
)
```

### Resume Analysis

```python
from agents.resume_analysis_agent import ResumeAnalysisAgent

agent = ResumeAnalysisAgent()
analysis = await agent.analyze_resume("path/to/resume.docx")
```

## 📁 Project Structure

```
marketin_jobs_/
├── agents/                          # Agent implementations
│   ├── smart_orchestrator_agent.py # Main workflow coordinator
│   ├── linkedin_web_agent.py       # LinkedIn automation
│   ├── glassdoor_web_agent.py      # Glassdoor automation
│   ├── job_search_agent.py         # General job search
│   ├── resume_analysis_agent.py    # Resume analysis
│   ├── application_agent.py        # Job applications
│   ├── skills_analysis_agent.py    # Skills analysis
│   ├── resume_modification_agent.py # Resume optimization
│   └── base_agent.py               # Base agent class
├── utils/                           # Utility functions
│   ├── database.py                 # Database operations
│   ├── logger.py                   # Logging utilities
│   ├── report_generator.py         # Report generation
│   ├── resume_editor.py            # Resume editing
│   ├── supabase_database.py        # Supabase integration
│   └── workflow_visualizer.py      # Workflow visualization
├── examples/                        # Example scripts
│   ├── basic_usage.py              # Basic usage examples
│   ├── advanced_usage.py           # Advanced usage examples
│   ├── web_automation_example.py   # Web automation demo
│   ├── langgraph_example.py        # LangGraph workflow demo
│   └── workflow_visualization_example.py
├── data/                           # Data files
│   └── sample_resume.docx          # Sample resume
├── logs/                           # Application logs
├── config.py                       # Main configuration
├── job_config.py                   # Job search configuration
├── main.py                         # Main entry point
└── requirements.txt                # Python dependencies
```

## 🔧 Advanced Configuration

### Web Automation Settings

Customize browser behavior and automation settings:

```python
# In web agents
WEB_AUTOMATION_TIMEOUT = 30          # Timeout for operations
WEB_AUTOMATION_MAX_RETRIES = 3       # Max retry attempts
WEB_AUTOMATION_DELAY = 2.0           # Delay between actions
```

### Safety Settings

```python
# Prevent overwhelming job sites
MAX_REQUESTS_PER_MINUTE = 10
MAX_DAILY_APPLICATIONS = 10
APPLICATION_DELAY = 30               # Seconds between applications
```

### Resume Settings

```python
MAX_RESUME_PAGES = 2                 # Max pages for resume
MIN_SKILL_MENTIONS = 3               # Min skill mentions required
SKILL_MATCH_THRESHOLD = 0.7          # Skill matching threshold
```

## 🗄️ Database Integration

### Supabase (Recommended)

The system supports Supabase for data persistence:

1. **Set up Supabase project**
2. **Run the setup script**: `supabase_setup.sql`
3. **Configure in .env**:
   ```bash
   SUPABASE_URL=your_project_url
   SUPABASE_ANON_KEY=your_anon_key
   SUPABASE_SERVICE_ROLE_KEY=your_service_role_key
   USE_SUPABASE=true
   ```

### SQLite (Fallback)

If Supabase is not configured, the system falls back to SQLite:
```bash
DATABASE_URL=sqlite:///job_applications.db
```

## 🐛 Troubleshooting

### Common Issues

1. **Browser Automation Issues**
   - Ensure Chrome is installed and up to date
   - Check that ChromeDriver version matches Chrome version
   - Verify no other Chrome instances are running

2. **Login Failures**
   - Verify email/password are correct
   - Check if 2FA is enabled (may require manual intervention)
   - Ensure accounts are not locked or suspended

3. **Rate Limiting**
   - Increase delays between actions
   - Reduce max daily applications
   - Use different user agents

### Browser Troubleshooting

**Common Browser Issues:**
- **ChromeDriver Version Mismatch**: Ensure ChromeDriver version matches your Chrome browser version
- **Browser Crashes**: Close other Chrome instances and restart the application
- **Element Not Found**: Job sites may have changed their HTML structure - check for updates
- **Rate Limiting**: Increase delays between actions and reduce request frequency

**Solutions:**
- **Automatic ChromeDriver Download**: Run `python download_chromedriver.py` to get the correct version
- Update Chrome and ChromeDriver to latest versions
- Clear browser cache and cookies
- Use headless mode for better stability
- Implement exponential backoff for failed requests

**Windows-Specific Issues:**
- **WinError 193**: Usually indicates ChromeDriver compatibility issues
- **ChromeDriver Download**: Use the provided download script for Windows compatibility
- **Path Issues**: Ensure ChromeDriver is in your PATH or current directory

### Glassdoor Stability

**Known Issues and Fixes:**
- **Login Failures**: Glassdoor occasionally changes login flow - check for updates
- **Job Listings**: Some job listings may not load due to dynamic content
- **Rate Limiting**: Glassdoor has strict rate limits - use built-in delays
- **Session Timeouts**: Implement automatic re-login for long sessions

**Stability Improvements:**
- Use robust element waiting strategies
- Implement retry mechanisms with exponential backoff
- Handle dynamic content loading
- Monitor for site structure changes

## 📊 Monitoring and Logging

### Log Files

- **Application logs**: `./logs/` directory
- **Workflow logs**: Detailed workflow execution logs
- **Error logs**: Error tracking and debugging information

### Reporting

The system generates comprehensive reports including:
- Job search results and statistics
- Application success rates
- Skill analysis and recommendations
- Workflow performance metrics

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests if applicable
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🆘 Support

For issues and questions:
1. Check the troubleshooting section
2. Review the example scripts
3. Check the logs for error details
4. Open an issue on GitHub

## 🔄 Recent Changes

### Configuration Migration
- **Job search configuration** moved from `.env` to `job_config.py`
- **Centralized configuration** for easier customization
- **Preset support** for common job roles
- **Backward compatibility** maintained

### Web Automation
- **No API tokens required** for job board access
- **Email/password authentication** for LinkedIn and Glassdoor
- **Selenium-based automation** for reliable job site interaction
- **Built-in safety features** to prevent rate limiting

### LangGraph Integration
- **Complete rewrite** using LangGraph for workflow orchestration
- **Declarative workflow definition** with visual graphs
- **Built-in state management** and error handling
- **Scalable architecture** for adding new agents

---

**Note**: This system works with just the OpenAI API key and your job board credentials. No complex API setup required - just email and password!
