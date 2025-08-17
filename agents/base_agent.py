from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
import asyncio
from datetime import datetime
from utils.logger import setup_logger

class BaseAgent(ABC):
    """Base class for all agents in the job application system."""
    
    def __init__(self, name: str, max_retries: int = 3):
        self.name = name
        self.max_retries = max_retries
        self.logger = setup_logger(name)
        self.execution_count = 0
        self.last_execution = None
        
    @abstractmethod
    async def execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute the agent's main functionality."""
        pass
    
    async def safe_execute(self, input_data: Dict[str, Any]) -> Dict[str, Any]:
        """Execute with error handling and retries."""
        self.execution_count += 1
        self.last_execution = datetime.now()
        
        for attempt in range(self.max_retries):
            try:
                self.log_action("STARTING", f"Attempt {attempt + 1}/{self.max_retries}")
                result = await self.execute(input_data)
                self.log_action("SUCCESS", f"Execution completed successfully")
                return result
                
            except Exception as e:
                self.log_action("ERROR", f"Attempt {attempt + 1} failed: {str(e)}")
                
                if attempt == self.max_retries - 1:
                    self.log_action("FAILED", f"All {self.max_retries} attempts failed")
                    return {
                        "status": "error",
                        "error": str(e),
                        "agent": self.name,
                        "attempts": self.max_retries
                    }
                
                # Wait before retry (exponential backoff)
                wait_time = 2 ** attempt
                await asyncio.sleep(wait_time)
    
    def log_action(self, action: str, details: str):
        """Log agent actions with consistent formatting."""
        self.logger.info(f"{self.name} [{action}]: {details}")
    
    def validate_input(self, input_data: Dict[str, Any], required_fields: list) -> bool:
        """Validate that required input fields are present."""
        missing_fields = [field for field in required_fields if field not in input_data]
        
        if missing_fields:
            self.log_action("VALIDATION_ERROR", f"Missing required fields: {missing_fields}")
            return False
        
        return True
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent execution statistics."""
        return {
            "name": self.name,
            "execution_count": self.execution_count,
            "last_execution": self.last_execution.isoformat() if self.last_execution else None
        }
