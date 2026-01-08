"""
Example usage script for the IT Resource Event Processor.
This script demonstrates how to use the application programmatically.
"""

import os
from main import ResourceEventProcessor

def main():
    """Example usage."""
    # Get API key from environment variable
    api_key = os.getenv('OPENROUTER_API_KEY')
    
    if not api_key:
        print("Please set OPENROUTER_API_KEY environment variable")
        print("Example: export OPENROUTER_API_KEY='your-api-key'")
        return
    
    # Initialize processor
    processor = ResourceEventProcessor(
        openrouter_api_key=api_key,
        database_path="events_database.json"
    )
    
    # Process input file
    input_file = "sample_input.json"
    if os.path.exists(input_file):
        processor.process_input_file(input_file)
        
        # Generate CO2 report
        report = processor.generate_co2_report("CO2_emission_report.json")
        
        print("\n" + "="*50)
        print("Report Summary:")
        print("="*50)
        print(f"Total CO2 Emissions: {report.get('total_co2_emissions_kg', 0)} kg")
        print(f"Total Energy Consumption: {report.get('energy_consumption', {}).get('total_energy_kwh', 0)} kWh")
        print("\nCO2 by Resource Category:")
        for category, co2 in report.get('co2_emissions_by_resource_category', {}).items():
            print(f"  {category}: {co2} kg")
    else:
        print(f"Input file not found: {input_file}")
        print("Please create a sample_input.json file or use your own input file")

if __name__ == '__main__':
    main()
