#!/usr/bin/env python3
"""
Clinical Trial Data Extractor

This script extracts structured data from clinical trial JSON files using regex patterns
in the first pass and prepares data for LLM-based enhancement in the second pass.
"""

import json
import re
import os
import argparse
from typing import Dict, List, Any, Optional, Union
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ClinicalTrialExtractor:
    """Class to extract structured data from clinical trial JSON files."""
    
    def __init__(self, input_file: str):
        """
        Initialize the extractor with the input file.
        
        Args:
            input_file: Path to the JSON file containing clinical trial data
        """
        self.input_file = input_file
        self.trial_data = None
        self.extracted_data = {}
        
    def load_data(self) -> None:
        """Load the JSON data from the input file."""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                
            # Handle both single trial and array of trials
            if isinstance(data, list):
                if len(data) > 0:
                    self.trial_data = data[0]  # Take the first trial if multiple
                else:
                    logger.error(f"Empty trial data in {self.input_file}")
                    self.trial_data = {}
            else:
                self.trial_data = data
                
            logger.info(f"Successfully loaded data from {self.input_file}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from {self.input_file}")
            self.trial_data = {}
        except FileNotFoundError:
            logger.error(f"File not found: {self.input_file}")
            self.trial_data = {}
    
    def get_nested_value(self, data: Dict, path: str) -> Any:
        """
        Get a value from a nested dictionary using a dot-separated path.
        
        Args:
            data: Dictionary to extract value from
            path: Dot-separated path (e.g., 'protocolSection.statusModule.overallStatus')
        
        Returns:
            The value at the specified path or None if not found
        """
        keys = path.split('.')
        current = data
        
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return None
        
        return current
    
    def extract_basic_info(self) -> Dict:
        """
        Extract basic information from the trial data.
        
        Returns:
            Dictionary containing extracted basic trial information
        """
        if not self.trial_data:
            return {}
        
        # Initialize protocol section reference to simplify paths
        protocol = self.trial_data.get('protocolSection', {})
        
        # Extract basic information
        basic_info = {
            'nct_id': self.get_nested_value(protocol, 'identificationModule.nctId'),
            'brief_title': self.get_nested_value(protocol, 'identificationModule.briefTitle'),
            'official_title': self.get_nested_value(protocol, 'identificationModule.officialTitle'),
            'overall_status': self.get_nested_value(protocol, 'statusModule.overallStatus'),
            'study_type': self.get_nested_value(protocol, 'designModule.studyType'),
            'phases': self.get_nested_value(protocol, 'designModule.phases'),
            'enrollment': self.get_nested_value(protocol, 'designModule.enrollmentInfo.count'),
            'enrollment_type': self.get_nested_value(protocol, 'designModule.enrollmentInfo.type'),
            'start_date': self.get_nested_value(protocol, 'statusModule.startDateStruct.date'),
            'primary_completion_date': self.get_nested_value(protocol, 'statusModule.primaryCompletionDateStruct.date'),
            'study_first_submit_date': self.get_nested_value(protocol, 'statusModule.studyFirstSubmitDate'),
            'lead_sponsor': self.get_nested_value(protocol, 'sponsorCollaboratorsModule.leadSponsor.name'),
            'lead_sponsor_class': self.get_nested_value(protocol, 'sponsorCollaboratorsModule.leadSponsor.class'),
        }
        
        # Extract conditions
        conditions = self.get_nested_value(protocol, 'conditionsModule.conditions')
        if isinstance(conditions, list):
            basic_info['conditions'] = conditions
        
        # Extract study design info
        design_info = self.get_nested_value(protocol, 'designModule.designInfo')
        if design_info:
            basic_info['allocation'] = design_info.get('allocation')
            basic_info['intervention_model'] = design_info.get('interventionModel')
            basic_info['primary_purpose'] = design_info.get('primaryPurpose')
            
            if 'maskingInfo' in design_info:
                basic_info['masking'] = design_info['maskingInfo'].get('masking')
                basic_info['who_masked'] = design_info['maskingInfo'].get('whoMasked')
        
        return basic_info
    
    def extract_eligibility_criteria(self) -> Dict:
        """
        Extract and parse eligibility criteria using regex patterns.
        
        Returns:
            Dictionary containing parsed inclusion and exclusion criteria
        """
        if not self.trial_data:
            return {'inclusion_criteria': [], 'exclusion_criteria': []}
        
        # Get eligibility criteria text
        criteria_text = self.get_nested_value(
            self.trial_data.get('protocolSection', {}), 
            'eligibilityModule.eligibilityCriteria'
        )
        
        if not criteria_text:
            return {'inclusion_criteria': [], 'exclusion_criteria': []}
        
        # Find inclusion and exclusion sections
        inclusion_section = self._extract_section(criteria_text, r'(?i)(?:INCLUSION\s+CRITERIA|ELIGIBILITY\s+CRITERIA)[:.\-]?\s*(.*?)(?:(?:EXCLUSION\s+CRITERIA)|$)', True)
        exclusion_section = self._extract_section(criteria_text, r'(?i)EXCLUSION\s+CRITERIA[:.\-]?\s*(.*?)$', True)
        
        # Parse criteria into lists
        inclusion_criteria = self._parse_criteria_list(inclusion_section)
        exclusion_criteria = self._parse_criteria_list(exclusion_section)
        
        return {
            'inclusion_criteria': inclusion_criteria,
            'exclusion_criteria': exclusion_criteria
        }
    
    def _extract_section(self, text: str, pattern: str, dotall: bool = False) -> str:
        """
        Extract a section of text using a regex pattern.
        
        Args:
            text: Text to search in
            pattern: Regex pattern to use
            dotall: Whether to use re.DOTALL flag
        
        Returns:
            Extracted section or empty string if not found
        """
        flags = re.DOTALL if dotall else 0
        match = re.search(pattern, text, flags)
        return match.group(1).strip() if match else ""
    
    def _parse_criteria_list(self, text: str) -> List[str]:
        """
        Parse a criteria section into a list of individual criteria.
        
        Args:
            text: Text containing criteria
        
        Returns:
            List of individual criteria
        """
        if not text:
            return []
        
        # Try to find numbered or bulleted list items
        criteria = []
        
        # Pattern for numbered criteria like "1.", "2.", etc.
        numbered_pattern = r'(?:^|\n)(?:\s*\d+\.|\s*-|\s*\*|\s*•)\s*(.+?)(?=(?:\n(?:\s*\d+\.|\s*-|\s*\*|\s*•))|$)'
        numbered_matches = re.finditer(numbered_pattern, text, re.MULTILINE | re.DOTALL)
        
        for match in numbered_matches:
            criterion = match.group(1).strip()
            if criterion:
                # Clean up the criterion text
                criterion = re.sub(r'\s+', ' ', criterion)
                criteria.append(criterion)
        
        # If no numbered items found, try to split by newlines
        if not criteria:
            lines = [line.strip() for line in text.split('\n') if line.strip()]
            
            # Filter out lines that are likely headers or not criteria
            criteria = [line for line in lines if len(line) > 10 and not re.match(r'^(?:INCLUSION|EXCLUSION|CRITERIA|NOTE):', line, re.IGNORECASE)]
        
        return criteria
    
    def extract_interventions(self) -> List[Dict]:
        """
        Extract information about interventions used in the trial.
        
        Returns:
            List of dictionaries with intervention details
        """
        if not self.trial_data:
            return []
        
        interventions = self.get_nested_value(
            self.trial_data.get('protocolSection', {}),
            'armsInterventionsModule.interventions'
        )
        
        if not interventions:
            return []
        
        # Extract relevant information from each intervention
        result = []
        for intervention in interventions:
            intervention_info = {
                'name': intervention.get('name'),
                'type': intervention.get('type'),
                'description': intervention.get('description'),
                'arm_group_labels': intervention.get('armGroupLabels', []),
                'other_names': intervention.get('otherNames', [])
            }
            result.append(intervention_info)
        
        return result
    
    def extract_outcomes(self) -> Dict:
        """
        Extract primary and secondary outcome measures from the trial.
        
        Returns:
            Dictionary containing primary and secondary outcomes
        """
        if not self.trial_data:
            return {'primary_outcomes': [], 'secondary_outcomes': []}
        
        outcomes_module = self.get_nested_value(
            self.trial_data.get('protocolSection', {}),
            'outcomesModule'
        )
        
        if not outcomes_module:
            return {'primary_outcomes': [], 'secondary_outcomes': []}
        
        # Extract primary outcomes
        primary_outcomes = []
        for outcome in outcomes_module.get('primaryOutcomes', []):
            primary_outcomes.append({
                'measure': outcome.get('measure'),
                'description': outcome.get('description'),
                'time_frame': outcome.get('timeFrame')
            })
        
        # Extract secondary outcomes
        secondary_outcomes = []
        for outcome in outcomes_module.get('secondaryOutcomes', []):
            secondary_outcomes.append({
                'measure': outcome.get('measure'),
                'description': outcome.get('description'),
                'time_frame': outcome.get('timeFrame')
            })
        
        return {
            'primary_outcomes': primary_outcomes,
            'secondary_outcomes': secondary_outcomes
        }
    
    def extract_all(self) -> Dict:
        """
        Extract all available information from the trial data.
        
        Returns:
            Dictionary containing all extracted information
        """
        if not self.trial_data:
            self.load_data()
        
        self.extracted_data = {
            'basic_info': self.extract_basic_info(),
            'eligibility_criteria': self.extract_eligibility_criteria(),
            'interventions': self.extract_interventions(),
            'outcomes': self.extract_outcomes()
        }
        
        return self.extracted_data
    
    def save_extracted_data(self, output_file: str) -> None:
        """
        Save the extracted data to a JSON file.
        
        Args:
            output_file: Path to the output JSON file
        """
        if not self.extracted_data:
            self.extract_all()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.extracted_data, f, indent=2)
            
            logger.info(f"Successfully saved extracted data to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save data to {output_file}: {e}")
    
    def prepare_llm_input(self) -> Dict:
        """
        Prepare input for LLM-based enhancement.
        
        Returns:
            Dictionary containing data formatted for LLM processing
        """
        if not self.extracted_data:
            self.extract_all()
        
        # Prepare eligibility criteria for LLM processing
        eligibility_criteria = self.extracted_data.get('eligibility_criteria', {})
        inclusion_text = "\n".join([f"- {criterion}" for criterion in eligibility_criteria.get('inclusion_criteria', [])])
        exclusion_text = "\n".join([f"- {criterion}" for criterion in eligibility_criteria.get('exclusion_criteria', [])])
        
        # Prepare basic trial information
        basic_info = self.extracted_data.get('basic_info', {})
        title = basic_info.get('brief_title', '') or basic_info.get('official_title', '')
        
        # Prepare prompt for LLM
        llm_input = {
            'nct_id': basic_info.get('nct_id', ''),
            'title': title,
            'study_type': basic_info.get('study_type', ''),
            'phase': ', '.join(basic_info.get('phases', [])) if isinstance(basic_info.get('phases', []), list) else basic_info.get('phases', ''),
            'condition': ', '.join(basic_info.get('conditions', [])) if isinstance(basic_info.get('conditions', []), list) else '',
            'inclusion_criteria': inclusion_text,
            'exclusion_criteria': exclusion_text
        }
        
        return llm_input


def main():
    """Main function to run the clinical trial data extraction."""
    parser = argparse.ArgumentParser(description='Extract structured data from clinical trial JSON files.')
    parser.add_argument('input_file', help='Path to the input JSON file')
    parser.add_argument('-o', '--output', help='Path to the output JSON file')
    
    args = parser.parse_args()
    
    # Set default output filename if not provided
    if not args.output:
        input_basename = os.path.basename(args.input_file)
        output_basename = os.path.splitext(input_basename)[0] + '_extracted.json'
        args.output = os.path.join(os.path.dirname(args.input_file), output_basename)
    
    # Extract data from the input file
    extractor = ClinicalTrialExtractor(args.input_file)
    extractor.extract_all()
    extractor.save_extracted_data(args.output)
    
    # Print basic information about the extraction
    print(f"Extracted data from {args.input_file}")
    print(f"Saved extracted data to {args.output}")


if __name__ == '__main__':
    main() 