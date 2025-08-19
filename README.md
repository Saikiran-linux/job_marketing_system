# LangGraph-based Job Application System

A sophisticated multi-agent system for automated job searching and application, built with **LangGraph** for robust workflow orchestration.

## 🚀 What's New in LangGraph Version

This system has been completely rewritten to use **LangGraph** instead of LangChain, providing:

- **Declarative Workflow Definition**: Clear, visual workflow graphs
- **Built-in State Management**: Automatic state flow between agents
- **Better Error Handling**: Robust error recovery and state persistence
- **Scalable Architecture**: Easy to add new agents and workflow steps
- **Modern Async Support**: Full async/await support throughout

## 🏗️ Architecture Overview

The system uses LangGraph's workflow approach with the following structure:

```
resume_analysis → job_search → process_jobs → generate_report
```

### Core Components

- **OrchestratorAgent**: Main workflow coordinator using LangGraph
- **AgentState**: Centralized state object that flows through the workflow
- **Specialized Agents**: Each handling specific tasks (resume analysis, job search, etc.)
- **Workflow Graph**: Declarative definition of the entire process

## 🛠️ Installation

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
   # Edit .env with your API keys
   ```

## 🔑 Environment Variables

```bash
# OpenAI API for AI-powered features
OPENAI_API_KEY=your_openai_api_key

# LinkedIn API (optional)
LINKEDIN_CLIENT_ID=your_linkedin_client_id
LINKEDIN_CLIENT_SECRET=your_linkedin_client_secret
LINKEDIN_ACCESS_TOKEN=your_linkedin_access_token
```

## 🚀 Quick Start

### Run the Full Workflow

```bash
python main.py
```

### Run Example Workflow

```bash
python main.py --example
```

### Run LangGraph Demo

```bash
python examples/langgraph_example.py
```

## 📋 Usage Examples

### Basic Workflow Execution

```python
from agents.orchestrator_agent import OrchestratorAgent
from agents.base_agent import AgentState

# Create initial state
state = AgentState(
    role="Software Engineer",
    resume_path="./resume.docx",
    location="San Francisco, CA",
    max_jobs=5,
    auto_apply=False
)

# Execute workflow
orchestrator = OrchestratorAgent()
final_state = await orchestrator.execute(state)

# Check results
if final_state.status == "completed":
    print(f"Jobs processed: {len(final_state.processed_jobs)}")
    print(f"Success rate: {final_state.final_report['summary']['success_rate']}%")
```

### Custom Workflow Creation

```python
from langgraph.graph import StateGraph, END
from agents.base_agent import AgentState

# Create custom workflow
workflow = StateGraph(AgentState)

# Add nodes
workflow.add_node("custom_step", custom_agent.create_node())
workflow.add_node("another_step", another_agent.create_node())

# Define flow
workflow.set_entry_point("custom_step")
workflow.add_edge("custom_step", "another_step")
workflow.add_edge("another_step", END)

# Compile and use
compiled_workflow = workflow.compile()
result = await compiled_workflow.ainvoke(initial_state)
```

## 🤖 Agent System

### Base Agent

All agents inherit from `BaseAgent` and implement:
- `execute(state: AgentState) -> AgentState`: Main execution logic
- `create_node() -> callable`: LangGraph node creation
- Built-in error handling and retries

### Specialized Agents

- **ResumeAnalysisAgent**: Analyzes resumes and extracts skills
- **JobSearchAgent**: Searches multiple job sources
- **SkillsAnalysisAgent**: Analyzes job requirements
- **ResumeModificationAgent**: Tailors resumes for specific jobs
- **ApplicationAgent**: Automates job applications
- **LinkedInAgent**: LinkedIn-specific operations

## 🔄 Workflow States

The `AgentState` object flows through the entire workflow:

```python
class AgentState(BaseModel):
    # Core workflow info
    session_id: str
    start_time: str
    current_step: str
    steps_completed: list
    status: str
    error: Optional[str]
    
    # Input parameters
    role: str
    resume_path: str
    location: str
    max_jobs: int
    auto_apply: bool
    
    # Results from each step
    resume_analysis: Optional[Dict]
    job_search_results: Optional[Dict]
    processed_jobs: list
    final_report: Optional[Dict]
    
    # Metadata
    end_time: Optional[str]
    workflow_duration: Optional[str]
