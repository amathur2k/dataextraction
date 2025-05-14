#!/usr/bin/env python3
"""
Clinical Trial Data Analysis Pipeline

This script combines the extraction and LLM enhancement steps into a complete
pipeline for analyzing clinical trial data from JSON files.
"""

import os
import sys
import argparse
import logging
from typing import List, Optional
import json

# Import our modules
from trial_data_extractor import ClinicalTrialExtractor
from llm_enhancer import LLMEnhancer

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
    skip_llm: bool = False
) -> tuple:
    """
    Process a single clinical trial JSON file through extraction and enhancement.
    
    Args:
        input_file: Path to the input JSON file
        output_dir: Directory to save output files
        api_key: OpenAI API key for LLM enhancement
        skip_llm: Whether to skip the LLM enhancement step
    
    Returns:
        Tuple of (extraction_success, enhancement_success) booleans
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Set up file paths
    basename = os.path.basename(input_file)
    name_without_ext = os.path.splitext(basename)[0]
    extracted_file = os.path.join(output_dir, f"{name_without_ext}_extracted.json")
    enhanced_file = os.path.join(output_dir, f"{name_without_ext}_enhanced.json")
    
    # Step 1: Extract structured data from the trial JSON
    logger.info(f"Extracting data from {input_file}")
    extractor = ClinicalTrialExtractor(input_file)
    try:
        extracted_data = extractor.extract_all()
        extractor.save_extracted_data(extracted_file)
        extraction_success = True
        logger.info(f"Extraction completed successfully. Output saved to {extracted_file}")
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return False, False
    
    # Step 2: Enhance the extracted data with LLM (if enabled)
    if not skip_llm:
        logger.info(f"Enhancing data from {extracted_file}")
        try:
            enhancer = LLMEnhancer(extracted_file, api_key)
            enhanced_data = enhancer.enhance_all()
            enhancer.save_enhanced_data(enhanced_file)
            enhancement_success = True
            logger.info(f"Enhancement completed successfully. Output saved to {enhanced_file}")
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return extraction_success, False
    else:
        logger.info("Skipping LLM enhancement step")
        enhancement_success = None
    
    return extraction_success, enhancement_success

def process_directory(
    input_dir: str, 
    output_dir: str, 
    api_key: Optional[str] = None, 
    skip_llm: bool = False,
    file_pattern: str = "*.json"
) -> tuple:
    """
    Process all JSON files in a directory through extraction and enhancement.
    
    Args:
        input_dir: Directory containing input JSON files
        output_dir: Directory to save output files
        api_key: OpenAI API key for LLM enhancement
        skip_llm: Whether to skip the LLM enhancement step
        file_pattern: Pattern to match input files (default: "*.json")
    
    Returns:
        Tuple of (files_processed, extraction_success_count, enhancement_success_count)
    """
    import glob
    
    # Get list of JSON files in the input directory
    input_pattern = os.path.join(input_dir, file_pattern)
    input_files = glob.glob(input_pattern)
    
    if not input_files:
        logger.warning(f"No JSON files found matching pattern {input_pattern}")
        return 0, 0, 0
    
    # Process each file
    extraction_success_count = 0
    enhancement_success_count = 0
    
    for input_file in input_files:
        logger.info(f"Processing file: {input_file}")
        extraction_success, enhancement_success = process_file(
            input_file, output_dir, api_key, skip_llm
        )
        
        if extraction_success:
            extraction_success_count += 1
        
        if enhancement_success:
            enhancement_success_count += 1
    
    return len(input_files), extraction_success_count, enhancement_success_count

def main():
    """Main function to run the clinical trial data analysis pipeline."""
    parser = argparse.ArgumentParser(description='Analyze clinical trial data from JSON files.')
    
    # Input file or directory options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--file', help='Path to a single input JSON file')
    input_group.add_argument('-d', '--directory', help='Path to a directory containing input JSON files')
    
    # Output options
    parser.add_argument('-o', '--output-dir', default='output', help='Directory to save output files (default: "output")')
    
    # LLM options
    parser.add_argument('-k', '--api-key', help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)')
    parser.add_argument('--skip-llm', action='store_true', help='Skip the LLM enhancement step')
    
    # Additional options
    parser.add_argument('-p', '--pattern', default='*.json', help='File pattern for JSON files when processing a directory (default: "*.json")')
    parser.add_argument('-v', '--verbose', action='store_true', help='Enable verbose logging')
    
    args = parser.parse_args()
    
    # Configure logging level
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Process input based on whether it's a file or directory
    if args.file:
        logger.info(f"Processing single file: {args.file}")
        extraction_success, enhancement_success = process_file(
            args.file, args.output_dir, args.api_key, args.skip_llm
        )
        
        if extraction_success:
            print("Extraction completed successfully.")
        else:
            print("Extraction failed.")
            sys.exit(1)
        
        if not args.skip_llm:
            if enhancement_success:
                print("Enhancement completed successfully.")
            else:
                print("Enhancement failed.")
                sys.exit(1)
    else:
        logger.info(f"Processing directory: {args.directory}")
        files_processed, extraction_success_count, enhancement_success_count = process_directory(
            args.directory, args.output_dir, args.api_key, args.skip_llm, args.pattern
        )
        
        print(f"Processed {files_processed} files:")
        print(f"  - Extraction successful for {extraction_success_count} files")
        
        if not args.skip_llm:
            print(f"  - Enhancement successful for {enhancement_success_count} files")
    
    logger.info("Analysis pipeline completed.")

if __name__ == '__main__':
    main() 