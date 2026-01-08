# IT Resource Event Processor and CO2 Emission Reporter

A Python application for processing IT resource events, analyzing them with LLM, and generating CO2 emission reports.

## Features

- **Event Processing**: Processes JSON input files containing IT resource events
- **Failure Prediction**: Uses OpenRouter LLM to predict failure probabilities for each resource based on events
- **Event Storage**: Stores all events in a JSON database file
- **Energy Calculation**: Calculates energy consumption considering resource types, time periods, and events
- **Carbon Footprint**: Evaluates CO2 emissions using LLM analysis
- **Report Generation**: Generates comprehensive CO2 emission reports with LLM-generated summaries

## Resource Types and Power Consumption

- **Servers**: 100W/hour (8am-8pm), 70W/hour (8pm-8am)
- **Workstations**: 60W/hour (8am-8pm), 0W/hour (off at night)
- **Automates**: 300W/hour (8am-8pm), 0W/hour (off at night)
- **Internet Gateway**: 50W/hour (always on)

## Event Types

- cpu_overflow / cpu_overload
- software_update
- operating_system_update
- software_service_failure
- operating_system_failure
- hardware_failure
- hardware_maintenance_stop
- software_maintenance_stop

## Installation

1. Install required dependencies:
```bash
pip install -r requirements.txt
```

2. Set your OpenRouter API key as an environment variable:
```bash
# Windows PowerShell
$env:OPENROUTER_API_KEY="your-api-key-here"

# Windows CMD
set OPENROUTER_API_KEY=your-api-key-here

# Linux/Mac
export OPENROUTER_API_KEY="your-api-key-here"
```

Or get an API key from [OpenRouter](https://openrouter.ai/)

## Usage

### Basic Usage

```bash
python main.py input_events.json
```

### Advanced Usage

```bash
python main.py input_events.json --api-key YOUR_API_KEY --database custom_database.json --output custom_report.json
```

### Command Line Arguments

- `input_file`: Path to input JSON file with resource events (required)
- `--api-key`: OpenRouter API key (optional if OPENROUTER_API_KEY env var is set)
- `--database`: Path to database file (default: `events_database.json`)
- `--output`: Path to output report file (default: `CO2_emission_report.json`)

## Input JSON Format

```json
{
  "ressource_1": {
    "type": "server",
    "events": [
      {
        "event_id": 4987616,
        "timestamp_start_event": "2026-01-07T16:02:08.815888",
        "timestamp_end_event": "2026-01-07T16:02:08.815888",
        "duration_event": "21654654",
        "event_type": "cpu_overflow"
      }
    ]
  }
}
```

## Output

The application generates:

1. **Database File** (`events_database.json`): Stores all processed events with failure probabilities
2. **CO2 Emission Report (JSON)** (`CO2_emission_report.json`): Comprehensive JSON report with:
   - Total CO2 emissions
   - CO2 emissions by resource category
   - Energy consumption breakdown
   - Key findings and recommendations
   - Detailed breakdown by resource type
   - Textual report included in the JSON
3. **CO2 Emission Report (Textual)** (`CO2_emission_report_textual.txt`): Human-readable textual report with:
   - Executive summary
   - CO2 emissions by resource category
   - **CO2 emissions per individual resource**
   - **Failure probability per resource**
   - Energy consumption per resource
   - Event counts per resource
   - **3 LLM-generated recommendations to reduce CO2 emissions** (based on actual resources and their current state)

The system accounts for all resources in production:
- 10 servers
- 20 workstations
- 5 automates
- 1 internet gateway

## Example Output Report Structure

```json
{
  "report_metadata": {
    "generated_at": "2026-01-14T10:00:00",
    "report_period": {
      "start": "2026-01-07T10:00:00",
      "end": "2026-01-14T10:00:00",
      "days": 7
    }
  },
  "total_co2_emissions_kg": 123.45,
  "co2_emissions_by_resource_category": {
    "server": 50.0,
    "workstation": 30.0,
    "automate": 40.0,
    "internet_gateway": 3.45
  },
  "energy_consumption": {
    "total_energy_kwh": 246.9,
    "energy_by_resource_type": {...}
  },
  "key_findings": [...],
  "recommendations": [...]
}
```

## Architecture

- `main.py`: Main application entry point
- `llm_service.py`: OpenRouter LLM API integration
- `energy_calculator.py`: Energy consumption calculations
- `database.py`: JSON database handler
- `report_generator.py`: CO2 emission report generator

## Notes

- The application calculates energy consumption for the last 7 days from the current date
- Events affect energy consumption: maintenance stops reduce consumption, overloads increase it
- Carbon footprint uses standard conversion (approximately 0.5 kg CO2 per kWh)
- LLM is used for intelligent analysis and report generation
