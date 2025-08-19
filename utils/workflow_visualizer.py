#!/usr/bin/env python3
"""
Workflow Visualizer for Multi-Agent Job Application System

This module generates visual representations of the system workflow,
showing how different agents interact and process data.
"""

import os
import json
from typing import Dict, Any, List, Optional
from datetime import datetime
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import FancyBboxPatch, ConnectionPatch
import networkx as nx
from agents.orchestrator_agent import OrchestratorAgent
from agents.base_agent import AgentState

class WorkflowVisualizer:
    """Visualizes the multi-agent system workflow."""
    
    def __init__(self):
        """Initialize the workflow visualizer."""
        self.colors = {
            'orchestrator': '#FF6B6B',      # Red
            'resume_analysis': '#4ECDC4',   # Teal
            'job_search': '#45B7D1',        # Blue
            'skills_analysis': '#96CEB4',   # Green
            'resume_modification': '#FFEAA7', # Yellow
            'application': '#DDA0DD',       # Plum
            'report_generation': '#98D8C8', # Mint
            'data_flow': '#F7DC6F',         # Gold
            'decision': '#BB8FCE',          # Purple
            'endpoint': '#85C1E9'           # Light Blue
        }
        
    def generate_workflow_graph(self, save_path: Optional[str] = None) -> str:
        """
        Generate a comprehensive workflow graph of the multi-agent system.
        
        Args:
            save_path: Optional path to save the graph image
            
        Returns:
            Path to the saved graph image
        """
        
        # Create figure and axis
        fig, ax = plt.subplots(1, 1, figsize=(16, 12))
        ax.set_xlim(0, 10)
        ax.set_ylim(0, 12)
        ax.axis('off')
        
        # Title
        ax.text(5, 11.5, 'Multi-Agent Job Application System Workflow', 
                fontsize=20, fontweight='bold', ha='center')
        
        # Define agent positions and details
        agents = {
            'orchestrator': {
                'pos': (5, 10),
                'size': (2, 1),
                'color': self.colors['orchestrator'],
                'title': 'Orchestrator Agent',
                'description': 'Coordinates all agents\nManages workflow state\nHandles errors'
            },
            'resume_analysis': {
                'pos': (1, 8),
                'size': (1.5, 0.8),
                'color': self.colors['resume_analysis'],
                'title': 'Resume Analysis',
                'description': 'Extracts skills\nAnalyzes content\nIdentifies sections'
            },
            'job_search': {
                'pos': (3, 8),
                'size': (1.5, 0.8),
                'color': self.colors['job_search'],
                'title': 'Job Search',
                'description': 'Searches job boards\nFilters results\nExtracts job details'
            },
            'skills_analysis': {
                'pos': (5, 8),
                'size': (1.5, 0.8),
                'color': self.colors['skills_analysis'],
                'title': 'Skills Analysis',
                'description': 'Analyzes job requirements\nIdentifies skill gaps\nRanks skills'
            },
            'resume_modification': {
                'pos': (7, 8),
                'size': (1.5, 0.8),
                'color': self.colors['resume_modification'],
                'title': 'Resume Modification',
                'description': 'Optimizes content\nAdds keywords\nATS optimization'
            },
            'application': {
                'pos': (5, 6),
                'size': (1.5, 0.8),
                'color': self.colors['application'],
                'title': 'Application Agent',
                'description': 'Submits applications\nHandles forms\nTracks status'
            },
            'report_generation': {
                'pos': (5, 4),
                'size': (1.5, 0.8),
                'color': self.colors['report_generation'],
                'title': 'Report Generation',
                'description': 'Creates summaries\nAnalyzes results\nProvides insights'
            }
        }
        
        # Draw agents
        for agent_id, agent_info in agents.items():
            self._draw_agent(ax, agent_info)
        
        # Draw data flow arrows
        self._draw_data_flow(ax, agents)
        
        # Draw workflow stages
        self._draw_workflow_stages(ax)
        
        # Add legend
        self._draw_legend(ax)
        
        # Add system architecture notes
        self._draw_architecture_notes(ax)
        
        # Save the graph
        if not save_path:
            save_path = f"workflow_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def _draw_agent(self, ax, agent_info: Dict[str, Any]):
        """Draw an individual agent box."""
        x, y = agent_info['pos']
        width, height = agent_info['size']
        color = agent_info['color']
        title = agent_info['title']
        description = agent_info['description']
        
        # Draw agent box
        box = FancyBboxPatch(
            (x - width/2, y - height/2), width, height,
            boxstyle="round,pad=0.1",
            facecolor=color,
            edgecolor='black',
            linewidth=2
        )
        ax.add_patch(box)
        
        # Add title
        ax.text(x, y + height/4, title, fontsize=12, fontweight='bold', 
                ha='center', va='center')
        
        # Add description
        ax.text(x, y - height/4, description, fontsize=9, ha='center', va='center')
    
    def _draw_data_flow(self, ax, agents: Dict[str, Any]):
        """Draw data flow arrows between agents."""
        
        # Define flow connections
        flows = [
            ('orchestrator', 'resume_analysis', 'Resume Path'),
            ('orchestrator', 'job_search', 'Job Criteria'),
            ('resume_analysis', 'skills_analysis', 'Skills Data'),
            ('job_search', 'skills_analysis', 'Job Requirements'),
            ('skills_analysis', 'resume_modification', 'Skill Gaps'),
            ('resume_modification', 'application', 'Modified Resume'),
            ('application', 'report_generation', 'Application Results'),
            ('orchestrator', 'report_generation', 'Workflow State')
        ]
        
        for start_agent, end_agent, label in flows:
            start_pos = agents[start_agent]['pos']
            end_pos = agents[end_agent]['pos']
            
            # Draw arrow
            arrow = ConnectionPatch(
                start_pos, end_pos, "data", "data",
                arrowstyle="->", shrinkA=5, shrinkB=5,
                mutation_scale=20, fc="black", ec="black",
                linewidth=2
            )
            ax.add_patch(arrow)
            
            # Add flow label
            mid_x = (start_pos[0] + end_pos[0]) / 2
            mid_y = (start_pos[1] + end_pos[1]) / 2
            ax.text(mid_x, mid_y, label, fontsize=8, ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.2", facecolor='white', alpha=0.8))
    
    def _draw_workflow_stages(self, ax):
        """Draw workflow stage indicators."""
        
        stages = [
            (1, 2, 'Stage 1: Input & Analysis'),
            (3, 2, 'Stage 2: Processing & Optimization'),
            (5, 2, 'Stage 3: Application & Submission'),
            (7, 2, 'Stage 4: Reporting & Analytics')
        ]
        
        for x, y, stage_name in stages:
            # Draw stage box
            stage_box = FancyBboxPatch(
                (x - 1, y - 0.3), 2, 0.6,
                boxstyle="round,pad=0.1",
                facecolor=self.colors['data_flow'],
                edgecolor='black',
                linewidth=1
            )
            ax.add_patch(stage_box)
            
            # Add stage text
            ax.text(x, y, stage_name, fontsize=10, fontweight='bold',
                   ha='center', va='center')
    
    def _draw_legend(self, ax):
        """Draw a legend explaining the colors and components."""
        
        legend_items = [
            ('Orchestrator', self.colors['orchestrator']),
            ('Analysis Agents', self.colors['resume_analysis']),
            ('Processing Agents', self.colors['skills_analysis']),
            ('Action Agents', self.colors['application']),
            ('Output Agents', self.colors['report_generation'])
        ]
        
        legend_x = 8.5
        legend_y = 10
        
        ax.text(legend_x, legend_y + 1, 'Agent Types', fontsize=12, fontweight='bold')
        
        for i, (name, color) in enumerate(legend_items):
            y_pos = legend_y - i * 0.4
            # Draw color box
            color_box = patches.Rectangle((legend_x, y_pos - 0.1), 0.3, 0.2,
                                        facecolor=color, edgecolor='black')
            ax.add_patch(color_box)
            # Add label
            ax.text(legend_x + 0.4, y_pos, name, fontsize=9, va='center')
    
    def _draw_architecture_notes(self, ax):
        """Draw system architecture notes."""
        
        notes = [
            "• LangGraph-based workflow orchestration",
            "• Pydantic models for state management",
            "• Async/await for concurrent processing",
            "• AI-powered content optimization",
            "• Multi-platform job application support",
            "• Comprehensive error handling & logging"
        ]
        
        notes_x = 0.5
        notes_y = 1.5
        
        ax.text(notes_x, notes_y + 0.5, 'System Architecture', 
                fontsize=11, fontweight='bold')
        
        for i, note in enumerate(notes):
            y_pos = notes_y - i * 0.25
            ax.text(notes_x, y_pos, note, fontsize=8, va='center')
    
    def generate_network_graph(self, save_path: Optional[str] = None) -> str:
        """
        Generate a network graph representation using NetworkX.
        
        Args:
            save_path: Optional path to save the network graph
            
        Returns:
            Path to the saved network graph image
        """
        
        # Create directed graph
        G = nx.DiGraph()
        
        # Add nodes (agents)
        agents = [
            'Orchestrator',
            'Resume Analysis',
            'Job Search',
            'Skills Analysis',
            'Resume Modification',
            'Application',
            'Report Generation'
        ]
        
        G.add_nodes_from(agents)
        
        # Add edges (workflow connections)
        edges = [
            ('Orchestrator', 'Resume Analysis'),
            ('Orchestrator', 'Job Search'),
            ('Resume Analysis', 'Skills Analysis'),
            ('Job Search', 'Skills Analysis'),
            ('Skills Analysis', 'Resume Modification'),
            ('Resume Modification', 'Application'),
            ('Application', 'Report Generation'),
            ('Orchestrator', 'Report Generation')
        ]
        
        G.add_edges_from(edges)
        
        # Create figure
        plt.figure(figsize=(12, 10))
        
        # Use hierarchical layout
        pos = nx.spring_layout(G, k=3, iterations=50)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, 
                              node_color=[self.colors['orchestrator']] + 
                                       [self.colors['resume_analysis']] * 2 +
                                       [self.colors['skills_analysis']] * 2 +
                                       [self.colors['application']] +
                                       [self.colors['report_generation']],
                              node_size=3000,
                              alpha=0.8)
        
        # Draw edges
        nx.draw_networkx_edges(G, pos, 
                              edge_color='gray',
                              arrows=True,
                              arrowsize=20,
                              arrowstyle='->',
                              width=2)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=10, font_weight='bold')
        
        # Add title
        plt.title('Multi-Agent System Network Graph', fontsize=16, fontweight='bold', pad=20)
        
        # Save the graph
        if not save_path:
            save_path = f"network_graph_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def generate_workflow_diagram(self, save_path: Optional[str] = None) -> str:
        """
        Generate a detailed workflow diagram showing the complete process flow.
        
        Args:
            save_path: Optional path to save the workflow diagram
            
        Returns:
            Path to the saved workflow diagram image
        """
        
        # Create figure
        fig, ax = plt.subplots(1, 1, figsize=(18, 14))
        ax.set_xlim(0, 12)
        ax.set_ylim(0, 14)
        ax.axis('off')
        
        # Title
        ax.text(6, 13.5, 'Complete Workflow Diagram', 
                fontsize=22, fontweight='bold', ha='center')
        
        # Define workflow steps
        workflow_steps = [
            {
                'stage': 'Input & Initialization',
                'steps': [
                    ('User Input', 'Role, Location, Resume', 1, 12),
                    ('State Creation', 'AgentState initialization', 3, 12),
                    ('Validation', 'Check required fields', 5, 12),
                    ('Session Setup', 'Generate session ID', 7, 12)
                ]
            },
            {
                'stage': 'Resume Analysis',
                'steps': [
                    ('Content Extraction', 'Parse resume file', 1, 10),
                    ('Skills Extraction', 'Identify technical skills', 3, 10),
                    ('Section Analysis', 'Experience, education', 5, 10),
                    ('Content Summary', 'Generate analysis report', 7, 10)
                ]
            },
            {
                'stage': 'Job Search & Analysis',
                'steps': [
                    ('Job Discovery', 'Search job boards', 1, 8),
                    ('Requirements Extraction', 'Parse job descriptions', 3, 8),
                    ('Skills Mapping', 'Match job requirements', 5, 8),
                    ('Gap Analysis', 'Identify missing skills', 7, 8)
                ]
            },
            {
                'stage': 'Resume Optimization',
                'steps': [
                    ('Content Optimization', 'AI-powered enhancement', 1, 6),
                    ('Keyword Addition', 'Add relevant terms', 3, 6),
                    ('ATS Optimization', 'Format for systems', 5, 6),
                    ('File Generation', 'Create modified resume', 7, 6)
                ]
            },
            {
                'stage': 'Application Process',
                'steps': [
                    ('Cover Letter', 'Generate personalized letter', 1, 4),
                    ('Form Filling', 'Auto-fill application forms', 3, 4),
                    ('Resume Upload', 'Submit modified resume', 5, 4),
                    ('Application Submit', 'Complete submission', 7, 4)
                ]
            },
            {
                'stage': 'Reporting & Analytics',
                'steps': [
                    ('Data Collection', 'Gather results', 1, 2),
                    ('Analysis', 'Process outcomes', 3, 2),
                    ('Report Generation', 'Create summary', 5, 2),
                    ('Insights', 'Provide recommendations', 7, 2)
                ]
            }
        ]
        
        # Draw workflow stages
        for stage_info in workflow_steps:
            stage_name = stage_info['stage']
            steps = stage_info['steps']
            
            # Draw stage header
            stage_y = steps[0][3] + 0.5
            ax.text(6, stage_y, stage_name, fontsize=14, fontweight='bold',
                   ha='center', va='center',
                   bbox=dict(boxstyle="round,pad=0.5", facecolor=self.colors['decision']))
            
            # Draw individual steps
            for step_name, description, x, y in steps:
                # Draw step box
                step_box = FancyBboxPatch(
                    (x - 0.8, y - 0.3), 1.6, 0.6,
                    boxstyle="round,pad=0.1",
                    facecolor=self.colors['data_flow'],
                    edgecolor='black',
                    linewidth=1
                )
                ax.add_patch(step_box)
                
                # Add step name
                ax.text(x, y + 0.1, step_name, fontsize=9, fontweight='bold',
                       ha='center', va='center')
                
                # Add description
                ax.text(x, y - 0.1, description, fontsize=7, ha='center', va='center')
        
        # Draw flow arrows between stages
        for i in range(len(workflow_steps) - 1):
            current_stage_y = workflow_steps[i][0][3] - 0.5
            next_stage_y = workflow_steps[i + 1][0][3] + 0.5
            
            # Draw vertical flow arrow
            arrow = ConnectionPatch(
                (6, current_stage_y), (6, next_stage_y), "data", "data",
                arrowstyle="->", shrinkA=5, shrinkB=5,
                mutation_scale=20, fc="black", ec="black",
                linewidth=3
            )
            ax.add_patch(arrow)
        
        # Add system features
        features = [
            "🔄 Async Processing",
            "🤖 AI-Powered Optimization",
            "📊 Real-time Analytics",
            "🛡️ Error Handling",
            "📝 Comprehensive Logging",
            "⚡ Performance Monitoring"
        ]
        
        features_x = 10
        features_y = 12
        
        ax.text(features_x, features_y + 1, 'System Features', 
                fontsize=12, fontweight='bold')
        
        for i, feature in enumerate(features):
            y_pos = features_y - i * 0.4
            ax.text(features_x, y_pos, feature, fontsize=9, va='center')
        
        # Save the diagram
        if not save_path:
            save_path = f"workflow_diagram_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
        
        plt.tight_layout()
        plt.savefig(save_path, dpi=300, bbox_inches='tight')
        plt.close()
        
        return save_path
    
    def generate_all_visualizations(self, output_dir: str = "./workflow_visualizations") -> Dict[str, str]:
        """
        Generate all types of workflow visualizations.
        
        Args:
            output_dir: Directory to save all visualizations
            
        Returns:
            Dictionary mapping visualization types to file paths
        """
        
        # Create output directory
        os.makedirs(output_dir, exist_ok=True)
        
        # Generate all visualizations
        results = {}
        
        try:
            # Workflow graph
            workflow_graph_path = os.path.join(output_dir, "workflow_graph.png")
            results['workflow_graph'] = self.generate_workflow_graph(workflow_graph_path)
            
            # Network graph
            network_graph_path = os.path.join(output_dir, "network_graph.png")
            results['network_graph'] = self.generate_network_graph(network_graph_path)
            
            # Workflow diagram
            workflow_diagram_path = os.path.join(output_dir, "workflow_diagram.png")
            results['workflow_diagram'] = self.generate_workflow_diagram(workflow_diagram_path)
            
            # Create summary file
            summary_path = os.path.join(output_dir, "visualization_summary.txt")
            self._create_summary_file(summary_path, results)
            results['summary'] = summary_path
            
        except Exception as e:
            print(f"Error generating visualizations: {str(e)}")
            results['error'] = str(e)
        
        return results
    
    def _create_summary_file(self, summary_path: str, results: Dict[str, str]):
        """Create a summary file describing all generated visualizations."""
        
        summary_content = f"""
Multi-Agent Job Application System - Workflow Visualizations
Generated on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

Generated Files:
1. Workflow Graph: {results.get('workflow_graph', 'N/A')}
   - Shows agent relationships and data flow
   - Includes system architecture notes
   - Color-coded by agent type

2. Network Graph: {results.get('network_graph', 'N/A')}
   - NetworkX-based graph representation
   - Hierarchical layout showing connections
   - Directed graph with workflow flow

3. Workflow Diagram: {results.get('workflow_diagram', 'N/A')}
   - Detailed step-by-step process flow
   - Shows all workflow stages
   - Includes system features

System Overview:
- Orchestrator Agent coordinates all operations
- Resume Analysis extracts and analyzes content
- Job Search discovers relevant opportunities
- Skills Analysis identifies requirements and gaps
- Resume Modification optimizes content
- Application Agent handles submissions
- Report Generation provides insights

Data Flow:
1. User input → State initialization
2. Resume analysis → Skills extraction
3. Job search → Requirements analysis
4. Skills mapping → Gap identification
5. Content optimization → Resume modification
6. Application submission → Status tracking
7. Results collection → Report generation

Architecture Features:
- LangGraph-based workflow orchestration
- Async/await for concurrent processing
- Pydantic models for state management
- AI-powered content optimization
- Multi-platform job application support
- Comprehensive error handling and logging
        """
        
        with open(summary_path, 'w') as f:
            f.write(summary_content)
    
    def get_visualization_tools(self) -> List[Dict[str, Any]]:
        """Get available visualization tools."""
        
        return [
            {
                "name": "generate_workflow_graph",
                "description": "Generate a comprehensive workflow graph",
                "parameters": {
                    "save_path": "Optional path to save the graph image"
                }
            },
            {
                "name": "generate_network_graph",
                "description": "Generate a network graph using NetworkX",
                "parameters": {
                    "save_path": "Optional path to save the network graph"
                }
            },
            {
                "name": "generate_workflow_diagram",
                "description": "Generate a detailed workflow diagram",
                "parameters": {
                    "save_path": "Optional path to save the workflow diagram"
                }
            },
            {
                "name": "generate_all_visualizations",
                "description": "Generate all types of workflow visualizations",
                "parameters": {
                    "output_dir": "Directory to save all visualizations"
                }
            }
        ]

def main():
    """Main function to generate workflow visualizations."""
    
    print("🚀 Generating Multi-Agent System Workflow Visualizations")
    print("=" * 60)
    
    try:
        # Create visualizer
        visualizer = WorkflowVisualizer()
        
        # Generate all visualizations
        results = visualizer.generate_all_visualizations()
        
        if 'error' not in results:
            print("✅ All visualizations generated successfully!")
            print("\nGenerated files:")
            for viz_type, file_path in results.items():
                if viz_type != 'summary':
                    print(f"   • {viz_type}: {file_path}")
            
            print(f"\n📋 Summary: {results.get('summary', 'N/A')}")
            print("\n🎯 Use these visualizations to:")
            print("   • Understand system architecture")
            print("   • Plan development and testing")
            print("   • Document system design")
            print("   • Present to stakeholders")
            
        else:
            print(f"❌ Error generating visualizations: {results['error']}")
            
    except Exception as e:
        print(f"❌ Failed to generate visualizations: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

