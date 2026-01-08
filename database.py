"""
Database handler for storing events in JSON format.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any, Optional


class Database:
    """Database handler for JSON file storage."""
    
    def __init__(self, database_path: str = "events_database.json"):
        """
        Initialize database.
        
        Args:
            database_path: Path to JSON database file
        """
        self.database_path = database_path
        self.data = self._load_database()
    
    def _load_database(self) -> Dict[str, Any]:
        """Load database from JSON file."""
        if os.path.exists(self.database_path):
            try:
                with open(self.database_path, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError):
                return {}
        return {}
    
    def save(self):
        """Save database to JSON file."""
        try:
            with open(self.database_path, 'w', encoding='utf-8') as f:
                json.dump(self.data, f, indent=2, ensure_ascii=False)
        except IOError as e:
            print(f"Error saving database: {e}")
    
    def add_event(self, resource_id: str, resource_type: str, event: Dict[str, Any]):
        """
        Add an event to the database.
        
        Args:
            resource_id: Resource identifier
            resource_type: Type of resource
            event: Event data dictionary
        """
        if resource_id not in self.data:
            self.data[resource_id] = {
                'type': resource_type,
                'events': [],
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
        
        # Add timestamp if not present
        if 'stored_at' not in event:
            event['stored_at'] = datetime.now().isoformat()
        
        # Check if event already exists (by event_id)
        event_id = event.get('event_id')
        existing_events = self.data[resource_id]['events']
        
        # Check if event with same ID already exists
        event_exists = any(e.get('event_id') == event_id for e in existing_events)
        
        if not event_exists:
            self.data[resource_id]['events'].append(event)
            self.data[resource_id]['updated_at'] = datetime.now().isoformat()
        else:
            # Update existing event
            for i, e in enumerate(existing_events):
                if e.get('event_id') == event_id:
                    existing_events[i] = event
                    self.data[resource_id]['updated_at'] = datetime.now().isoformat()
                    break
    
    def get_all_events(self) -> Dict[str, Any]:
        """
        Get all events from database.
        
        Returns:
            Dictionary with all events
        """
        return self.data.copy()
    
    def get_resource_events(self, resource_id: str) -> Optional[Dict[str, Any]]:
        """
        Get events for a specific resource.
        
        Args:
            resource_id: Resource identifier
            
        Returns:
            Resource data or None if not found
        """
        return self.data.get(resource_id)
    
    def get_events_by_type(self, resource_type: str) -> Dict[str, Any]:
        """
        Get all events for a specific resource type.
        
        Args:
            resource_type: Type of resource
            
        Returns:
            Dictionary with events filtered by type
        """
        filtered = {}
        for resource_id, resource_data in self.data.items():
            if resource_data.get('type') == resource_type:
                filtered[resource_id] = resource_data
        return filtered
