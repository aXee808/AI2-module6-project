"""
Report generator for CO2 emissions.
"""

from datetime import datetime, timedelta
from typing import Dict, Any, List


class ReportGenerator:
    """Generator for CO2 emission reports."""
    
    def __init__(self, llm_service, energy_calculator):
        """
        Initialize report generator.
        
        Args:
            llm_service: LLMService instance
            energy_calculator: EnergyCalculator instance
        """
        self.llm_service = llm_service
        self.energy_calculator = energy_calculator
    
    def generate_report(self, energy_data: Dict[str, Any], carbon_data: Dict[str, Any], 
                       events: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate comprehensive CO2 emission report.
        
        Args:
            energy_data: Energy consumption data
            carbon_data: Carbon footprint data
            events: Events data
            
        Returns:
            Complete report dictionary
        """
        # Generate summary using LLM
        llm_summary = self.llm_service.generate_report_summary(energy_data, carbon_data, events)
        
        # Count resources by type
        resource_counts = {
            'server': 0,
            'workstation': 0,
            'automate': 0,
            'internet_gateway': 0
        }
        
        for resource_id, resource_data in events.items():
            resource_type = resource_data.get('type')
            if resource_type in resource_counts:
                resource_counts[resource_type] += 1
        
        # Build comprehensive report
        report = {
            'report_metadata': {
                'generated_at': datetime.now().isoformat(),
                'report_period': energy_data.get('period', {}),
                'report_type': 'CO2 Emission Report'
            },
            'executive_summary': llm_summary.get('summary', ''),
            'total_co2_emissions_kg': carbon_data.get('total_co2_kg', 0),
            'co2_emissions_by_resource_category': carbon_data.get('co2_by_resource_type', {}),
            'energy_consumption': {
                'total_energy_kwh': energy_data.get('total_energy_kwh', 0),
                'total_energy_wh': energy_data.get('total_energy_wh', 0),
                'energy_by_resource_type': energy_data.get('energy_by_type', {})
            },
            'resource_inventory': resource_counts,
            'key_findings': llm_summary.get('key_findings', []),
            'recommendations': llm_summary.get('recommendations', []),
            'detailed_breakdown': {
                'by_resource_type': self._generate_type_breakdown(
                    energy_data, carbon_data, events
                ),
                'methodology': carbon_data.get('methodology', 'Standard CO2 calculation')
            },
            'additional_details': llm_summary.get('details', {})
        }
        
        return report
    
    def _generate_type_breakdown(self, energy_data: Dict[str, Any], carbon_data: Dict[str, Any],
                                 events: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate detailed breakdown by resource type.
        
        Args:
            energy_data: Energy consumption data
            carbon_data: Carbon footprint data
            events: Events data
            
        Returns:
            Breakdown dictionary
        """
        breakdown = {}
        
        co2_by_type = carbon_data.get('co2_by_resource_type', {})
        energy_by_type = energy_data.get('energy_by_type', {})
        energy_by_resource = energy_data.get('energy_by_resource', {})
        
        for resource_type in ['server', 'workstation', 'automate', 'internet_gateway']:
            # Count resources of this type
            count = sum(1 for r in events.values() if r.get('type') == resource_type)
            
            # Get resources of this type
            resources = {
                rid: rdata for rid, rdata in energy_by_resource.items()
                if rdata.get('type') == resource_type
            }
            
            breakdown[resource_type] = {
                'resource_count': count,
                'total_co2_kg': co2_by_type.get(resource_type, 0),
                'total_energy_kwh': round(energy_by_type.get(resource_type, 0) / 1000.0, 2),
                'total_energy_wh': energy_by_type.get(resource_type, 0),
                'average_co2_per_resource_kg': round(
                    co2_by_type.get(resource_type, 0) / max(count, 1), 2
                ),
                'resources': resources
            }
        
        return breakdown
    
    def generate_textual_report(self, energy_data: Dict[str, Any], carbon_data: Dict[str, Any],
                                events: Dict[str, Any], database: Any) -> str:
        """
        Generate textual CO2 emission report with per-resource details.
        
        Args:
            energy_data: Energy consumption data
            carbon_data: Carbon footprint data
            events: Events data
            database: Database instance to get failure probabilities
            
        Returns:
            Textual report string
        """
        # Get all resources from database
        all_resources = database.get_all_events()
        
        # Calculate CO2 per resource
        co2_per_kwh = 0.5  # kg CO2 per kWh
        production_inventory = energy_data.get('production_inventory', {})
        energy_by_resource = energy_data.get('energy_by_resource', {})
        
        # Build per-resource data
        resource_details = []
        
        # Process resources with events
        for resource_id, resource_data in all_resources.items():
            resource_type = resource_data.get('type')
            resource_events = resource_data.get('events', [])
            
            # Get energy consumption for this resource
            if resource_id in energy_by_resource:
                energy_wh = energy_by_resource[resource_id].get('adjusted_energy_wh', 0)
            else:
                # Calculate base energy if not in events
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                base_energy = self.energy_calculator._calculate_base_energy(
                    resource_type, start_date, end_date
                )
                energy_wh = base_energy
            
            energy_kwh = energy_wh / 1000.0
            co2_kg = energy_kwh * co2_per_kwh
            
            # Calculate average failure probability from events
            if resource_events:
                failure_probs = [e.get('failure_probability', 0) for e in resource_events if 'failure_probability' in e]
                avg_failure_prob = sum(failure_probs) / len(failure_probs) if failure_probs else 0.0
            else:
                avg_failure_prob = 0.0
            
            resource_details.append({
                'id': resource_id,
                'type': resource_type,
                'co2_kg': co2_kg,
                'energy_kwh': energy_kwh,
                'failure_probability': avg_failure_prob,
                'events_count': len(resource_events)
            })
        
        # Add resources without events (from production inventory)
        # Track existing resource IDs to avoid duplicates
        existing_ids = {r['id'] for r in resource_details}
        
        for resource_type, count in production_inventory.items():
            # Count how many of this type we have with events
            resources_with_events = sum(1 for r in all_resources.values() if r.get('type') == resource_type)
            resources_without_events = count - resources_with_events
            
            if resources_without_events > 0:
                # Calculate base energy for resources without events
                end_date = datetime.now()
                start_date = end_date - timedelta(days=7)
                base_energy = self.energy_calculator._calculate_base_energy(
                    resource_type, start_date, end_date
                )
                energy_kwh = (base_energy / 1000.0)
                co2_kg = energy_kwh * co2_per_kwh
                
                # Add entries for each resource without events
                counter = 1
                for i in range(resources_without_events):
                    # Generate unique ID
                    while True:
                        resource_id = f"{resource_type}_{counter}"
                        if resource_id not in existing_ids:
                            existing_ids.add(resource_id)
                            break
                        counter += 1
                    
                    resource_details.append({
                        'id': resource_id,
                        'type': resource_type,
                        'co2_kg': co2_kg,
                        'energy_kwh': energy_kwh,
                        'failure_probability': 0.0,
                        'events_count': 0
                    })
                    counter += 1
        
        # Sort by resource type, then by CO2
        resource_details.sort(key=lambda x: (x['type'], -x['co2_kg']))
        
        # Generate textual report
        report_lines = []
        report_lines.append("=" * 80)
        report_lines.append("CO2 EMISSION REPORT - WEEKLY SUMMARY")
        report_lines.append("=" * 80)
        report_lines.append("")
        
        # Report metadata
        period = energy_data.get('period', {})
        report_lines.append(f"Report Period: {period.get('start', 'N/A')} to {period.get('end', 'N/A')}")
        report_lines.append(f"Generated At: {datetime.now().isoformat()}")
        report_lines.append("")
        
        # Executive summary
        report_lines.append("-" * 80)
        report_lines.append("EXECUTIVE SUMMARY")
        report_lines.append("-" * 80)
        total_co2 = carbon_data.get('total_co2_kg', 0)
        total_energy = energy_data.get('total_energy_kwh', 0)
        report_lines.append(f"Total CO2 Emissions: {total_co2:.2f} kg")
        report_lines.append(f"Total Energy Consumption: {total_energy:.2f} kWh")
        report_lines.append("")
        
        # CO2 by resource category
        report_lines.append("-" * 80)
        report_lines.append("CO2 EMISSIONS BY RESOURCE CATEGORY")
        report_lines.append("-" * 80)
        co2_by_type = carbon_data.get('co2_by_resource_type', {})
        for resource_type in ['server', 'workstation', 'automate', 'internet_gateway']:
            co2 = co2_by_type.get(resource_type, 0)
            count = production_inventory.get(resource_type, 0)
            report_lines.append(f"{resource_type.capitalize()}: {co2:.2f} kg CO2 ({count} resources)")
        report_lines.append("")
        
        # Per-resource details
        report_lines.append("-" * 80)
        report_lines.append("CO2 EMISSIONS AND FAILURE PROBABILITY PER RESOURCE")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        # Group by resource type
        current_type = None
        for resource in resource_details:
            if resource['type'] != current_type:
                if current_type is not None:
                    report_lines.append("")
                current_type = resource['type']
                report_lines.append(f"{current_type.upper()} Resources:")
                report_lines.append("-" * 40)
            
            report_lines.append(
                f"  {resource['id']:30s} | "
                f"CO2: {resource['co2_kg']:8.2f} kg | "
                f"Energy: {resource['energy_kwh']:8.2f} kWh | "
                f"Failure Prob: {resource['failure_probability']:5.2%} | "
                f"Events: {resource['events_count']}"
            )
        
        report_lines.append("")
        
        # Generate CO2 reduction advice using LLM
        report_lines.append("-" * 80)
        report_lines.append("RECOMMENDATIONS TO REDUCE CO2 EMISSIONS")
        report_lines.append("-" * 80)
        report_lines.append("")
        
        try:
            advices = self.llm_service.generate_co2_reduction_advice(
                energy_data, carbon_data, resource_details
            )
            
            for i, advice in enumerate(advices, 1):
                report_lines.append(f"{i}. {advice}")
                report_lines.append("")
        except Exception as e:
            # Fallback if LLM fails
            report_lines.append("1. Implement power management policies to reduce energy consumption during idle periods.")
            report_lines.append("")
            report_lines.append("2. Optimize resource utilization and consider virtualization to reduce physical hardware requirements.")
            report_lines.append("")
            report_lines.append("3. Monitor and maintain IT resources regularly to ensure optimal energy efficiency.")
            report_lines.append("")
        
        report_lines.append("=" * 80)
        
        return "\n".join(report_lines)
