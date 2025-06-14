#!/usr/bin/env python3
"""
Clinical Trial Data Analysis Pipeline Runner

This script serves as the main entry point for the clinical trial data analysis pipeline.
It orchestrates the extraction and analysis steps for processing clinical trial data from JSON files.
"""

import os
import sys
import argparse
import logging
from typing import List, Optional
import json
import shutil
import requests

# Import our modules
from trial_data_extractor import ClinicalTrialExtractor
from trial_data_analyzer import ClinicalTrialAnalyzer, clean_output_directory
from db_handler import ClinicalTrialDatabaseHandler

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def download_trial_data(nctid: str, debug_dir: str) -> str:
    """
    Download clinical trial data from ClinicalTrials.gov API.
    
    Args:
        nctid: NCT ID of the clinical trial (e.g., "NCT00001372")
        debug_dir: Directory to save the downloaded JSON file
    
    Returns:
        Path to the downloaded JSON file
    
    Raises:
        Exception: If the API request fails or data cannot be saved
    """
    # Ensure debug directory exists
    os.makedirs(debug_dir, exist_ok=True)
    
    # Construct API URL
    url = f"https://clinicaltrials.gov/api/v2/studies/{nctid}"
    
    try:
        logger.info(f"Downloading trial data for {nctid} from {url}")
        response = requests.get(url)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        # Get JSON data
        data = response.json()
        
        # Save to file
        output_file = os.path.join(debug_dir, f"{nctid}.json")
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        
        logger.info(f"Successfully downloaded and saved trial data to {output_file}")
        return output_file
        
    except requests.exceptions.RequestException as e:
        raise Exception(f"Failed to download trial data for {nctid}: {e}")
    except json.JSONDecodeError as e:
        raise Exception(f"Failed to parse JSON response for {nctid}: {e}")
    except IOError as e:
        raise Exception(f"Failed to save trial data for {nctid}: {e}")

def push_to_database(
    analysis_file: str,
    db_host: str = 'localhost',
    db_port: int = 5432,
    db_name: str = None,
    db_user: str = 'postgres',
    db_password: str = 'admin',
    table_name: str = 'myclinicaltrials'
) -> bool:
    """
    Push analysis results to PostgreSQL database.
    
    Args:
        analysis_file: Path to the analysis JSON file
        db_host: Database host
        db_port: Database port
        db_name: Database name
        db_user: Database user
        db_password: Database password
        table_name: Table name to insert data into
    
    Returns:
        True if successful, False otherwise
    """
    if not db_name:
        logger.error("Database name is required for database operations")
        return False
    
    if not os.path.exists(analysis_file):
        logger.error(f"Analysis file not found: {analysis_file}")
        return False
    
    try:
        # Use database handler with context manager
        with ClinicalTrialDatabaseHandler(
            host=db_host,
            port=db_port,
            database=db_name,
            user=db_user,
            password=db_password
        ) as db_handler:
            
            # Check if table exists
            if not db_handler.check_table_exists(table_name):
                logger.error(f"Table '{table_name}' does not exist in database '{db_name}'. "
                           f"Please create it first using create_db_schema.py")
                return False
            
            # Insert analysis data
            success = db_handler.insert_analysis_data(analysis_file, table_name)
            
            if success:
                logger.info(f"Successfully pushed analysis data to database table '{table_name}'")
            else:
                logger.error("Failed to push analysis data to database")
            
            return success
            
    except Exception as e:
        logger.error(f"Database operation failed: {e}")
        return False

