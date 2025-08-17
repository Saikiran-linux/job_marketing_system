# Job Marketing System

An intelligent, automated job search and application system that uses multiple AI agents to find jobs, analyze requirements, optimize resumes, and submit applications.

## 🚀 Features

- **Intelligent Job Search**: Automatically searches multiple job boards (Indeed, LinkedIn, Glassdoor)
- **Skills Analysis**: Uses AI to extract and analyze required skills from job descriptions
- **Resume Optimization**: Automatically modifies resumes to match job requirements
- **Automated Applications**: Submits job applications with optimized resumes and cover letters
- **Comprehensive Reporting**: Generates detailed analytics and recommendations
- **Multi-Agent Architecture**: Modular design with specialized agents for different tasks

## 🏗️ Architecture

The system consists of six specialized agents:

1. **Job Search Agent** - Finds relevant job postings from multiple sources
2. **Skills Analysis Agent** - Extracts required skills using AI and pattern matching
3. **Resume Analysis Agent** - Analyzes current resume content and structure
4. **Resume Modification Agent** - Optimizes resumes for specific job requirements
5. **Application Agent** - Automates the job application process
6. **Orchestrator Agent** - Coordinates all agents in a complete workflow

## 📋 Prerequisites

- Python 3.8 or higher
- Chrome browser (for web automation)
- OpenAI API key (for AI-powered features)

## 🛠️ Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/Saikiran-linux/job_marketing_system.git
   cd job_marketing_system
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up configuration**:
   ```bash
   cp .env.example .env
   # Edit .env with your API keys and settings
   ```

4. **Download required NLTK data** (automatic on first run):
   ```python
   import nltk
   nltk.download('punkt')
   nltk.download('stopwords')
   ```

## ⚙️ Configuration

Create a `.env` file with the following settings:

```env
# Required
OPENAI_API_KEY=your_openai_api_key_here

# Optional Job Board Credentials
LINKEDIN_EMAIL=your_linkedin_email@example.com
LINKEDIN_PASSWORD=your_linkedin_password
INDEED_EMAIL=your_indeed_email@example.com
INDEED_PASSWORD=your_indeed_password

# Application Settings
MAX_JOBS_PER_SOURCE=50
APPLICATION_DELAY=5
MAX_DAILY_APPLICATIONS=20
SKILL_MATCH_THRESHOLD=0.7
```

## 🚀 Quick Start

### Basic Usage

```bash
# Search and analyze jobs (no applications)
python main.py --role "Software Engineer" --resume "./my_resume.docx"

# Search with specific location
python main.py --role "Data Scientist" --location "San Francisco" --resume "./resume.docx"

# Auto-apply to jobs (use with caution!)
python main.py --role "Python Developer" --resume "./resume.docx" --auto-apply

# Dry run (test without applying)
python main.py --role "DevOps Engineer" --resume "./resume.docx" --dry-run
```

### Advanced Usage

```bash
# Limit job search
python main.py --role "ML Engineer" --resume "./resume.docx" --max-jobs 10

# Check configuration
python main.py --config-check

# Resume previous session
python main.py --session-id "session_20240101_120000"
```

## 📁 File Structure

```
job_marketing_system/
├── agents/                     # AI agents
│   ├── base_agent.py          # Base agent class
│   ├── job_search_agent.py    # Job searching
│   ├── skills_analysis_agent.py # Skills extraction
│   ├── resume_analysis_agent.py # Resume analysis
│   ├── resume_modification_agent.py # Resume optimization
│   ├── application_agent.py   # Job applications
│   └── orchestrator_agent.py  # Workflow coordination
├── utils/                      # Utilities
│   ├── logger.py              # Logging setup
│   ├── database.py            # Data persistence
│   └── report_generator.py    # Analytics
├── data/                       # Resume templates
├── output/                     # Generated resumes
├── logs/                       # Application logs
├── config.py                   # Configuration
├── main.py                     # Main entry point
└── requirements.txt            # Dependencies
```

## 🔧 API Usage

### Programmatic Usage

