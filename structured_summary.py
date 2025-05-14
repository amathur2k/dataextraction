#!/usr/bin/env python3
"""
Clinical Trial Structured Summary Generator

This script takes the enhanced data from the first two passes and generates
a structured JSON with only the specific requested fields.
"""

import os
import json
import argparse
import logging
from typing import Dict, Any, Optional, List, Union

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class StructuredSummaryGenerator:
    """Class to generate structured summaries from enhanced clinical trial data."""
    
    def __init__(self, input_file: str):
        """
        Initialize the generator with the input file.
        
        Args:
            input_file: Path to the JSON file containing enhanced clinical trial data
        """
        self.input_file = input_file
        self.enhanced_data = None
        self.structured_summary = {}
    
    def load_data(self) -> None:
        """Load the enhanced clinical trial data from the input file."""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                self.enhanced_data = json.load(f)
            
            logger.info(f"Successfully loaded enhanced data from {self.input_file}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from {self.input_file}")
            self.enhanced_data = {}
        except FileNotFoundError:
            logger.error(f"File not found: {self.input_file}")
            self.enhanced_data = {}
    
    def get_value_or_na(self, data: Dict, *keys, default: str = "N/A") -> Any:
        """
        Safely get a value from nested dictionaries, returning N/A if not found.
        
        Args:
            data: Dictionary to extract value from
            *keys: Sequence of keys to navigate nested dictionaries
            default: Default value if key is not found
            
        Returns:
            The value if found, otherwise default
        """
        current = data
        for key in keys:
            if isinstance(current, dict) and key in current:
                current = current[key]
            else:
                return default
        
        # Return N/A for empty values
        if current is None or current == "" or (isinstance(current, list) and len(current) == 0):
            return default
            
        return current
    
    def extract_core_metadata(self) -> Dict:
        """Extract core trial metadata."""
        original_data = self.enhanced_data.get('original_data', {})
        basic_info = original_data.get('basic_info', {})
        
        return {
            "nct_id": self.get_value_or_na(basic_info, 'nct_id'),
            "status": self.get_value_or_na(basic_info, 'overall_status'),
            "dates": {
                "registration": self.get_value_or_na(basic_info, 'study_first_submitted'),
                "start": self.get_value_or_na(basic_info, 'start_date'),
                "completion": self.get_value_or_na(basic_info, 'completion_date'),
                "last_update": self.get_value_or_na(basic_info, 'last_update_posted')
            },
            "phase": self.get_value_or_na(basic_info, 'phases'),
            "study_type": self.get_value_or_na(basic_info, 'study_type'),
            "enrollment": {
                "target": self.get_value_or_na(basic_info, 'enrollment'),
                "actual": self.get_value_or_na(basic_info, 'enrollment_actual')
            },
            "sponsor_collaborators": {
                "primary_sponsor": self.get_value_or_na(basic_info, 'lead_sponsor'),
                "collaborators": self.get_value_or_na(basic_info, 'collaborators', default=[])
            }
        }
    
    def extract_scientific_content(self) -> Dict:
        """Extract scientific content."""
        original_data = self.enhanced_data.get('original_data', {})
        enhanced_outcomes = self.enhanced_data.get('enhanced_outcomes', {})
        
        interventions = original_data.get('interventions', [])
        intervention_details = []
        
        for intervention in interventions:
            intervention_details.append({
                "name": self.get_value_or_na(intervention, 'name'),
                "type": self.get_value_or_na(intervention, 'type'),
                "description": self.get_value_or_na(intervention, 'description'),
                "dosage": self.get_value_or_na(intervention, 'dosage'),
                "route": self.get_value_or_na(intervention, 'route')
            })
        
        # Try to extract mechanism of action from descriptions
        mechanism_of_action = "N/A"
        for intervention in interventions:
            description = intervention.get('description', '')
            if description and any(term in description.lower() for term in ['mechanism', 'inhibit', 'activate', 'target', 'pathway']):
                mechanism_of_action = description
                break
        
        # Extract study design
        design_info = original_data.get('design_info', {})
        
        # Extract outcomes
        outcomes = original_data.get('outcomes', {})
        primary_outcomes = []
        for outcome in outcomes.get('primary_outcomes', []):
            primary_outcomes.append({
                "measure": self.get_value_or_na(outcome, 'measure'),
                "description": self.get_value_or_na(outcome, 'description'),
                "timeframe": self.get_value_or_na(outcome, 'time_frame')
            })
        
        secondary_outcomes = []
        for outcome in outcomes.get('secondary_outcomes', []):
            secondary_outcomes.append({
                "measure": self.get_value_or_na(outcome, 'measure'),
                "description": self.get_value_or_na(outcome, 'description'),
                "timeframe": self.get_value_or_na(outcome, 'time_frame')
            })
        
        return {
            "intervention": intervention_details,
            "mechanism_of_action": mechanism_of_action,
            "target_pathway": {
                "gene": self.get_value_or_na({}, 'gene'),
                "protein": self.get_value_or_na({}, 'protein'),
                "chemical_compound": self.get_value_or_na({}, 'chemical_compound')
            },
            "biomarkers": self.get_value_or_na({}, 'biomarkers'),
            "study_design": {
                "allocation": self.get_value_or_na(design_info, 'allocation'),
                "intervention_model": self.get_value_or_na(design_info, 'intervention_model'),
                "masking": self.get_value_or_na(design_info, 'masking'),
                "primary_purpose": self.get_value_or_na(design_info, 'primary_purpose')
            },
            "arms_groups": self.get_value_or_na(original_data, 'arms', default=[]),
            "outcomes": {
                "primary": primary_outcomes,
                "secondary": secondary_outcomes
            }
        }
    
    def extract_patient_information(self) -> Dict:
        """Extract patient-related information."""
        original_data = self.enhanced_data.get('original_data', {})
        enhanced_eligibility = self.enhanced_data.get('enhanced_eligibility', {})
        enhanced_criteria = enhanced_eligibility.get('enhanced_criteria', {})
        
        # Get raw eligibility criteria
        eligibility = original_data.get('eligibility_criteria', {})
        inclusion = eligibility.get('inclusion_criteria', [])
        exclusion = eligibility.get('exclusion_criteria', [])
        
        # Extract demographics from enhanced data if available
        demographics = enhanced_criteria.get('demographics', {})
        age = demographics.get('age', {})
        gender = demographics.get('gender', 'N/A')
        
        # Extract disease characteristics and prior treatments
        medical_conditions = enhanced_criteria.get('medical_conditions', {})
        prior_treatments = enhanced_criteria.get('prior_treatments', {})
        
        return {
            "eligibility_criteria": {
                "inclusion": inclusion,
                "exclusion": exclusion
            },
            "demographics": {
                "age": {
                    "min": self.get_value_or_na(age, 'min'),
                    "max": self.get_value_or_na(age, 'max'),
                    "description": self.get_value_or_na(age, 'description')
                },
                "sex": gender,
                "other": demographics.get('other', [])
            },
            "disease_characteristics": {
                "required": medical_conditions.get('required', []),
                "excluded": medical_conditions.get('excluded', [])
            },
            "prior_treatments": {
                "required": prior_treatments.get('required', []),
                "excluded": prior_treatments.get('excluded', [])
            }
        }
    
    def extract_operational_aspects(self) -> Dict:
        """Extract operational aspects."""
        original_data = self.enhanced_data.get('original_data', {})
        
        # Extract locations
        locations = original_data.get('locations', [])
        formatted_locations = []
        
        for location in locations:
            formatted_locations.append({
                "facility": self.get_value_or_na(location, 'facility'),
                "city": self.get_value_or_na(location, 'city'),
                "state": self.get_value_or_na(location, 'state'),
                "country": self.get_value_or_na(location, 'country'),
                "status": self.get_value_or_na(location, 'status')
            })
        
        # Extract investigators
        investigators = []
        for location in locations:
            for investigator in location.get('investigators', []):
                investigators.append({
                    "name": self.get_value_or_na(investigator, 'name'),
                    "role": self.get_value_or_na(investigator, 'role'),
                    "facility": self.get_value_or_na(location, 'facility')
                })
        
        return {
            "locations": formatted_locations,
            "investigators": investigators,
            "enrollment_status": self.get_value_or_na(original_data, 'overall_status'),
            "ipd_sharing": self.get_value_or_na(original_data, 'patient_data', 'sharing_ipd')
        }
    
    def generate_structured_summary(self) -> Dict:
        """
        Generate a structured summary of the clinical trial.
        
        Returns:
            Dictionary containing the structured summary
        """
        if not self.enhanced_data:
            self.load_data()
        
        if not self.enhanced_data:
            return {"error": "Failed to load enhanced data"}
        
        self.structured_summary = {
            "core_trial_metadata": self.extract_core_metadata(),
            "scientific_content": self.extract_scientific_content(),
            "patient_related_information": self.extract_patient_information(),
            "operational_aspects": self.extract_operational_aspects()
        }
        
        return self.structured_summary
    
    def save_structured_summary(self, output_file: str) -> None:
        """
        Save the structured summary to a JSON file.
        
        Args:
            output_file: Path to the output JSON file
        """
        if not self.structured_summary:
            self.generate_structured_summary()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.structured_summary, f, indent=2)
            
            logger.info(f"Successfully saved structured summary to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save structured summary to {output_file}: {e}")


def main():
    """Main function to run the structured summary generator."""
    parser = argparse.ArgumentParser(description='Generate structured summary from enhanced clinical trial data.')
    parser.add_argument('input_file', help='Path to the input JSON file with enhanced clinical trial data')
    parser.add_argument('-o', '--output', help='Path to the output structured summary JSON file')
    
    args = parser.parse_args()
    
    # Set default output filename if not provided
    if not args.output:
        input_basename = os.path.basename(args.input_file)
        output_basename = os.path.splitext(input_basename)[0] + '_structured_summary.json'
        args.output = os.path.join(os.path.dirname(args.input_file), output_basename)
    
    # Generate the structured summary
    generator = StructuredSummaryGenerator(args.input_file)
    generator.generate_structured_summary()
    generator.save_structured_summary(args.output)
    
    # Print basic information about the summary
    print(f"Generated structured summary from {args.input_file}")
    print(f"Saved structured summary to {args.output}")


if __name__ == '__main__':
    main() 