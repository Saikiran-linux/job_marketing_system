# Cursor MCP Configuration

This directory contains configuration for Cursor's Model Context Protocol (MCP) servers.

## ⚠️ Security Notice

The `mcp.json` file contains sensitive Supabase credentials and should **NEVER** be committed to Git.

## Setup Instructions

### Option 1: Environment Variables (Recommended)

1. Set environment variables:
   ```bash
   # Windows PowerShell
   $env:SUPABASE_PROJECT_REF="your_project_ref"
   $env:SUPABASE_ACCESS_TOKEN="your_access_token"
   
   # Windows Command Prompt
   set SUPABASE_PROJECT_REF=your_project_ref
   set SUPABASE_ACCESS_TOKEN=your_access_token
   ```

2. Run the configuration script:
   ```bash
   python .cursor/mcp_config.py
   ```

### Option 2: .env File

1. Create a `.env` file in your project root:
   ```
   SUPABASE_PROJECT_REF=your_project_ref
   SUPABASE_ACCESS_TOKEN=your_access_token
   ```

2. Run the configuration script:
   ```bash
   python .cursor/mcp_config.py
   ```

### Option 3: Manual Configuration

1. Copy `mcp.json.template` to `mcp.json`
2. Replace the placeholder values with your actual credentials

## Files

- `mcp.json` - Active configuration (generated, contains sensitive data)
- `mcp.json.template` - Template with placeholder values
- `mcp_config.py` - Script to generate configuration from environment variables
- `README.md` - This file

## Git Safety

All sensitive files are automatically ignored by `.gitignore`:
- `.cursor/mcp.json` - Contains actual credentials
- `.cursor/mcp.json.template` - Template file
- `.cursor/mcp_config.py` - Configuration script
