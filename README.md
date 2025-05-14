# Clinical Trial Data Analysis

This project extracts and analyzes clinical trial data from JSON files using a three-phase approach:
1. **Regex-based Extraction**: Extract structured data from clinical trial JSON files using regex patterns
2. **LLM-based Enhancement**: Process the extracted data using OpenAI GPT-4o to provide deeper analysis, structured categorization, and human-readable summaries
3. **Structured Summary Generation**: Create a standardized JSON output with specific fields for consistent data representation

## Features

- Extract key clinical trial information such as:
  - Basic trial details (ID, title, status, phase, etc.)
  - Study design information
  - Eligibility criteria (inclusion and exclusion)
  - Interventions
  - Outcome measures

- LLM-based enhancement:
  - Categorize eligibility criteria by demographics, medical conditions, etc.
  - Extract numerical values and time frames from criteria
  - Normalize drug names and conditions
  - Generate human-readable trial summaries
  - Analyze outcome measures

- Structured summary generation:
  - Core trial metadata (ID, status, dates, phase, etc.)
  - Scientific content (interventions, mechanisms, targets, outcomes)
  - Patient-related information (eligibility, demographics, disease characteristics)
  - Operational aspects (locations, investigators, enrollment status)

## Requirements

- Python 3.7 or higher
- Required Python packages:
  - `openai` (for LLM enhancement)

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install openai
```

3. Set your OpenAI API key:

```bash
export OPENAI_API_KEY=your_api_key_here
```

## Usage

### Process a Single File

```bash
python analyze_trial_data.py -f path/to/trial.json -o output_directory
```

### Process Multiple Files in a Directory

```bash
python analyze_trial_data.py -d path/to/directory -o output_directory
```

### Skip LLM Enhancement

If you want to extract data without using the OpenAI API for enhancement:

```bash
python analyze_trial_data.py -f path/to/trial.json --skip-llm
```

### Skip Structured Summary Generation

If you want to skip the structured summary generation step:

```bash
python analyze_trial_data.py -f path/to/trial.json --skip-summary
```

### Use Custom API Key

```bash
python analyze_trial_data.py -f path/to/trial.json -k your_openai_api_key
```

You can also set the API key as an environment variable:

```bash
export OPENAI_API_KEY=your_openai_api_key
python analyze_trial_data.py -f path/to/trial.json
```

### Additional Options

- `-f, --file`: Path to a single JSON file to process
- `-d, --directory`: Path to a directory containing JSON files to process
- `-o, --output`: Directory to save output files
- `-k, --api_key`: OpenAI API key (can also be set via OPENAI_API_KEY environment variable)
- `--skip-llm`: Skip the LLM enhancement step
- `--skip-summary`: Skip the structured summary generation step

## Components

### 1. `trial_data_extractor.py`

This module extracts structured data from clinical trial JSON files using regex patterns and basic parsing.

You can use it standalone:

```bash
python trial_data_extractor.py path/to/trial_data.json -o extracted_data.json
```

### 2. `llm_enhancer.py`

This module enhances the extracted clinical trial data using OpenAI's GPT-4o API.

You can use it standalone:

```bash
python llm_enhancer.py path/to/extracted_data.json -o enhanced_data.json -k your_openai_api_key
```

### 3. `structured_summary.py`

This module creates a standardized JSON output with specific fields for consistent data representation.

## Output Format

The extraction phase outputs a JSON file with the following structure:

```json
{
  "basic_info": {
    "nct_id": "NCT12345678",
    "brief_title": "Trial Title",
    ...
  },
  "eligibility_criteria": {
    "inclusion_criteria": [...],
    "exclusion_criteria": [...]
  },
  "interventions": [...],
  "outcomes": {
    "primary_outcomes": [...],
    "secondary_outcomes": [...]
  }
}
```

The enhancement phase adds the following to create a comprehensive analysis:

```json
{
  "study_summary": "Human-readable summary of the trial...",
  "enhanced_eligibility": {
    "raw_criteria": {...},
    "enhanced_criteria": {
      "demographics": {...},
      "medical_conditions": {...},
      ...
    }
  },
  "enhanced_outcomes": {...},
  "original_data": {...}
}
```

The structured summary generation step adds the following to create a standardized JSON output:

```json
{
  "core_trial_metadata": {
    "nct_id": "NCT12345678",
    "status": "Recruiting",
    "start_date": "2023-01-01",
    "end_date": "2024-01-01",
    "phase": "Phase 2"
  },
  "scientific_content": {
    "interventions": [...],
    "mechanisms": [...],
    "targets": [...],
    "outcomes": [...]
  },
  "patient_related_information": {
    "eligibility": {...},
    "demographics": {...},
    "disease_characteristics": {...}
  },
  "operational_aspects": {
    "locations": [...],
    "investigators": [...],
    "enrollment_status": "Recruiting"
  }
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 