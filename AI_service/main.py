#!/usr/bin/env python
# main.py - Entry point for Greenhouse AI Service

import os
import sys
import argparse
import logging
import asyncio
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('greenhouse_ai.log')
    ]
)
logger = logging.getLogger('main')

def start_api_server():
    """Start the FastAPI server."""
    from src.api.app import start
    logger.info("Starting API server")
    start()

def start_console_mode():
    """Start in console mode for testing and debugging."""
    import json
    import config.config as app_config
    from src.core.greenhouse_ai_service import GreenhouseAIService
    
    logger.info("Starting in console mode")
    
    # Initialize service
    service = GreenhouseAIService(config=app_config)
    service.start()
    
    async def run_test():
        """Run some test operations."""
        try:
            # Test creating a recommendation
            logger.info("Testing recommendation creation...")
            plant_types = ["tomato", "cucumber", "lettuce"]
            
            recommendation = await service.create_irrigation_recommendation(
                plant_types=plant_types,
                zones=None,
                priority="normal"
            )
            
            logger.info(f"Created recommendation: {json.dumps(recommendation, indent=2)}")
            
            # Test sending recommendation to Core Operations
            logger.info("Testing sending recommendation to Core Operations...")
            try:
                send_result = await service.send_recommendation_to_core(
                    recommendation_id=recommendation['id'],
                    priority="normal"
                )
                
                logger.info(f"Send result: {json.dumps(send_result, indent=2)}")
            except Exception as e:
                logger.error(f"Error sending recommendation to Core Operations: {str(e)}")
            
            # Test fetching sensor data
            logger.info("Testing sensor data retrieval...")
            try:
                sensor_data = await service.core_ops_integration.fetch_sensor_data(hours=24)
                logger.info(f"Retrieved {len(sensor_data)} sensor data points")
            except Exception as e:
                logger.error(f"Error fetching sensor data: {str(e)}")
            
            logger.info("All tests completed successfully!")
            
        except Exception as e:
            logger.error(f"Error during test: {str(e)}")
        finally:
            # Stop the service
            await service.stop()
    
    # Run the test
    asyncio.run(run_test())

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Greenhouse AI Service')
    parser.add_argument('--mode', choices=['api', 'console'], default='api',
                        help='Run mode: api (default) or console')
    args = parser.parse_args()
    
    if args.mode == 'api':
        start_api_server()
    else:
        start_console_mode()

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        logger.info("Service stopped by user")
    except Exception as e:
        logger.critical(f"Unhandled exception: {str(e)}", exc_info=True)
        sys.exit(1)