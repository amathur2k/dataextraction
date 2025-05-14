# Clinical Trial Data Analysis

This project extracts and analyzes clinical trial data from JSON files using a two-phase approach:
1. **Regex-based Extraction**: Extract structured data from clinical trial JSON files using regex patterns
2. **LLM-based Enhancement**: Process the extracted data using OpenAI GPT-4o to provide deeper analysis, structured categorization, and human-readable summaries

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
  - Generate concise human-readable summaries
  - Analyze and explain outcome measures

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

## Usage

### Process a Single File

```bash
python analyze_trial_data.py -f path/to/trial_data.json -o output_directory
```

### Process Multiple Files in a Directory

```bash
python analyze_trial_data.py -d path/to/data_directory -o output_directory
```

### Skip LLM Enhancement

If you want to extract data without using the OpenAI API for enhancement:

```bash
python analyze_trial_data.py -f path/to/trial_data.json --skip-llm
```

### Use Custom API Key

```bash
python analyze_trial_data.py -f path/to/trial_data.json -k your_openai_api_key
```

You can also set the API key as an environment variable:

```bash
export OPENAI_API_KEY=your_openai_api_key
python analyze_trial_data.py -f path/to/trial_data.json
```

### Additional Options

- `-p, --pattern`: Specify a file pattern when processing a directory (default: `*.json`)
- `-v, --verbose`: Enable verbose logging

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

### 3. `analyze_trial_data.py`

This is the main script that combines the extraction and enhancement steps into a complete pipeline.

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

## License

This project is licensed under the MIT License - see the LICENSE file for details. 