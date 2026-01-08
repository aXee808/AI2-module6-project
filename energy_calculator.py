"""
Energy consumption calculator for IT resources.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Any
import math


class EnergyCalculator:
    """Calculator for energy consumption of IT resources."""
    
    # Power consumption in watts per hour
    POWER_CONSUMPTION = {
        'server': {
            'production': 100,  # 8am-8pm
            'night': 70  # 8pm-8am
        },
        'workstation': {
            'production': 60,  # 8am-8pm
            'night': 0  # Off at night
        },
        'automate': {
            'production': 300,  # 8am-8pm
            'night': 0  # Off at night
        },
        'internet_gateway': {
            'always': 50  # Always on
        }
    }
    
    PRODUCTION_START_HOUR = 8
    PRODUCTION_END_HOUR = 20
    
    # Production inventory
    PRODUCTION_INVENTORY = {
        'server': 10,
        'workstation': 20,
        'automate': 5,
        'internet_gateway': 1
    }
    
    def __init__(self):
        """Initialize energy calculator."""
        pass
    
    def calculate_weekly_energy(self, events_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate energy consumption for the last week considering events.
        Accounts for all resources in production inventory.
        
        Args:
            events_data: Dictionary with resource events
            
        Returns:
            Dictionary with energy consumption data
        """
        # Calculate date range (last 7 days)
        end_date = datetime.now()
        start_date = end_date - timedelta(days=7)
        
        total_energy_wh = 0
        energy_by_type = {
            'server': 0,
            'workstation': 0,
            'automate': 0,
            'internet_gateway': 0
        }
        
        # Track resources and their states
        resources = {}
        
        # Create a map of resource IDs to their data
        resource_map = {}
        for resource_id, resource_data in events_data.items():
            resource_type = resource_data.get('type')
            resource_map[resource_id] = resource_data
        
        # Calculate energy for ALL resources in production
        for resource_type, count in self.PRODUCTION_INVENTORY.items():
            # Calculate base energy per resource of this type
            base_energy_per_resource = self._calculate_base_energy(resource_type, start_date, end_date)
            
            # Calculate total base energy for all resources of this type
            total_base_energy = base_energy_per_resource * count
            
            # Adjust for events from resources of this type
            total_adjusted_energy = total_base_energy
            resources_with_events = 0
            
            for resource_id, resource_data in events_data.items():
                if resource_data.get('type') == resource_type:
                    resource_events = resource_data.get('events', [])
                    # Adjust energy for this specific resource
                    adjusted_energy = self._adjust_energy_for_events(
                        base_energy_per_resource, resource_type, resource_events, start_date, end_date
                    )
                    
                    # Calculate difference from base
                    energy_delta = adjusted_energy - base_energy_per_resource
                    total_adjusted_energy += energy_delta
                    
                    resources[resource_id] = {
                        'type': resource_type,
                        'base_energy_wh': base_energy_per_resource,
                        'adjusted_energy_wh': adjusted_energy,
                        'events_count': len(resource_events)
                    }
                    resources_with_events += 1
            
            # For resources without events, use base energy
            resources_without_events = count - resources_with_events
            if resources_without_events > 0:
                # Add base energy for resources without events
                total_adjusted_energy += base_energy_per_resource * resources_without_events
            
            energy_by_type[resource_type] = total_adjusted_energy
            total_energy_wh += total_adjusted_energy
        
        return {
            'total_energy_wh': round(total_energy_wh, 2),
            'total_energy_kwh': round(total_energy_wh / 1000.0, 2),
            'energy_by_type': {k: round(v, 2) for k, v in energy_by_type.items()},
            'energy_by_resource': resources,
            'production_inventory': self.PRODUCTION_INVENTORY.copy(),
            'period': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': 7
            }
        }
    
    def _calculate_base_energy(self, resource_type: str, start_date: datetime, end_date: datetime) -> float:
        """
        Calculate base energy consumption for a resource type over a period.
        
        Args:
            resource_type: Type of resource
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            Energy consumption in watt-hours
        """
        if resource_type == 'internet_gateway':
            # Always on: 50W * hours
            hours = (end_date - start_date).total_seconds() / 3600
            return self.POWER_CONSUMPTION['internet_gateway']['always'] * hours
        
        # For other resources, calculate production vs night time
        total_hours = (end_date - start_date).total_seconds() / 3600
        energy = 0
        
        current = start_date
        while current < end_date:
            hour = current.hour
            
            # Determine if production or night time
            if self.PRODUCTION_START_HOUR <= hour < self.PRODUCTION_END_HOUR:
                # Production time
                power = self.POWER_CONSUMPTION[resource_type]['production']
            else:
                # Night time
                power = self.POWER_CONSUMPTION[resource_type]['night']
            
            # Calculate energy for this hour (or partial hour)
            next_hour = (current.replace(minute=0, second=0, microsecond=0) + timedelta(hours=1))
            if next_hour > end_date:
                next_hour = end_date
            
            hours = (next_hour - current).total_seconds() / 3600
            energy += power * hours
            
            current = next_hour
        
        return energy
    
    def _adjust_energy_for_events(self, base_energy: float, resource_type: str, 
                                   events: List[Dict], start_date: datetime, end_date: datetime) -> float:
        """
        Adjust energy consumption based on events.
        
        Args:
            base_energy: Base energy consumption
            resource_type: Type of resource
            events: List of events
            start_date: Start datetime
            end_date: End datetime
            
        Returns:
            Adjusted energy consumption in watt-hours
        """
        adjusted_energy = base_energy
        
        for event in events:
            event_type = event.get('event_type', '')
            duration_str = event.get('duration_event', '0')
            
            try:
                duration_seconds = int(float(duration_str))
            except (ValueError, TypeError):
                continue
            
            duration_hours = duration_seconds / 3600.0
            
            # Get event timestamps
            try:
                timestamp_start_str = event.get('timestamp_start_event', '')
                timestamp_end_str = event.get('timestamp_end_event', '')
                
                if not timestamp_start_str:
                    continue
                
                # Handle ISO format with or without timezone
                if timestamp_start_str.endswith('Z'):
                    timestamp_start_str = timestamp_start_str[:-1] + '+00:00'
                event_start = datetime.fromisoformat(timestamp_start_str.replace('Z', '+00:00'))
                
                # Remove timezone for comparison if present
                if event_start.tzinfo:
                    event_start = event_start.replace(tzinfo=None)
                
                if timestamp_end_str:
                    if timestamp_end_str.endswith('Z'):
                        timestamp_end_str = timestamp_end_str[:-1] + '+00:00'
                    event_end = datetime.fromisoformat(timestamp_end_str.replace('Z', '+00:00'))
                    if event_end.tzinfo:
                        event_end = event_end.replace(tzinfo=None)
                else:
                    event_end = event_start
            except (ValueError, TypeError):
                continue
            
            # Only consider events within the period
            if event_start < start_date or event_start > end_date:
                continue
            
            # Calculate power consumption during event
            if resource_type == 'internet_gateway':
                power_during_event = self.POWER_CONSUMPTION['internet_gateway']['always']
            else:
                # Determine if event occurred during production or night time
                hour = event_start.hour
                if self.PRODUCTION_START_HOUR <= hour < self.PRODUCTION_END_HOUR:
                    power_during_event = self.POWER_CONSUMPTION[resource_type]['production']
                else:
                    power_during_event = self.POWER_CONSUMPTION[resource_type]['night']
            
            # Adjust energy based on event type
            if 'maintenance_stop' in event_type or 'failure' in event_type:
                # Resource is stopped, no energy consumption during event
                energy_saved = power_during_event * duration_hours
                adjusted_energy -= energy_saved
            elif event_type == 'cpu_overflow' or event_type == 'cpu_overload':
                # CPU overload may increase energy consumption by 20-30%
                energy_increase = power_during_event * duration_hours * 0.25
                adjusted_energy += energy_increase
            elif 'update' in event_type:
                # Updates may slightly increase energy consumption
                energy_increase = power_during_event * duration_hours * 0.1
                adjusted_energy += energy_increase
        
        return max(0, adjusted_energy)  # Energy cannot be negative