```python
import asyncio
from agents.orchestrator_agent import OrchestratorAgent

async def search_and_apply():
    orchestrator = OrchestratorAgent()
    
    result = await orchestrator.execute({
        "role": "Software Engineer",
        "resume_path": "./resume.docx",
        "location": "remote",
        "max_jobs": 20,
        "auto_apply": False  # Set to True for actual applications
    })
    
    print(f"Found {result['summary']['jobs_found']} jobs")
    return result

# Run the workflow
result = asyncio.run(search_and_apply())
```

### Individual Agent Usage

```python
from agents.skills_analysis_agent import SkillsAnalysisAgent

# Analyze job skills
skills_agent = SkillsAnalysisAgent()
result = await skills_agent.execute({
    "job_description": "We need a Python developer with Django experience..."
})

print(result["required_skills"])
```

## 📊 Reports and Analytics

The system generates comprehensive reports:

### Session Reports
- Application success rates
- Skill gap analysis
- Company targeting insights
- Timeline analytics

### Weekly Reports
- Performance trends
- Market insights
- Skill demand analysis

### Skill Gap Reports
- Missing skills identification
- Learning recommendations
- Market demand trends

### Accessing Reports

```python
from utils.report_generator import ReportGenerator

# Generate session report
reporter = ReportGenerator()
report = reporter.generate_session_report("session_20240101_120000")

# Generate visual charts
chart_file = reporter.create_visual_report("session_20240101_120000")
```

## 🔒 Safety and Ethics

### Important Considerations

1. **Rate Limiting**: Built-in delays prevent overwhelming job sites
2. **Simulation Mode**: Test applications without actually submitting
3. **Authentication**: Most job sites require manual login setup
4. **Terms of Service**: Ensure compliance with job board policies
5. **Data Privacy**: All data stored locally by default

### Best Practices

- Start with `--dry-run` to test the system
- Use reasonable daily application limits
- Review generated resumes before submission
- Respect job board rate limits and terms of service
- Keep your API keys secure

## 🐛 Troubleshooting

### Common Issues

1. **OpenAI API Errors**:
   ```bash
   # Check API key
   python main.py --config-check
   ```

2. **Browser Issues**:
   ```bash
   # Update Chrome driver
   pip install --upgrade selenium webdriver-manager
   ```

3. **Resume Parsing Errors**:
   - Ensure resume is in .docx format
   - Check file permissions
   - Verify file path is correct

4. **Job Site Blocking**:
   - Increase delays between requests
   - Use different user agents
   - Implement proxy rotation

### Debug Mode

```bash
# Enable verbose logging
python main.py --role "Developer" --resume "./resume.docx" --verbose
```

## 🔮 Advanced Features

### Custom Job Sources

Add new job sites by extending the `JobSearchAgent`:

```python
class CustomJobSearchAgent(JobSearchAgent):
    async def _search_custom_site(self, role, location, max_jobs):
        # Implement custom job site search
        pass
```

### Resume Templates

Create custom resume templates in the `data/` directory:

```python
# Custom resume formatting
from docx import Document

def create_custom_resume(content):
    doc = Document("./data/custom_template.docx")
    # Customize resume format
    return doc
```

### Skill Databases

Extend skill recognition with custom databases:

```python
# Add industry-specific skills
custom_skills = {
    "fintech": ["blockchain", "cryptocurrency", "trading systems"],
    "healthcare": ["HIPAA", "HL7", "medical imaging"]
}
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Add tests for new functionality
4. Submit a pull request

### Development Setup

```bash
# Install development dependencies
pip install -r requirements-dev.txt

# Run tests
pytest tests/

# Run linting
flake8 agents/ utils/
```

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## ⚠️ Disclaimer

This tool is for educational and personal use. Users are responsible for:
- Complying with job board terms of service
- Ensuring accuracy of application materials
- Respecting rate limits and anti-bot measures
- Following applicable laws and regulations

Use responsibly and ethically. The authors are not responsible for any misuse or consequences.

## 🆘 Support

- **Documentation**: Check this README and code comments
- **Issues**: Report bugs via GitHub issues
- **Discussions**: Use GitHub discussions for questions

## 🗺️ Roadmap

- [ ] LinkedIn API integration
- [ ] PDF resume support
- [ ] Machine learning skill matching
- [ ] Email notification system
- [ ] Web dashboard interface
- [ ] Integration with job tracking systems
- [ ] Advanced analytics and ML insights

---

Built with ❤️ for job seekers everywhere. Good luck with your job search!
