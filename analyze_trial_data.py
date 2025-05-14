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
from structured_summary import StructuredSummaryGenerator

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
    skip_llm: bool = False,
    skip_summary: bool = False
) -> tuple:
    """
    Process a single clinical trial file through the complete pipeline.
    
    Args:
        input_file: Path to the input JSON file
        output_dir: Directory to save output files
        api_key: OpenAI API key (optional)
        skip_llm: Whether to skip the LLM enhancement step
        skip_summary: Whether to skip the structured summary generation step
    
    Returns:
        Tuple of (extraction_success, enhancement_success, summary_success)
    """
    # Create output directory if it doesn't exist
    os.makedirs(output_dir, exist_ok=True)
    
    # Step 1: Extract structured data using regex patterns
    file_basename = os.path.basename(input_file)
    name_without_ext = os.path.splitext(file_basename)[0]
    extraction_output = os.path.join(output_dir, f"{name_without_ext}_extracted.json")
    
    extraction_success = False
    enhancement_success = False
    summary_success = False
    
    try:
        extractor = ClinicalTrialExtractor(input_file)
        extractor.extract_all()
        extractor.save_extracted_data(extraction_output)
        extraction_success = True
        logger.info(f"Extraction completed for {input_file}")
    except Exception as e:
        logger.error(f"Extraction failed: {e}")
        return extraction_success, enhancement_success, summary_success
    
    # Step 2: Enhance extracted data using LLM (if not skipped)
    if not skip_llm:
        enhancement_output = os.path.join(output_dir, f"{name_without_ext}_enhanced.json")
        
        try:
            enhancer = LLMEnhancer(extraction_output, api_key)
            enhancer.enhance_all()
            enhancer.save_enhanced_data(enhancement_output)
            enhancement_success = True
            logger.info(f"Enhancement completed for {extraction_output}")
        except Exception as e:
            logger.error(f"Enhancement failed: {e}")
            return extraction_success, enhancement_success, summary_success
    else:
        logger.info("Skipping LLM enhancement step")
        enhancement_success = True  # Mark as successful if intentionally skipped
    
    # Step 3: Generate structured summary (if not skipped)
    if not skip_summary and enhancement_success:
        summary_output = os.path.join(output_dir, f"{name_without_ext}_structured_summary.json")
        
        try:
            # Use the enhanced data as input if available, otherwise use extracted data
            input_for_summary = os.path.join(output_dir, f"{name_without_ext}_enhanced.json") if enhancement_success else extraction_output
            
            generator = StructuredSummaryGenerator(input_for_summary)
            generator.generate_structured_summary()
            generator.save_structured_summary(summary_output)
            summary_success = True
            logger.info(f"Structured summary generated for {input_for_summary}")
        except Exception as e:
            logger.error(f"Structured summary generation failed: {e}")
    else:
        if skip_summary:
            logger.info("Skipping structured summary generation step")
            summary_success = True  # Mark as successful if intentionally skipped
    
    return extraction_success, enhancement_success, summary_success

def process_directory(
    input_dir: str, 
    output_dir: str, 
    api_key: Optional[str] = None,
    skip_llm: bool = False,
    skip_summary: bool = False
) -> None:
    """
    Process all JSON files in a directory.
    
    Args:
        input_dir: Directory containing input JSON files
        output_dir: Directory to save output files
        api_key: OpenAI API key (optional)
        skip_llm: Whether to skip the LLM enhancement step
        skip_summary: Whether to skip the structured summary generation step
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
        'enhancement_success': 0,
        'summary_success': 0
    }
    
    for json_file in json_files:
        logger.info(f"Processing {json_file}")
        extraction_ok, enhancement_ok, summary_ok = process_file(
            json_file, output_dir, api_key, skip_llm, skip_summary
        )
        
        if extraction_ok:
            results['extraction_success'] += 1
        if enhancement_ok:
            results['enhancement_success'] += 1
        if summary_ok:
            results['summary_success'] += 1
    
    # Log summary
    logger.info(f"Processing complete. Results: {results}")

def main():
    """Main function to run the clinical trial data analysis pipeline."""
    parser = argparse.ArgumentParser(description='Clinical Trial Data Analysis Pipeline')
    
    # Input arguments
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument('-f', '--file', help='Path to a single JSON file to process')
    input_group.add_argument('-d', '--directory', help='Path to a directory containing JSON files to process')
    
    # Output arguments
    parser.add_argument('-o', '--output', required=True, help='Directory to save output files')
    
    # Optional arguments
    parser.add_argument('-k', '--api_key', help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)')
    parser.add_argument('--skip-llm', action='store_true', help='Skip the LLM enhancement step')
    parser.add_argument('--skip-summary', action='store_true', help='Skip the structured summary generation step')
    
    args = parser.parse_args()
    
    # Process input
    if args.file:
        if not os.path.isfile(args.file):
            logger.error(f"Input file not found: {args.file}")
            sys.exit(1)
        
        logger.info(f"Processing file {args.file}")
        extraction_ok, enhancement_ok, summary_ok = process_file(
            args.file, args.output, args.api_key, args.skip_llm, args.skip_summary
        )
        
        # Print summary
        print("Extraction completed successfully." if extraction_ok else "Extraction failed.")
        if not args.skip_llm:
            print("Enhancement completed successfully." if enhancement_ok else "Enhancement failed.")
        if not args.skip_summary:
            print("Structured summary generated successfully." if summary_ok else "Structured summary generation failed.")
    
    elif args.directory:
        logger.info(f"Processing directory {args.directory}")
        process_directory(args.directory, args.output, args.api_key, args.skip_llm, args.skip_summary)

if __name__ == '__main__':
    main() 