```

## 📊 Monitoring and Debugging

### Workflow Status

```python
# Get workflow status by session ID
status = await orchestrator.get_workflow_status("session_123")
print(f"Status: {status['workflow_state']['status']}")
```

### Agent Statistics

```python
# Get statistics from all agents
stats = orchestrator.get_agent_stats()
for agent_name, agent_stats in stats.items():
    print(f"{agent_name}: {agent_stats['execution_count']} executions")
```

### Workflow Graph Inspection

```python
# Inspect the workflow structure
workflow = orchestrator.get_workflow_graph()
print(f"Nodes: {workflow.nodes}")
print(f"Entry point: {workflow.entry_point}")
```

## 🔧 Configuration

Edit `config.py` to customize:

- Job search limits
- Application delays
- File paths
- API endpoints
- Default locations

## 📁 Project Structure

```
marketin_jobs_/
├── agents/                    # Agent implementations
│   ├── base_agent.py         # Base agent class
│   ├── orchestrator_agent.py # Main workflow coordinator
│   ├── job_search_agent.py   # Job search functionality
│   ├── resume_analysis_agent.py # Resume analysis
│   ├── skills_analysis_agent.py # Skills extraction
│   ├── resume_modification_agent.py # Resume tailoring
│   ├── application_agent.py  # Job application
│   └── linkedin_agent.py     # LinkedIn integration
├── examples/                  # Usage examples
│   ├── langgraph_example.py  # LangGraph demo
│   └── ...                   # Other examples
├── utils/                     # Utility functions
├── main.py                    # Main entry point
├── requirements.txt           # Dependencies
└── README.md                 # This file
```

## 🚀 Advanced Features

### Custom Workflow Nodes

```python
def custom_node(state: AgentState) -> AgentState:
    """Custom workflow node."""
    # Your custom logic here
    state.steps_completed.append("custom_step")
    return state

# Add to workflow
workflow.add_node("custom", custom_node)
```

### Conditional Workflows

```python
def should_continue(state: AgentState) -> str:
    """Conditional routing based on state."""
    if state.error:
        return "error_handler"
    elif state.current_step == "completed":
        return END
    else:
        return "next_step"

# Add conditional edges
workflow.add_conditional_edges("current_step", should_continue)
```

### State Persistence

```python
# Save workflow state
await orchestrator._save_workflow_state(final_state)

# Load workflow state
status = await orchestrator.get_workflow_status(session_id)
```

## 🧪 Testing

### Run Tests

```bash
# Run all tests
python -m pytest

# Run specific test file
python -m pytest tests/test_orchestrator.py

# Run with coverage
python -m pytest --cov=agents
```

### Example Test

```python
import pytest
from agents.orchestrator_agent import OrchestratorAgent
from agents.base_agent import AgentState

@pytest.mark.asyncio
async def test_workflow_execution():
    orchestrator = OrchestratorAgent()
    state = AgentState(role="Test", resume_path="./test.docx")
    
    result = await orchestrator.execute(state)
    assert result.status in ["completed", "error"]
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests
5. Submit a pull request

## 📄 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🙏 Acknowledgments

- **LangGraph** team for the excellent workflow framework
- **OpenAI** for AI capabilities
- **LinkedIn** for job search APIs
- **Community contributors** for feedback and improvements

## 📞 Support

For questions and support:
- Open an issue on GitHub
- Check the examples directory
- Review the agent documentation

---

**Happy job hunting with LangGraph! 🚀**