def process_file(
    input_file: str, 
    output_dir: str, 
    api_key: Optional[str] = None,
    extraction_only: bool = False,
    debug_mode: bool = True,
    push_to_db: bool = False,
    db_config: Optional[dict] = None
) -> tuple:
    """
    Process a single clinical trial file through the complete pipeline.
    
    Args:
        input_file: Path to the input JSON file
        output_dir: Directory to save output files
        api_key: OpenAI API key (optional)
        extraction_only: Whether to only perform extraction without LLM analysis
        debug_mode: Whether to save intermediate data for debugging
        push_to_db: Whether to push results to database
        db_config: Database configuration dictionary
    
    Returns:
        Tuple of (extraction_success, analysis_success, db_push_success)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create debug directory if in debug mode
    debug_dir = None
    if debug_mode:
        debug_dir = os.path.join(output_dir, "debug")
        os.makedirs(debug_dir, exist_ok=True)
    
    # Step 1: Extract structured data using regex patterns
    file_basename = os.path.basename(input_file)
    name_without_ext = os.path.splitext(file_basename)[0]
    
    # Determine output paths
    extraction_output = os.path.join(output_dir, f"{name_without_ext}_extracted.json")
    if debug_mode:
        # In debug mode, save extraction output to debug directory
        extraction_output = os.path.join(debug_dir, f"{name_without_ext}_extracted.json")
    
    extraction_success = False
    analysis_success = False
    db_push_success = False
    
    try:
        extractor = ClinicalTrialExtractor(input_file)
        extractor.extract_all()
        extractor.save_extracted_data(extraction_output)
        extraction_success = True
        logger.info(f"Extraction completed for {input_file}")
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return extraction_success, analysis_success, db_push_success
    
    # Step 2: Analyze extracted data using LLM (if not extraction only)
    analysis_output = None
    if not extraction_only:
        analysis_output = os.path.join(output_dir, f"{name_without_ext}_analyzed.json")
        
        try:
            analyzer = ClinicalTrialAnalyzer(extraction_output, api_key, debug_mode)
            analyzer.analyze_trial_data()
            analyzer.save_analyzed_data(analysis_output)
            analysis_success = True
            logger.info(f"Analysis completed for {extraction_output}")
        except Exception as e:
            logger.error(f"Analysis failed for {input_file}: {e}")
            # Delete any partially created analysis file to avoid confusion
            if os.path.exists(analysis_output):
                try:
                    os.remove(analysis_output)
                    logger.info(f"Removed incomplete analysis file: {analysis_output}")
                except Exception as cleanup_error:
                    logger.warning(f"Could not remove incomplete analysis file: {cleanup_error}")
    else:
        logger.info("Skipping LLM analysis step")
        analysis_success = True  # Mark as successful if intentionally skipped
        
        # If extraction only but debug mode is off, copy extraction output to main directory
        if not debug_mode:
            main_extraction_output = os.path.join(output_dir, f"{name_without_ext}_extracted.json")
            try:
                shutil.copy2(extraction_output, main_extraction_output)
                logger.info(f"Copied extraction output to {main_extraction_output}")
            except Exception as e:
                logger.warning(f"Could not copy extraction output: {e}")
    
    # Step 3: Push to database if requested and analysis was successful
    if push_to_db and analysis_success and not extraction_only and analysis_output and db_config:
        logger.info("Pushing analysis results to database...")
        db_push_success = push_to_database(analysis_output, **db_config)
    elif push_to_db and extraction_only:
        logger.warning("Database push skipped: extraction-only mode does not generate analysis files")
    elif push_to_db and not analysis_success:
        logger.warning("Database push skipped: analysis was not successful")
    
    return extraction_success, analysis_success, db_push_success

def process_nctid(
    nctid: str,
    output_dir: str,
    api_key: Optional[str] = None,
    extraction_only: bool = False,
    debug_mode: bool = True,
    push_to_db: bool = False,
    db_config: Optional[dict] = None
) -> tuple:
    """
    Process a clinical trial by downloading data from ClinicalTrials.gov API using NCT ID.
    
    Args:
        nctid: NCT ID of the clinical trial (e.g., "NCT00001372")
        output_dir: Directory to save output files
        api_key: OpenAI API key (optional)
        extraction_only: Whether to only perform extraction without LLM analysis
        debug_mode: Whether to save intermediate data for debugging
        push_to_db: Whether to push results to database
        db_config: Database configuration dictionary
    
    Returns:
        Tuple of (extraction_success, analysis_success, db_push_success)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Create debug directory (required for downloading)
    debug_dir = os.path.join(output_dir, "debug")
    os.makedirs(debug_dir, exist_ok=True)
    
    try:
        # Download the trial data
        downloaded_file = download_trial_data(nctid, debug_dir)
        
        # Process the downloaded file
        extraction_success, analysis_success, db_push_success = process_file(
            downloaded_file, output_dir, api_key, extraction_only, debug_mode, push_to_db, db_config
        )
        
        return extraction_success, analysis_success, db_push_success
        
    except Exception as e:
        logger.error(f"Failed to process NCT ID {nctid}: {e}")
        return False, False, False

