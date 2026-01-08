"""
Main application for IT resource event processing and CO2 emission reporting.
"""

import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any

from llm_service import LLMService
from energy_calculator import EnergyCalculator
from database import Database
from report_generator import ReportGenerator


class ResourceEventProcessor:
    """Main processor for resource events."""
    
    def __init__(self, openrouter_api_key: str, database_path: str = "events_database.json"):
        """
        Initialize the processor.
        
        Args:
            openrouter_api_key: API key for OpenRouter
            database_path: Path to the JSON database file
        """
        self.llm_service = LLMService(openrouter_api_key)
        self.energy_calculator = EnergyCalculator()
        self.database = Database(database_path)
        self.report_generator = ReportGenerator(self.llm_service, self.energy_calculator)
    
    def process_input_file(self, input_file: str):
        """
        Process input JSON file with resource events.
        
        Args:
            input_file: Path to input JSON file
        """
        print(f"Loading input file: {input_file}")
        with open(input_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        print(f"Processing {len(data)} resources...")
        
        # Process each resource
        for resource_id, resource_data in data.items():
            resource_type = resource_data.get('type')
            events = resource_data.get('events', [])
            
            print(f"\nProcessing {resource_id} (type: {resource_type}) with {len(events)} events")
            
            # Analyze each event with LLM for failure prediction
            for event in events:
                print(f"  Analyzing event {event.get('event_id')}...")
                failure_probability = self.llm_service.predict_failure_probability(
                    resource_type, event
                )
                event['failure_probability'] = failure_probability
                
                # Store event in database
                self.database.add_event(resource_id, resource_type, event)
        
        # Save database
        self.database.save()
        print("\nEvents stored in database.")
    
    def generate_co2_report(self, output_file: str = "CO2_emission_report.json"):
        """
        Generate CO2 emission report for the last week.
        
        Args:
            output_file: Path to output JSON report file
        """
        print("\nGenerating CO2 emission report for the last week...")
        
        # Get events from database
        all_events = self.database.get_all_events()
        
        # Calculate end date (now) and start date (7 days ago)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        # Filter events from last week
        week_events = self._filter_events_by_date_range(all_events, start_date, end_date)
        
        # Calculate energy consumption and carbon footprint
        print("Calculating energy consumption and carbon footprint...")
        energy_data = self.energy_calculator.calculate_weekly_energy(week_events)
        
        # Use LLM to evaluate carbon footprint
        print("Evaluating carbon footprint with LLM...")
        carbon_footprint = self.llm_service.evaluate_carbon_footprint(energy_data, week_events)
        
        # Generate report with LLM
        print("Generating summary report with LLM...")
        report = self.report_generator.generate_report(
            energy_data, carbon_footprint, week_events
        )
        
        # Generate textual report
        print("Generating textual report...")
        textual_report = self.report_generator.generate_textual_report(
            energy_data, carbon_footprint, week_events, self.database
        )
        
        # Save JSON report
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)
        
        # Save textual report
        textual_output_file = output_file.replace('.json', '_textual.txt')
        with open(textual_output_file, 'w', encoding='utf-8') as f:
            f.write(textual_report)
        
        print(f"\nCO2 emission report (JSON) saved to: {output_file}")
        print(f"CO2 emission report (Textual) saved to: {textual_output_file}")
        
        # Also add textual report to JSON
        report['textual_report'] = textual_report
        
        return report
    
    def _filter_events_by_date_range(self, events: Dict, start_date: datetime, end_date: datetime) -> Dict:
        """Filter events by date range."""
        filtered = {}
        
        for resource_id, resource_data in events.items():
            filtered_events = []
            for event in resource_data.get('events', []):
                try:
                    timestamp_str = event.get('timestamp_start_event', '')
                    if not timestamp_str:
                        continue
                    
                    # Handle ISO format with or without timezone
                    if timestamp_str.endswith('Z'):
                        timestamp_str = timestamp_str[:-1] + '+00:00'
                    
                    event_start = datetime.fromisoformat(timestamp_str.replace('Z', '+00:00'))
                    # Remove timezone for comparison if present
                    if event_start.tzinfo:
                        event_start = event_start.replace(tzinfo=None)
                    
                    if start_date <= event_start <= end_date:
                        filtered_events.append(event)
                except (ValueError, TypeError) as e:
                    # Skip events with invalid timestamps
                    continue
            
            if filtered_events:
                filtered[resource_id] = {
                    'type': resource_data.get('type'),
                    'events': filtered_events
                }
        
        return filtered


def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description='Process IT resource events and generate CO2 reports')
    parser.add_argument('input_file', help='Path to input JSON file with resource events')
    parser.add_argument('--api-key', help='OpenRouter API key (or set OPENROUTER_API_KEY env var)')
    parser.add_argument('--database', default='events_database.json', help='Path to database file')
    parser.add_argument('--output', default='CO2_emission_report.json', help='Path to output report file')
    
    args = parser.parse_args()
    
    # Get API key
    api_key = args.api_key or os.getenv('OPENROUTER_API_KEY')
    if not api_key:
        print("Error: OpenRouter API key is required. Set OPENROUTER_API_KEY environment variable or use --api-key")
        return
    
    # Initialize processor
    processor = ResourceEventProcessor(api_key, args.database)
    
    # Process input file
    if not os.path.exists(args.input_file):
        print(f"Error: Input file not found: {args.input_file}")
        return
    
    processor.process_input_file(args.input_file)
    
    # Generate CO2 report
    processor.generate_co2_report(args.output)


if __name__ == '__main__':
    main()
