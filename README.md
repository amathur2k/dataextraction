# Clinical Trial Data Analysis

This project extracts and analyzes clinical trial data from JSON files using a two-phase approach:
1. **Regex-based Extraction**: Extract structured data from clinical trial JSON files using regex patterns
2. **LLM-based Analysis**: Process the extracted data using OpenAI GPT-4o to provide comprehensive structured analysis with specific fields

## Features

- Extract key clinical trial information such as:
  - Basic trial details (ID, title, status, phase, etc.)
  - Study design information
  - Eligibility criteria (inclusion and exclusion)
  - Interventions
  - Outcome measures

- LLM-based comprehensive analysis:
  - Core Trial Metadata (ID, status, dates, phase, etc.)
  - Scientific Content (interventions, mechanisms, targets, outcomes)
  - Patient-Related Information (eligibility, demographics, disease characteristics)
  - Operational Aspects (locations, investigators, enrollment status)

## Installation

1. Clone this repository
2. Install the required dependencies:
   ```
   pip install openai
   ```
3. Set your OpenAI API key:
   ```
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

### Extraction Only (Skip LLM Analysis)

If you want to extract data without using the OpenAI API for analysis:

```bash
python analyze_trial_data.py -f path/to/trial.json --extraction-only
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

### Command Line Options

- `-f, --file`: Path to a single JSON file to process
- `-d, --directory`: Path to a directory containing JSON files to process
- `-o, --output`: Directory to save output files
- `-k, --api_key`: OpenAI API key (can also be set via OPENAI_API_KEY environment variable)
- `--extraction-only`: Only perform extraction without LLM analysis

## Components

### 1. `trial_data_extractor.py`

This module extracts structured data from clinical trial JSON files using regex patterns and basic parsing.

You can use it standalone:

```bash
python trial_data_extractor.py path/to/trial_data.json -o extracted_data.json
```

### 2. `trial_data_analyzer.py`

This module analyzes the extracted clinical trial data using OpenAI's GPT-4o API to provide comprehensive structured analysis with specific fields.

You can use it standalone:

```bash
python trial_data_analyzer.py path/to/extracted_data.json -o analyzed_data.json -k your_openai_api_key
```

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

The analysis phase provides a comprehensive structured output with these specific fields:

```json
{
  "analyzed_data": {
    "core_trial_metadata": {
      "nct_id": "NCT12345678",
      "status": "Recruiting",
      "dates": {
        "registration": "2023-01-01",
        "start": "2023-03-15",
        "completion": "2024-12-31",
        "last_update": "2023-05-20"
      },
      "phase": "Phase 2",
      "study_type": "Interventional",
      "enrollment": {
        "target": 100,
        "actual": 45
      },
      "sponsor_collaborators": {
        "primary_sponsor": "University Medical Center",
        "collaborators": ["Pharmaceutical Company A", "Research Institute B"]
      }
    },
    "scientific_content": {
      "intervention": [...],
      "mechanism_of_action": "...",
      "target_pathway": {...},
      "biomarkers": [...],
      "study_design": {...},
      "arms_groups": [...],
      "outcomes": {...}
    },
    "patient_related_information": {
      "eligibility_criteria": {...},
      "demographics": {...},
      "disease_characteristics": {...},
      "prior_treatments": {...}
    },
    "operational_aspects": {
      "locations": [...],
      "investigators": [...],
      "enrollment_status": {...},
      "ipd_sharing": {...}
    }
  },
  "original_data": {...}
}
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 