def process_directory(
    input_dir: str, 
    output_dir: str, 
    api_key: Optional[str] = None,
    extraction_only: bool = False,
    debug_mode: bool = True,
    push_to_db: bool = False,
    db_config: Optional[dict] = None
) -> None:
    """
    Process all JSON files in a directory.
    
    Args:
        input_dir: Directory containing input JSON files
        output_dir: Directory to save output files
        api_key: OpenAI API key (optional)
        extraction_only: Whether to only perform extraction without LLM analysis
        debug_mode: Whether to save intermediate data for debugging
        push_to_db: Whether to push results to database
        db_config: Database configuration dictionary
    """
    if not os.path.isdir(input_dir):
        logger.error(f"Input directory not found: {input_dir}")
        return
    
    os.makedirs(output_dir, exist_ok=True)
    
    # Find all JSON files in the directory
    json_files = [os.path.join(input_dir, f) for f in os.listdir(input_dir) 
                 if f.endswith('.json') and os.path.isfile(os.path.join(input_dir, f))]
    
    if not json_files:
        logger.warning(f"No JSON files found in {input_dir}")
        return
    
    logger.info(f"Found {len(json_files)} JSON files to process")
    
    # Process each file
    results = {
        'total': len(json_files),
        'extraction_success': 0,
        'analysis_success': 0,
        'db_push_success': 0
    }
    
    for json_file in json_files:
        logger.info(f"Processing {json_file}")
        extraction_ok, analysis_ok, db_push_ok = process_file(
            json_file, output_dir, api_key, extraction_only, debug_mode, push_to_db, db_config
        )
        
        if extraction_ok:
            results['extraction_success'] += 1
        if analysis_ok:
            results['analysis_success'] += 1
        if db_push_ok:
            results['db_push_success'] += 1
    
    # Log summary
    logger.info(f"Processing complete. Results: {results}")

def main():
    """Main function to run the clinical trial data analysis pipeline."""
    parser = argparse.ArgumentParser(description='Clinical Trial Data Analysis Pipeline Runner')
    
    # Input arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--file', help='Path to a single JSON file to process')
    input_group.add_argument('-d', '--directory', help='Path to a directory containing JSON files to process')
    input_group.add_argument('-n', '--nctid', help='NCT ID to download and process from ClinicalTrials.gov API')
    
    # Output arguments
    parser.add_argument('-o', '--output', required=True, help='Directory to save output files')
    
    # Optional arguments
    parser.add_argument('-k', '--api_key', help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)')
    parser.add_argument('--extraction-only', action='store_true', help='Only perform extraction without LLM analysis')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to save intermediate data')
    parser.add_argument('--no-clean', action='store_true', help='Do not clean output directory before processing')
    
    # Database arguments
    parser.add_argument('--push-to-db', action='store_true', help='Push analysis results to PostgreSQL database')
    parser.add_argument('--db-host', default='localhost', help='Database host (default: localhost)')
    parser.add_argument('--db-port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument('--db-name', default='ctdb', help='Database name (default: ctdb)')
    parser.add_argument('--db-user', default='postgres', help='Database user (default: postgres)')
    parser.add_argument('--db-password', default='admin', help='Database password (default: admin)')
    parser.add_argument('--db-table', default='myclinicaltrials', help='Database table name (default: myclinicaltrials)')
    
    args = parser.parse_args()
    
    # Debug mode is now enabled by default in the function parameters
    debug_mode = True  # Always enable debug mode
    
    # Prepare database configuration
    db_config = None
    if args.push_to_db:
        db_config = {
            'db_host': args.db_host,
            'db_port': args.db_port,
            'db_name': args.db_name,
            'db_user': args.db_user,
            'db_password': args.db_password,
            'table_name': args.db_table
        }
    
    # Clean output directory by default unless --no-clean is specified
    if not args.no_clean and os.path.exists(args.output):
        clean_output_directory(args.output)
    
    # Process input
    if args.file:
        if not os.path.isfile(args.file):
            logger.error(f"Input file not found: {args.file}")
            sys.exit(1)
        
        logger.info(f"Processing file {args.file}")
        extraction_ok, analysis_ok, db_push_ok = process_file(
            args.file, args.output, args.api_key, args.extraction_only, debug_mode, args.push_to_db, db_config
        )
        
        # Print summary
        print("Extraction completed successfully." if extraction_ok else "Extraction failed.")
        if not args.extraction_only:
            print("Analysis completed successfully." if analysis_ok else "Analysis failed.")
        if args.push_to_db:
            print("Database push completed successfully." if db_push_ok else "Database push failed.")
    
    elif args.directory:
        logger.info(f"Processing directory {args.directory}")
        process_directory(args.directory, args.output, args.api_key, args.extraction_only, debug_mode, args.push_to_db, db_config)
    
    elif args.nctid:
        logger.info(f"Processing NCT ID {args.nctid}")
        extraction_ok, analysis_ok, db_push_ok = process_nctid(
            args.nctid, args.output, args.api_key, args.extraction_only, debug_mode, args.push_to_db, db_config
        )
        
        # Print summary
        print("Extraction completed successfully." if extraction_ok else "Extraction failed.")
        if not args.extraction_only:
            print("Analysis completed successfully." if analysis_ok else "Analysis failed.")
        if args.push_to_db:
            print("Database push completed successfully." if db_push_ok else "Database push failed.")

if __name__ == '__main__':
    main() 