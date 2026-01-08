"""
LLM service for OpenRouter API integration.
"""

import json
import requests
from typing import Dict, Any, Optional, List


class LLMService:
    """Service for interacting with OpenRouter LLM API."""
    
    def __init__(self, api_key: str, model: str = "openai/gpt-4o-mini"):
        """
        Initialize LLM service.
        
        Args:
            api_key: OpenRouter API key
            model: Model to use (default: gpt-4o-mini)
        """
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
    
    def _call_llm(self, prompt: str, system_prompt: Optional[str] = None) -> str:
        """
        Call OpenRouter LLM API.
        
        Args:
            prompt: User prompt
            system_prompt: Optional system prompt
            
        Returns:
            LLM response text
        """
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/your-repo",  # Optional
            "X-Title": "IT Resource Event Processor"  # Optional
        }
        
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        payload = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.3  # Lower temperature for more consistent results
        }
        
        try:
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            print(f"Error calling LLM: {e}")
            return ""
    
    def predict_failure_probability(self, resource_type: str, event: Dict[str, Any]) -> float:
        """
        Predict probability of future failures for a resource based on an event.
        
        Args:
            resource_type: Type of resource (server, workstation, automate, internet_gateway)
            event: Event data dictionary
            
        Returns:
            Failure probability as a float between 0 and 1
        """
        event_type = event.get('event_type', 'unknown')
        duration = event.get('duration_event', '0')
        
        system_prompt = """You are an IT infrastructure expert analyzing events to predict failure probabilities.
Analyze the event and provide a failure probability score between 0.0 and 1.0.
Consider the event type, resource type, and duration when making your assessment.
Respond with ONLY a JSON object containing a 'probability' field (float) and a 'reasoning' field (string)."""
        
        prompt = f"""Analyze this IT resource event and predict the probability of future failures:

Resource Type: {resource_type}
Event Type: {event_type}
Event Duration: {duration} seconds
Event ID: {event.get('event_id')}
Start Time: {event.get('timestamp_start_event')}
End Time: {event.get('timestamp_end_event')}

Based on this event, what is the probability (0.0 to 1.0) that this resource will experience future failures?
Provide your response as a JSON object with 'probability' and 'reasoning' fields."""

        response = self._call_llm(prompt, system_prompt)
        
        try:
            # Try to extract JSON from response
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            probability = float(result.get('probability', 0.5))
            return max(0.0, min(1.0, probability))  # Clamp between 0 and 1
        except (json.JSONDecodeError, ValueError, KeyError):
            # Default probability based on event type severity
            severity_map = {
                'hardware_failure': 0.9,
                'operating_system_failure': 0.8,
                'software_service_failure': 0.6,
                'cpu_overflow': 0.5,
                'hardware_maintenance_stop': 0.2,
                'software_maintenance_stop': 0.1,
                'software_update': 0.1,
                'operating_system_update': 0.2
            }
            return severity_map.get(event_type, 0.3)
    
    def evaluate_carbon_footprint(self, energy_data: Dict[str, Any], events: Dict[str, Any]) -> Dict[str, Any]:
        """
        Evaluate carbon footprint using LLM based on energy consumption and events.
        
        Args:
            energy_data: Energy consumption data
            events: Events data
            
        Returns:
            Carbon footprint evaluation dictionary
        """
        system_prompt = """You are an environmental expert calculating carbon footprints for IT infrastructure.
Calculate CO2 emissions based on energy consumption data.
Use standard conversion factors: approximately 0.5 kg CO2 per kWh (varies by region, use average).
Consider that events like maintenance stops reduce energy consumption, while overloads may increase it.
Respond with a JSON object containing 'total_co2_kg', 'co2_by_resource_type', and 'methodology' fields."""
        
        prompt = f"""Evaluate the carbon footprint for IT resources based on this energy consumption data:

{json.dumps(energy_data, indent=2)}

Consider that:
- Energy consumption is measured in watt-hours
- Convert to kWh (divide by 1000)
- Use average conversion factor of 0.5 kg CO2 per kWh
- Account for events that affect energy consumption (stops reduce consumption, overloads may increase it)

Provide a detailed carbon footprint evaluation as JSON with:
- 'total_co2_kg': total CO2 emissions in kg
- 'co2_by_resource_type': breakdown by resource type (server, workstation, automate, internet_gateway)
- 'methodology': explanation of calculation method"""

        response = self._call_llm(prompt, system_prompt)
        
        try:
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            return result
        except (json.JSONDecodeError, ValueError):
            # Fallback calculation
            return self._fallback_carbon_calculation(energy_data)
    
    def _fallback_carbon_calculation(self, energy_data: Dict[str, Any]) -> Dict[str, Any]:
        """Fallback carbon calculation if LLM fails."""
        total_wh = energy_data.get('total_energy_wh', 0)
        total_kwh = total_wh / 1000.0
        co2_per_kwh = 0.5  # kg CO2 per kWh
        total_co2 = total_kwh * co2_per_kwh
        
        co2_by_type = {}
        for resource_type in ['server', 'workstation', 'automate', 'internet_gateway']:
            wh = energy_data.get('energy_by_type', {}).get(resource_type, 0)
            kwh = wh / 1000.0
            co2_by_type[resource_type] = kwh * co2_per_kwh
        
        return {
            'total_co2_kg': round(total_co2, 2),
            'co2_by_resource_type': {k: round(v, 2) for k, v in co2_by_type.items()},
            'methodology': 'Standard calculation: energy (kWh) × 0.5 kg CO2/kWh'
        }
    
    def generate_report_summary(self, energy_data: Dict[str, Any], carbon_data: Dict[str, Any], 
                                events: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a summary report using LLM.
        
        Args:
            energy_data: Energy consumption data
            carbon_data: Carbon footprint data
            events: Events data
            
        Returns:
            Report summary dictionary
        """
        system_prompt = """You are a technical report writer creating CO2 emission reports for IT infrastructure.
Create a comprehensive, professional report summarizing energy consumption and CO2 emissions.
Respond with a JSON object containing 'summary', 'key_findings', 'recommendations', and 'details' fields."""
        
        prompt = f"""Create a comprehensive CO2 emission report summary based on this data:

Energy Consumption Data:
{json.dumps(energy_data, indent=2)}

Carbon Footprint Data:
{json.dumps(carbon_data, indent=2)}

Generate a professional report with:
- 'summary': Executive summary paragraph
- 'key_findings': List of key findings
- 'recommendations': List of recommendations for reducing emissions
- 'details': Detailed breakdown by resource category

Respond as JSON."""

        response = self._call_llm(prompt, system_prompt)
        
        try:
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            return result
        except (json.JSONDecodeError, ValueError):
            # Fallback report
            return {
                'summary': f"Total CO2 emissions: {carbon_data.get('total_co2_kg', 0)} kg",
                'key_findings': ['Energy consumption calculated based on resource types and events'],
                'recommendations': ['Monitor resource usage', 'Optimize energy consumption'],
                'details': carbon_data.get('co2_by_resource_type', {})
            }
    
    def generate_co2_reduction_advice(self, energy_data: Dict[str, Any], carbon_data: Dict[str, Any],
                                     resource_details: List[Dict[str, Any]]) -> List[str]:
        """
        Generate 3 specific advices to reduce CO2 emissions based on actual resources.
        
        Args:
            energy_data: Energy consumption data
            carbon_data: Carbon footprint data
            resource_details: List of per-resource details with CO2, energy, failure probability
            
        Returns:
            List of 3 advice strings
        """
        system_prompt = """You are an IT infrastructure sustainability expert providing actionable advice 
to reduce CO2 emissions. Analyze the actual resource inventory, energy consumption patterns, and CO2 emissions 
to provide 3 specific, practical, and actionable recommendations. Focus on the actual resources present 
(servers, workstations, automates, internet gateway) and their current consumption patterns."""
        
        # Prepare resource summary for LLM
        resource_summary = {
            'total_co2_kg': carbon_data.get('total_co2_kg', 0),
            'total_energy_kwh': energy_data.get('total_energy_kwh', 0),
            'co2_by_resource_type': carbon_data.get('co2_by_resource_type', {}),
            'production_inventory': energy_data.get('production_inventory', {}),
            'resources_with_high_co2': [],
            'resources_with_failures': []
        }
        
        # Find resources with highest CO2 emissions
        sorted_resources = sorted(resource_details, key=lambda x: x['co2_kg'], reverse=True)
        resource_summary['resources_with_high_co2'] = [
            {
                'id': r['id'],
                'type': r['type'],
                'co2_kg': r['co2_kg'],
                'energy_kwh': r['energy_kwh']
            }
            for r in sorted_resources[:5]  # Top 5 highest CO2 emitters
        ]
        
        # Find resources with high failure probability
        resources_with_failures = [r for r in resource_details if r['failure_probability'] > 0.3]
        resource_summary['resources_with_failures'] = [
            {
                'id': r['id'],
                'type': r['type'],
                'failure_probability': r['failure_probability'],
                'co2_kg': r['co2_kg']
            }
            for r in sorted(resources_with_failures, key=lambda x: x['failure_probability'], reverse=True)[:5]
        ]
        
        prompt = f"""Based on the following IT infrastructure CO2 emission analysis, provide exactly 3 specific, 
actionable recommendations to reduce CO2 emissions. Focus on the actual resources and their current state.

Current Infrastructure:
- Total CO2 Emissions: {resource_summary['total_co2_kg']:.2f} kg
- Total Energy Consumption: {resource_summary['total_energy_kwh']:.2f} kWh
- Production Inventory: {json.dumps(resource_summary['production_inventory'], indent=2)}
- CO2 by Resource Type: {json.dumps(resource_summary['co2_by_resource_type'], indent=2)}

Top CO2 Emitting Resources:
{json.dumps(resource_summary['resources_with_high_co2'], indent=2)}

Resources with High Failure Probability:
{json.dumps(resource_summary['resources_with_failures'], indent=2)}

Provide exactly 3 specific, actionable recommendations. Each recommendation should:
1. Be specific to the actual resources and their current consumption
2. Be practical and implementable
3. Include potential CO2 reduction impact if possible
4. Consider the resource types (servers, workstations, automates, internet gateway) and their usage patterns

Respond with a JSON object containing a 'advices' field which is an array of exactly 3 strings, each being one recommendation."""

        response = self._call_llm(prompt, system_prompt)
        
        try:
            response = response.strip()
            if response.startswith('```json'):
                response = response[7:]
            if response.startswith('```'):
                response = response[3:]
            if response.endswith('```'):
                response = response[:-3]
            response = response.strip()
            
            result = json.loads(response)
            advices = result.get('advices', [])
            
            # Ensure we have exactly 3 advices
            if len(advices) >= 3:
                return advices[:3]
            elif len(advices) > 0:
                # Pad with generic advice if needed
                while len(advices) < 3:
                    advices.append("Monitor and optimize energy consumption patterns.")
                return advices
            else:
                # Fallback advices
                return self._fallback_co2_advice(resource_summary)
        except (json.JSONDecodeError, ValueError, KeyError):
            # Fallback advices
            return self._fallback_co2_advice(resource_summary)
    
    def _fallback_co2_advice(self, resource_summary: Dict[str, Any]) -> List[str]:
        """Generate fallback CO2 reduction advice."""
        advices = []
        
        # Analyze which resource type has highest CO2
        co2_by_type = resource_summary.get('co2_by_resource_type', {})
        if co2_by_type:
            max_type = max(co2_by_type.items(), key=lambda x: x[1])
            if max_type[0] == 'server':
                advices.append("Consider server virtualization and consolidation to reduce the number of physical servers, potentially reducing CO2 emissions by 20-30%.")
            elif max_type[0] == 'automate':
                advices.append("Optimize automate scheduling to reduce unnecessary runtime during non-production hours, reducing energy consumption.")
            elif max_type[0] == 'workstation':
                advices.append("Implement workstation power management policies to automatically shut down or hibernate workstations during non-business hours.")
        else:
            advices.append("Implement power management policies across all IT resources to reduce energy consumption during idle periods.")
        
        # Second advice based on failure probability
        if resource_summary.get('resources_with_failures'):
            advices.append("Address high failure probability resources proactively to prevent unexpected downtime and optimize maintenance schedules, reducing overall energy waste.")
        else:
            advices.append("Regularly monitor and maintain IT resources to ensure optimal energy efficiency and prevent energy waste from degraded performance.")
        
        # Third advice - general optimization
        total_co2 = resource_summary.get('total_co2_kg', 0)
        if total_co2 > 200:
            advices.append("Consider migrating to renewable energy sources or implementing energy-efficient hardware upgrades to significantly reduce carbon footprint.")
        else:
            advices.append("Implement real-time energy monitoring to identify and address energy consumption anomalies and optimize resource utilization.")
        
        return advices[:3]
