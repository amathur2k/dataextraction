# Clinical Trial Data Analysis

This project extracts and analyzes clinical trial data from JSON files using a two-phase approach:
1. **Regex-based Extraction**: Extract structured data from clinical trial JSON files using regex patterns
2. **LLM-based Analysis**: Process the extracted data using OpenAI GPT-4o to provide comprehensive structured analysis with specific fields
3. **Database Storage**: Store comprehensive analysis results in PostgreSQL database with 88-field schema

## Features

- **Multiple Input Sources**:
  - Process local JSON files (single file or directory)
  - Download and process trials directly from ClinicalTrials.gov API using NCT ID

- **Comprehensive Data Storage**:
  - PostgreSQL database integration with 88-field comprehensive schema
  - Automatic database schema creation
  - UPSERT operations for conflict resolution
  - Full-text search capabilities with GIN indexes

- Extract key clinical trial information such as:-
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
   pip install openai requests psycopg2-binary
   ```
3. Set your OpenAI API key:
   ```
   export OPENAI_API_KEY=your_api_key_here
   ```

## Database Setup (Optional)

If you want to use the database functionality to store analysis results:

### 1. Install PostgreSQL

Make sure you have PostgreSQL installed and running on your system.

### 2. Create Database and Schema

Use the provided script to create the database and comprehensive schema:

```bash
python create_db_schema.py
```

This script will:
- Create a database named `ctdb` (or specify custom name)
- Create a comprehensive table with 88 fields covering all aspects of clinical trials
- Set up 30+ performance indexes including GIN indexes for JSONB fields
- Configure full-text search capabilities
- Set up automatic triggers for search vector updates

### 3. Database Configuration

Default database configuration:
- **Host**: localhost
- **Port**: 5432
- **Database**: ctdb
- **User**: postgres
- **Password**: admin
- **Table**: myclinicaltrials

You can customize these settings using command line arguments (see Usage section).

## Usage

### Process a Single File

```bash
python run_trial_analysis.py -f path/to/trial.json -o output_directory
```

### Process Multiple Files in a Directory

```bash
python run_trial_analysis.py -d path/to/directory -o output_directory
```

### Process by NCT ID (Download from ClinicalTrials.gov)

Download and process a clinical trial directly from the ClinicalTrials.gov API:

```bash
python run_trial_analysis.py -n NCT00001372 -o output_directory
```

The trial data will be downloaded to the debug directory and then processed through the complete pipeline.

### Store Results in Database

To automatically store analysis results in PostgreSQL database:

```bash
python run_trial_analysis.py -n NCT00001372 -o output_directory --push-to-db --db-name ctdb
```

With custom database configuration:

```bash
python run_trial_analysis.py -n NCT00001372 -o output_directory \
  --push-to-db \
  --db-host localhost \
  --db-port 5432 \
  --db-name ctdb \
  --db-user postgres \
  --db-password admin \
  --db-table myclinicaltrials
```

### Extraction Only (Skip LLM Analysis)

If you want to extract data without using the OpenAI API for analysis:

```bash
python run_trial_analysis.py -f path/to/trial.json --extraction-only
```

Or with NCT ID:

```bash
python run_trial_analysis.py -n NCT00001372 -o output_directory --extraction-only
```

**Note**: Database push is not available in extraction-only mode as it requires LLM analysis results.

### Use Custom API Key

```bash
python run_trial_analysis.py -f path/to/trial.json -k your_openai_api_key
```

You can also set the API key as an environment variable:

```bash
export OPENAI_API_KEY=your_openai_api_key
python run_trial_analysis.py -f path/to/trial.json
```

### Command Line Options

#### Input Options
- `-f, --file`: Path to a single JSON file to process
- `-d, --directory`: Path to a directory containing JSON files to process
- `-n, --nctid`: NCT ID to download and process from ClinicalTrials.gov API

#### Output Options
- `-o, --output`: Directory to save output files
- `--no-clean`: Do not clean output directory before processing (by default, the output directory is cleaned)

#### Processing Options
- `-k, --api_key`: OpenAI API key (can also be set via OPENAI_API_KEY environment variable)
- `--extraction-only`: Only perform extraction without LLM analysis

#### Database Options
- `--push-to-db`: Push analysis results to PostgreSQL database
- `--db-host`: Database host (default: localhost)
- `--db-port`: Database port (default: 5432)
- `--db-name`: Database name (default: ctdb)
- `--db-user`: Database user (default: postgres)
- `--db-password`: Database password (default: admin)
- `--db-table`: Database table name (default: myclinicaltrials)

## Components

### 1. `trial_data_extractor.py`

This module extracts structured data from clinical trial JSON files using regex patterns and basic parsing.

### 2. `trial_data_analyzer.py`

This module analyzes the extracted clinical trial data using OpenAI's GPT-4o API to provide comprehensive structured analysis with specific fields.

### 3. `run_trial_analysis.py`

This is the main entry point that orchestrates the entire pipeline, connecting the extractor and analyzer modules.

### 4. `db_handler.py`

This module provides PostgreSQL database integration with comprehensive schema support:
- Connection management with context manager support
- Data insertion with UPSERT operations
- Comprehensive 88-field schema handling
- Full-text search support

### 5. `create_db_schema.py`

Standalone script to create the PostgreSQL database and comprehensive schema with:
- 88 fields covering all aspects of clinical trials
- 30+ performance indexes including GIN indexes for JSONB fields
- Full-text search capabilities
- Automatic triggers for search vector updates

## Database Schema

The database schema includes 88 comprehensive fields organized into categories:

### Core Trial Metadata (19 fields)
- NCT ID, status, dates, phase, study type
- Enrollment information, sponsors, titles

### Study Design (6 fields)  
- Allocation, intervention model, masking, primary purpose

### Interventions & Mechanisms (10 fields)
- Interventions, drug names, dosages, administration routes
- Mechanisms of action, target pathways, genes, proteins, compounds

### Biomarkers & Study Structure (4 fields)
- Biomarkers, biomarker types, arms/groups, number of arms

### Outcomes (3 fields)
- Primary, secondary, and other outcomes

### Patient Information (15 fields)
- Eligibility criteria (structured), demographics, age limits
- Conditions, disease characteristics, prior treatments

### Operational Aspects (9 fields)
- Locations, countries, facilities, investigators
- Enrollment status, site recruitment status

### IPD & Contacts (8 fields)
- IPD sharing information, contact details

### Documentation (5 fields)
- References, provided documents, oversight information

### Additional Metadata (3 fields)
- Stopping reasons, expanded access information

### Quality Assessment (4 fields)
- Analysis scores, rationale, missing information, recommendations

### Full Data Storage (2 fields)
- Original extracted data, complete analyzed data

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

## Examples

### Complete Pipeline with Database Storage

```bash
# Create database schema (one-time setup)
python create_db_schema.py

# Download, analyze, and store NCT00001372 in database
python run_trial_analysis.py \
  --nctid NCT00001372 \
  --output output \
  --push-to-db \
  --db-name ctdb

# Process local file and store in database
python run_trial_analysis.py \
  --file trial_data.json \
  --output output \
  --push-to-db \
  --db-name ctdb

# Process multiple files and store all in database
python run_trial_analysis.py \
  --directory trial_data_folder \
  --output output \
  --push-to-db \
  --db-name ctdb
```

### Extraction Only (No Database)

```bash
# Quick extraction without LLM analysis or database
python run_trial_analysis.py \
  --nctid NCT00001372 \
  --output output \
  --extraction-only
```

## License

This project is licensed under the MIT License - see the LICENSE file for details. 