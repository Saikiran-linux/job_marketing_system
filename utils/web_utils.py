"""
Web automation utilities for improved timeout handling and page loading.
"""

import asyncio
import random
from typing import Optional, List, Dict, Any
from playwright.async_api import Page, TimeoutError as PlaywrightTimeoutError
from config import Config

class WebUtils:
    """Utility class for improved web automation with better timeout handling."""
    
    # Default timeout values (in milliseconds) - from config
    DEFAULT_TIMEOUT = Config.PAGE_LOAD_TIMEOUT * 1000  # Convert seconds to milliseconds
    AUTH_TIMEOUT = Config.AUTH_TIMEOUT * 1000
    SEARCH_TIMEOUT = Config.SEARCH_TIMEOUT * 1000
    ELEMENT_TIMEOUT = Config.ELEMENT_TIMEOUT * 1000
    
    @staticmethod
    async def wait_for_page_load(page: Page, timeout: int = None) -> bool:
        """
        Wait for page to load using multiple strategies.
        
        Args:
            page: Playwright page object
            timeout: Timeout in milliseconds
            
        Returns:
            True if page loaded successfully, False otherwise
        """
        if timeout is None:
            timeout = WebUtils.DEFAULT_TIMEOUT
            
        try:
            # Strategy 1: Wait for network idle
            await page.wait_for_load_state("networkidle", timeout=timeout)
            return True
        except PlaywrightTimeoutError:
            try:
                # Strategy 2: Wait for DOM content loaded
                await page.wait_for_load_state("domcontentloaded", timeout=timeout // 2)
                # Add a small delay to allow for dynamic content
                await asyncio.sleep(2)
                return True
            except PlaywrightTimeoutError:
                try:
                    # Strategy 3: Wait for load event
                    await page.wait_for_load_state("load", timeout=timeout // 3)
                    return True
                except PlaywrightTimeoutError:
                    # Strategy 4: Just wait a bit and continue
                    await asyncio.sleep(3)
                    return False
    
    @staticmethod
    async def wait_for_element_smart(page: Page, selectors: List[str], 
                                   timeout: int = None, 
                                   visible: bool = True) -> Optional[Any]:
        """
        Wait for element using multiple selectors with smart fallback.
        
        Args:
            page: Playwright page object
            selectors: List of CSS selectors to try
            timeout: Timeout in milliseconds
            visible: Whether to wait for element to be visible
            
        Returns:
            Element if found, None otherwise
        """
        if timeout is None:
            timeout = WebUtils.ELEMENT_TIMEOUT
            
        # Try each selector with progressive timeout
        for i, selector in enumerate(selectors):
            try:
                # Progressive timeout: start with shorter timeouts for later selectors
                current_timeout = max(timeout // (i + 1), 5000)
                
                if visible:
                    element = await page.wait_for_selector(selector, timeout=current_timeout)
                else:
                    element = await page.wait_for_selector(selector, timeout=current_timeout, state="attached")
                
                if element:
                    return element
                    
            except PlaywrightTimeoutError:
                continue
        
        return None
    
    @staticmethod
    async def wait_for_multiple_elements(page: Page, selectors: List[str], 
                                      timeout: int = None, 
                                      min_count: int = 1) -> List[Any]:
        """
        Wait for multiple elements to be present.
        
        Args:
            page: Playwright page object
            selectors: List of CSS selectors to try
            timeout: Timeout in milliseconds
            min_count: Minimum number of elements required
            
        Returns:
            List of found elements
        """
        if timeout is None:
            timeout = WebUtils.ELEMENT_TIMEOUT
            
        # Try each selector
        for selector in selectors:
            try:
                # Wait for elements with timeout
                await page.wait_for_selector(selector, timeout=timeout)
                
                # Get all matching elements
                elements = await page.query_selector_all(selector)
                
                if len(elements) >= min_count:
                    return elements
                    
            except PlaywrightTimeoutError:
                continue
        
        return []
    
    @staticmethod
    async def fill_form_field_smart(page: Page, field_selectors: List[str], 
                                  value: str, timeout: int = None) -> bool:
        """
        Fill a form field using multiple selector strategies.
        
        Args:
            page: Playwright page object
            field_selectors: List of CSS selectors for the field
            value: Value to fill
            timeout: Timeout in milliseconds
            
        Returns:
            True if field was filled successfully, False otherwise
        """
        if timeout is None:
            timeout = WebUtils.ELEMENT_TIMEOUT
            
        element = await WebUtils.wait_for_element_smart(page, field_selectors, timeout)
        
        if element:
            try:
                # Clear the field first
                await element.fill("")
                # Fill with value
                await element.fill(value)
                return True
            except Exception:
                return False
        
        return False
    
    @staticmethod
    async def click_element_smart(page: Page, selectors: List[str], 
                                timeout: int = None) -> bool:
        """
        Click an element using multiple selector strategies.
        
        Args:
            page: Playwright page object
            selectors: List of CSS selectors for the element
            timeout: Timeout in milliseconds
            
        Returns:
            True if element was clicked successfully, False otherwise
        """
        if timeout is None:
            timeout = WebUtils.ELEMENT_TIMEOUT
            
        element = await WebUtils.wait_for_element_smart(page, selectors, timeout)
        
        if element:
            try:
                await element.click()
                return True
            except Exception:
                return False
        
        return False
    
    @staticmethod
    async def retry_with_backoff(func, max_retries: int = 3, 
                               base_delay: float = 1.0, 
                               max_delay: float = 10.0):
        """
        Retry a function with exponential backoff.
        
        Args:
            func: Async function to retry
            max_retries: Maximum number of retry attempts
            base_delay: Base delay between retries in seconds
            max_delay: Maximum delay between retries in seconds
            
        Returns:
            Result of the function if successful
            
        Raises:
            Exception: If all retries fail
        """
        last_exception = None
        
        for attempt in range(max_retries):
            try:
                return await func()
            except Exception as e:
                last_exception = e
                
                if attempt < max_retries - 1:
                    # Calculate delay with exponential backoff
                    delay = min(base_delay * (2 ** attempt), max_delay)
                    # Add some randomness to avoid thundering herd
                    delay += random.uniform(0, 1)
                    
                    await asyncio.sleep(delay)
        
        # If we get here, all retries failed
        raise last_exception
    
    @staticmethod
    async def wait_for_network_stable(page: Page, timeout: int = None, 
                                    min_requests: int = 0) -> bool:
        """
        Wait for network to be stable (no new requests for a period).
        
        Args:
            page: Playwright page object
            timeout: Timeout in milliseconds
            min_requests: Minimum number of requests to wait for
            
        Returns:
            True if network is stable, False otherwise
        """
        if timeout is None:
            timeout = WebUtils.DEFAULT_TIMEOUT
            
        try:
            # Wait for network idle
            await page.wait_for_load_state("networkidle", timeout=timeout)
            
            # Additional wait to ensure stability
            await asyncio.sleep(2)
            
            return True
            
        except PlaywrightTimeoutError:
            # If network idle times out, wait a bit more and continue
            await asyncio.sleep(3)
            return False
    
    @staticmethod
    def get_adaptive_timeout(base_timeout: int, network_condition: str = "normal") -> int:
        """
        Get adaptive timeout based on network conditions.
        
        Args:
            base_timeout: Base timeout in milliseconds
            network_condition: Network condition ("slow", "normal", "fast")
            
        Returns:
            Adjusted timeout in milliseconds
        """
        multipliers = {
            "slow": 2.5,
            "normal": 1.0,
            "fast": 0.7
        }
        
        return int(base_timeout * multipliers.get(network_condition, 1.0))
