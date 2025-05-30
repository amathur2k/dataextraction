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

# Import our modules
from trial_data_extractor import ClinicalTrialExtractor
from trial_data_analyzer import ClinicalTrialAnalyzer, clean_output_directory

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def process_file(
    input_file: str, 
    output_dir: str, 
    api_key: Optional[str] = None,
    extraction_only: bool = False,
    debug_mode: bool = True
) -> tuple:
    """
    Process a single clinical trial file through the complete pipeline.
    
    Args:
        input_file: Path to the input JSON file
        output_dir: Directory to save output files
        api_key: OpenAI API key (optional)
        extraction_only: Whether to only perform extraction without LLM analysis
        debug_mode: Whether to save intermediate data for debugging
    
    Returns:
        Tuple of (extraction_success, analysis_success)
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
    
    try:
        extractor = ClinicalTrialExtractor(input_file)
        extractor.extract_all()
        extractor.save_extracted_data(extraction_output)
        extraction_success = True
        logger.info(f"Extraction completed for {input_file}")
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return extraction_success, analysis_success
    
    # Step 2: Analyze extracted data using LLM (if not extraction only)
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
    
    return extraction_success, analysis_success

def process_directory(
    input_dir: str, 
    output_dir: str, 
    api_key: Optional[str] = None,
    extraction_only: bool = False,
    debug_mode: bool = True
) -> None:
    """
    Process all JSON files in a directory.
    
    Args:
        input_dir: Directory containing input JSON files
        output_dir: Directory to save output files
        api_key: OpenAI API key (optional)
        extraction_only: Whether to only perform extraction without LLM analysis
        debug_mode: Whether to save intermediate data for debugging
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
        'analysis_success': 0
    }
    
    for json_file in json_files:
        logger.info(f"Processing {json_file}")
        extraction_ok, analysis_ok = process_file(
            json_file, output_dir, api_key, extraction_only, debug_mode
        )
        
        if extraction_ok:
            results['extraction_success'] += 1
        if analysis_ok:
            results['analysis_success'] += 1
    
    # Log summary
    logger.info(f"Processing complete. Results: {results}")

def main():
    """Main function to run the clinical trial data analysis pipeline."""
    parser = argparse.ArgumentParser(description='Clinical Trial Data Analysis Pipeline Runner')
    
    # Input arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--file', help='Path to a single JSON file to process')
    input_group.add_argument('-d', '--directory', help='Path to a directory containing JSON files to process')
    
    # Output arguments
    parser.add_argument('-o', '--output', required=True, help='Directory to save output files')
    
    # Optional arguments
    parser.add_argument('-k', '--api_key', help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)')
    parser.add_argument('--extraction-only', action='store_true', help='Only perform extraction without LLM analysis')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode to save intermediate data')
    parser.add_argument('--no-clean', action='store_true', help='Do not clean output directory before processing')
    
    args = parser.parse_args()
    
    # Debug mode is now enabled by default in the function parameters
    debug_mode = True  # Always enable debug mode
    
    # Clean output directory by default unless --no-clean is specified
    if not args.no_clean and os.path.exists(args.output):
        clean_output_directory(args.output)
    
    # Process input
    if args.file:
        if not os.path.isfile(args.file):
            logger.error(f"Input file not found: {args.file}")
            sys.exit(1)
        
        logger.info(f"Processing file {args.file}")
        extraction_ok, analysis_ok = process_file(
            args.file, args.output, args.api_key, args.extraction_only, debug_mode
        )
        
        # Print summary
        print("Extraction completed successfully." if extraction_ok else "Extraction failed.")
        if not args.extraction_only:
            print("Analysis completed successfully." if analysis_ok else "Analysis failed.")
    
    elif args.directory:
        logger.info(f"Processing directory {args.directory}")
        process_directory(args.directory, args.output, args.api_key, args.extraction_only, debug_mode)

if __name__ == '__main__':
    main() 