#!/usr/bin/env python3
"""
Workflow Visualization Example

This example demonstrates how to generate workflow visualizations
for the multi-agent job application system.
"""

import sys
import os

# Add parent directory to path to import modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.workflow_visualizer import WorkflowVisualizer

def main():
    """Demonstrate workflow visualization capabilities."""
    
    print("🎨 Multi-Agent System Workflow Visualization Example")
    print("=" * 60)
    
    try:
        # Create visualizer
        visualizer = WorkflowVisualizer()
        
        print("\n📊 Available visualization tools:")
        tools = visualizer.get_visualization_tools()
        for i, tool in enumerate(tools, 1):
            print(f"   {i}. {tool['name']}")
            print(f"      Description: {tool['description']}")
            print(f"      Parameters: {tool['parameters']}")
            print()
        
        # Generate individual visualizations
        print("🔄 Generating individual visualizations...")
        
        # 1. Workflow Graph
        print("   • Generating workflow graph...")
        workflow_graph_path = visualizer.generate_workflow_graph()
        print(f"     ✅ Saved to: {workflow_graph_path}")
        
        # 2. Network Graph
        print("   • Generating network graph...")
        network_graph_path = visualizer.generate_network_graph()
        print(f"     ✅ Saved to: {network_graph_path}")
        
        # 3. Workflow Diagram
        print("   • Generating workflow diagram...")
        workflow_diagram_path = visualizer.generate_workflow_diagram()
        print(f"     ✅ Saved to: {workflow_diagram_path}")
        
        # Generate all visualizations in organized directory
        print("\n📁 Generating all visualizations in organized directory...")
        results = visualizer.generate_all_visualizations("./workflow_visualizations")
        
        if 'error' not in results:
            print("✅ All visualizations generated successfully!")
            print("\n📋 Generated files:")
            for viz_type, file_path in results.items():
                if viz_type != 'summary':
                    print(f"   • {viz_type}: {file_path}")
            
            print(f"\n📋 Summary: {results.get('summary', 'N/A')}")
            
            print("\n🎯 Visualization Types Generated:")
            print("   1. Workflow Graph - Shows agent relationships and data flow")
            print("   2. Network Graph - NetworkX-based graph representation")
            print("   3. Workflow Diagram - Detailed step-by-step process flow")
            
            print("\n🔍 System Architecture Highlights:")
            print("   • Orchestrator Agent coordinates all operations")
            print("   • Resume Analysis extracts and analyzes content")
            print("   • Job Search discovers relevant opportunities")
            print("   • Skills Analysis identifies requirements and gaps")
            print("   • Resume Modification optimizes content")
            print("   • Application Agent handles submissions")
            print("   • Report Generation provides insights")
            
            print("\n📈 Data Flow Overview:")
            print("   1. User input → State initialization")
            print("   2. Resume analysis → Skills extraction")
            print("   3. Job search → Requirements analysis")
            print("   4. Skills mapping → Gap identification")
            print("   5. Content optimization → Resume modification")
            print("   6. Application submission → Status tracking")
            print("   7. Results collection → Report generation")
            
        else:
            print(f"❌ Error generating visualizations: {results['error']}")
            
    except Exception as e:
        print(f"❌ Failed to generate visualizations: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()

