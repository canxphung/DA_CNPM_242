# src/external_api/response_parser.py
import json
import re

class ResponseParser:
    """
    Utilities for parsing and structuring responses from OpenAI API.
    """
    
    @staticmethod
    def parse_json_response(response_text):
        """
        Parse a JSON response from the API.
        
        Args:
            response_text: Response text from API
            
        Returns:
            Parsed JSON object or None on failure
        """
        try:
            # Try to parse as JSON directly
            return json.loads(response_text)
        except json.JSONDecodeError:
            # If not a valid JSON, try to extract JSON from the text
            json_match = re.search(r'```json(.*?)```', response_text, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1).strip())
                except json.JSONDecodeError:
                    pass
            
            # Try to extract JSON using regex
            try:
                # Find content between braces
                json_pattern = r'({.*})'
                match = re.search(json_pattern, response_text, re.DOTALL)
                if match:
                    return json.loads(match.group(1))
            except (json.JSONDecodeError, AttributeError):
                pass
            
            # Extract key-value pairs manually as a last resort
            result = {}
            
            # Look for irrigation recommendation
            irrigation_match = re.search(
                r'should_irrigate["\']?\s*:\s*(["\']?true["\']?|["\']?false["\']?|true|false)',
                response_text,
                re.IGNORECASE
            )
            if irrigation_match:
                value = irrigation_match.group(1).lower()
                result['should_irrigate'] = 'true' in value
            
            # Look for duration
            duration_match = re.search(
                r'duration_minutes["\']?\s*:\s*(\d+)',
                response_text
            )
            if duration_match:
                result['duration_minutes'] = int(duration_match.group(1))
            
            # Look for reason
            reason_match = re.search(
                r'reason["\']?\s*:\s*["\']([^"\']+)["\']',
                response_text
            )
            if reason_match:
                result['reason'] = reason_match.group(1)
            
            return result if result else None
    
    @staticmethod
    def extract_intent(response_text):
        """
        Extract intent from response text.
        
        Args:
            response_text: Response text from API
            
        Returns:
            Intent string or None
        """
        # Try to parse as JSON first
        parsed = ResponseParser.parse_json_response(response_text)
        if parsed and 'intent' in parsed:
            return parsed['intent']
        
        # If not JSON, look for intent directly
        intent_match = re.search(r'intent["\']?\s*:\s*["\']?([^"\'}\s,]+)', response_text)
        if intent_match:
            return intent_match.group(1)
        
        # Look for intent mentioned directly
        known_intents = [
            'query_soil_moisture', 'query_temperature', 'query_humidity',
            'query_light', 'turn_on_pump', 'turn_off_pump', 'get_status',
            'schedule_irrigation'
        ]
        
        for intent in known_intents:
            if intent in response_text:
                return intent
        
        return None
    
    @staticmethod
    def extract_irrigation_recommendation(response_text):
        """
        Extract irrigation recommendation from response text.
        
        Args:
            response_text: Response text from API
            
        Returns:
            Dictionary with recommendation or default values
        """
        parsed = ResponseParser.parse_json_response(response_text)
        
        if parsed:
            return {
                'should_irrigate': parsed.get('should_irrigate', False),
                'duration_minutes': parsed.get('duration_minutes', 10),
                'reason': parsed.get('reason', 'Based on analysis')
            }
        
        # Default recommendation if parsing fails
        return {
            'should_irrigate': False,
            'duration_minutes': 10,
            'reason': 'Could not parse recommendation',
            'error': 'Failed to parse API response'
        }
    
    @staticmethod
    def extract_entities(response_text):
        """
        Extract entities from response text.
        
        Args:
            response_text: Response text from API
            
        Returns:
            Dictionary of entities
        """
        parsed = ResponseParser.parse_json_response(response_text)
        
        if parsed and 'entities' in parsed:
            return parsed['entities']
        
        # Try to extract common entities manually
        entities = {}
        
        # Extract numbers
        number_matches = re.findall(r'(\d+)\s*(phút|giờ|tiếng|%|độ|celsius)', response_text, re.IGNORECASE)
        
        for match in number_matches:
            value, unit = match
            
            if unit in ['phút']:
                entities['duration_minutes'] = int(value)
            elif unit in ['giờ', 'tiếng']:
                entities['duration_minutes'] = int(value) * 60
            elif unit in ['%']:
                entities['percentage'] = int(value)
            elif unit in ['độ', 'celsius']:
                entities['temperature'] = int(value)
        
        return entities