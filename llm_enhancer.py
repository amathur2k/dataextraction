#!/usr/bin/env python3
"""
Clinical Trial Data LLM Enhancer

This script enhances extracted clinical trial data using OpenAI GPT-4o API
to provide deeper analysis, structured categorization, and human-readable summaries.
"""

import os
import json
import argparse
import logging
from typing import Dict, List, Any, Optional, Union
import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LLMEnhancer:
    """Class to enhance clinical trial data using OpenAI LLM APIs."""
    
    def __init__(self, input_file: str, api_key: Optional[str] = None):
        """
        Initialize the enhancer with input file and API key.
        
        Args:
            input_file: Path to the JSON file containing extracted clinical trial data
            api_key: OpenAI API key (optional, can also be set via environment variable)
        """
        self.input_file = input_file
        self.extracted_data = None
        self.enhanced_data = {}
        
        # Set up OpenAI API
        if api_key:
            openai.api_key = api_key
        elif 'OPENAI_API_KEY' in os.environ:
            openai.api_key = os.environ['OPENAI_API_KEY']
        else:
            logger.warning("No OpenAI API key provided. Please set OPENAI_API_KEY environment variable or provide it as an argument.")
    
    def load_data(self) -> None:
        """Load the extracted clinical trial data from the input file."""
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                self.extracted_data = json.load(f)
            
            logger.info(f"Successfully loaded data from {self.input_file}")
        except json.JSONDecodeError:
            logger.error(f"Failed to parse JSON from {self.input_file}")
            self.extracted_data = {}
        except FileNotFoundError:
            logger.error(f"File not found: {self.input_file}")
            self.extracted_data = {}
    
    def _call_gpt4(self, messages: List[Dict[str, str]], max_tokens: int = 1500) -> str:
        """
        Call the OpenAI GPT-4o API.
        
        Args:
            messages: List of message dictionaries to send to the API
            max_tokens: Maximum number of tokens to generate
        
        Returns:
            The model's response text
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-4o",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0.2,  # Lower temperature for more consistent results
                n=1,
                stop=None
            )
            
            # Extract the response text
            return response.choices[0].message.content.strip()
        except Exception as e:
            logger.error(f"Error calling OpenAI API: {e}")
            return ""
    
    def enhance_eligibility_criteria(self) -> Dict:
        """
        Enhance eligibility criteria with structured categorization and analysis.
        
        Returns:
            Dictionary containing enhanced eligibility criteria
        """
        if not self.extracted_data:
            return {}
        
        eligibility_criteria = self.extracted_data.get('eligibility_criteria', {})
        basic_info = self.extracted_data.get('basic_info', {})
        
        # Prepare inclusion and exclusion criteria text
        inclusion_criteria = eligibility_criteria.get('inclusion_criteria', [])
        exclusion_criteria = eligibility_criteria.get('exclusion_criteria', [])
        
        inclusion_text = "\n".join([f"- {criterion}" for criterion in inclusion_criteria])
        exclusion_text = "\n".join([f"- {criterion}" for criterion in exclusion_criteria])
        
        # Create prompt for enhanced analysis
        prompt = f"""
You are a clinical trial data analyst. Analyze the following inclusion and exclusion criteria from a clinical trial and organize them into categories.

NCT ID: {basic_info.get('nct_id', 'Unknown')}
Trial Title: {basic_info.get('brief_title', 'Unknown')}
Conditions: {', '.join(basic_info.get('conditions', [])) if isinstance(basic_info.get('conditions', []), list) else 'Unknown'}

INCLUSION CRITERIA:
{inclusion_text}

EXCLUSION CRITERIA:
{exclusion_text}

Please categorize these criteria into the following structured format (JSON):
1. Demographics (age, gender, etc.)
2. Medical conditions (required diagnoses, comorbidities, etc.)
3. Prior treatments (medications, procedures, etc.)
4. Lab values and measurements (vitals, test results, etc.)
5. Special requirements (consent, availability, etc.)

For each criterion, extract important numerical values (e.g., age ≥18 years, BMI < 30) and time frames (e.g., within 6 months). 
Identify and normalize drug names and medical conditions.

Respond in this structured JSON format:
```json
{{
  "demographics": {{
    "age": {{"min": 18, "max": null, "description": "Adults aged 18 or older"}},
    "gender": "Both male and female",
    "other": []
  }},
  "medical_conditions": {{
    "required": [],
    "excluded": []
  }},
  "prior_treatments": {{
    "required": [],
    "excluded": []
  }},
  "lab_values": [],
  "special_requirements": []
}}
```
"""
        
        # Call GPT-4o API
        messages = [
            {"role": "system", "content": "You are a clinical trial data analyst that helps structure and analyze eligibility criteria."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_gpt4(messages, max_tokens=2000)
        
        # Extract JSON from the response
        try:
            # Find the JSON part within the response (between ```json and ```)
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
                enhanced_criteria = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                enhanced_criteria = json.loads(response)
            
            logger.info("Successfully enhanced eligibility criteria")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse enhanced criteria JSON: {e}")
            enhanced_criteria = {}
        
        return {
            'raw_criteria': {
                'inclusion': inclusion_criteria,
                'exclusion': exclusion_criteria
            },
            'enhanced_criteria': enhanced_criteria,
            'llm_response': response
        }
    
    def generate_study_summary(self) -> str:
        """
        Generate a concise human-readable summary of the clinical trial.
        
        Returns:
            String containing the summary
        """
        if not self.extracted_data:
            return ""
        
        basic_info = self.extracted_data.get('basic_info', {})
        eligibility = self.extracted_data.get('eligibility_criteria', {})
        interventions = self.extracted_data.get('interventions', [])
        outcomes = self.extracted_data.get('outcomes', {})
        
        # Prepare intervention text
        intervention_text = ""
        for idx, intervention in enumerate(interventions, 1):
            name = intervention.get('name', 'Unknown')
            type_val = intervention.get('type', 'Unknown')
            desc = intervention.get('description', 'No description')
            intervention_text += f"{idx}. {name} ({type_val}): {desc}\n"
        
        # Prepare outcome text
        primary_outcomes = outcomes.get('primary_outcomes', [])
        primary_outcome_text = "\n".join([f"- {outcome.get('measure', 'Unknown')}: {outcome.get('description', 'No description')}" 
                                          for outcome in primary_outcomes])
        
        # Create prompt for summary generation
        prompt = f"""
Please generate a concise but comprehensive summary of the following clinical trial information:

NCT ID: {basic_info.get('nct_id', 'Unknown')}
Title: {basic_info.get('brief_title', basic_info.get('official_title', 'Unknown'))}
Status: {basic_info.get('overall_status', 'Unknown')}
Phase: {', '.join(basic_info.get('phases', [])) if isinstance(basic_info.get('phases', []), list) else basic_info.get('phases', 'Unknown')}
Study Type: {basic_info.get('study_type', 'Unknown')}
Study Design: {basic_info.get('intervention_model', 'Unknown')} {basic_info.get('masking', 'Unknown')}
Conditions: {', '.join(basic_info.get('conditions', [])) if isinstance(basic_info.get('conditions', []), list) else 'Unknown'}
Sponsor: {basic_info.get('lead_sponsor', 'Unknown')}

INTERVENTIONS:
{intervention_text}

PRIMARY OUTCOMES:
{primary_outcome_text}

NUMBER OF INCLUSION CRITERIA: {len(eligibility.get('inclusion_criteria', []))}
NUMBER OF EXCLUSION CRITERIA: {len(eligibility.get('exclusion_criteria', []))}

Write a clear, comprehensive summary of this clinical trial in about 4-6 paragraphs. Include the purpose, design, interventions, primary outcomes, and key eligibility considerations. Make it informative but accessible to someone with basic medical knowledge. Focus on the most important aspects of the trial.
"""
        
        # Call GPT-4o API
        messages = [
            {"role": "system", "content": "You are a clinical trial summarizer that creates concise, informative summaries of clinical trials."},
            {"role": "user", "content": prompt}
        ]
        
        summary = self._call_gpt4(messages, max_tokens=1000)
        logger.info("Successfully generated study summary")
        
        return summary
    
    def analyze_outcomes(self) -> Dict:
        """
        Analyze and enhance understanding of study outcomes.
        
        Returns:
            Dictionary containing enhanced outcome analysis
        """
        if not self.extracted_data:
            return {}
        
        basic_info = self.extracted_data.get('basic_info', {})
        outcomes = self.extracted_data.get('outcomes', {})
        
        primary_outcomes = outcomes.get('primary_outcomes', [])
        secondary_outcomes = outcomes.get('secondary_outcomes', [])
        
        # Prepare outcome text
        primary_outcome_text = "\n".join([f"- {outcome.get('measure', 'Unknown')}: {outcome.get('description', 'No description')} (Time frame: {outcome.get('time_frame', 'Not specified')})" 
                                        for outcome in primary_outcomes])
        
        secondary_outcome_text = "\n".join([f"- {outcome.get('measure', 'Unknown')}: {outcome.get('description', 'No description')} (Time frame: {outcome.get('time_frame', 'Not specified')})" 
                                          for outcome in secondary_outcomes])
        
        # Create prompt for outcome analysis
        prompt = f"""
Please analyze the following clinical trial outcomes:

NCT ID: {basic_info.get('nct_id', 'Unknown')}
Title: {basic_info.get('brief_title', basic_info.get('official_title', 'Unknown'))}
Conditions: {', '.join(basic_info.get('conditions', [])) if isinstance(basic_info.get('conditions', []), list) else 'Unknown'}

PRIMARY OUTCOMES:
{primary_outcome_text}

SECONDARY OUTCOMES:
{secondary_outcome_text}

Provide a structured analysis of these outcomes in JSON format:

1. For each outcome, identify:
   - The measurement type (e.g., efficacy, safety, tolerability, etc.)
   - The specific variables or endpoints being measured
   - The time frame for measurement
   - The statistical approach if mentioned
   - The clinical significance/importance of this outcome

2. Create a summary that explains how these outcomes collectively evaluate the intervention's effectiveness and safety.

Respond with valid JSON in this format:
```json
{{
  "primary_outcomes_analysis": [
    {{
      "outcome": "Original outcome text",
      "measurement_type": "efficacy/safety/etc.",
      "endpoints": ["specific variables measured"],
      "time_frame": "extracted time frame",
      "statistical_approach": "any mentioned statistical methods or null",
      "clinical_significance": "why this outcome matters"
    }}
  ],
  "secondary_outcomes_analysis": [
    {{
      "outcome": "Original outcome text",
      "measurement_type": "efficacy/safety/etc.",
      "endpoints": ["specific variables measured"],
      "time_frame": "extracted time frame",
      "statistical_approach": "any mentioned statistical methods or null",
      "clinical_significance": "why this outcome matters"
    }}
  ],
  "overall_assessment_approach": "Summary of how these outcomes collectively evaluate the intervention"
}}
```
"""
        
        # Call GPT-4o API
        messages = [
            {"role": "system", "content": "You are a clinical trial outcome analyst who provides structured analysis of clinical trial outcomes."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_gpt4(messages, max_tokens=2000)
        
        # Extract JSON from the response
        try:
            # Find the JSON part within the response (between ```json and ```)
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
                outcomes_analysis = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                outcomes_analysis = json.loads(response)
            
            logger.info("Successfully analyzed trial outcomes")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse outcomes analysis JSON: {e}")
            outcomes_analysis = {}
        
        return {
            'raw_outcomes': {
                'primary': primary_outcomes,
                'secondary': secondary_outcomes
            },
            'enhanced_outcomes': outcomes_analysis,
            'llm_response': response
        }
    
    def enhance_all(self) -> Dict:
        """
        Enhance all available trial data.
        
        Returns:
            Dictionary containing all enhanced information
        """
        if not self.extracted_data:
            self.load_data()
        
        # Skip LLM processing if no API key
        if not openai.api_key:
            logger.warning("Skipping LLM enhancement because no API key is provided")
            return {
                'error': 'No OpenAI API key provided. Set OPENAI_API_KEY environment variable or provide it as an argument.'
            }
        
        # Enhance various aspects of the trial data
        enhanced_eligibility = self.enhance_eligibility_criteria()
        summary = self.generate_study_summary()
        enhanced_outcomes = self.analyze_outcomes()
        
        self.enhanced_data = {
            'study_summary': summary,
            'enhanced_eligibility': enhanced_eligibility,
            'enhanced_outcomes': enhanced_outcomes,
            'original_data': self.extracted_data
        }
        
        return self.enhanced_data
    
    def save_enhanced_data(self, output_file: str) -> None:
        """
        Save the enhanced data to a JSON file.
        
        Args:
            output_file: Path to the output JSON file
        """
        if not self.enhanced_data:
            self.enhance_all()
        
        try:
            with open(output_file, 'w', encoding='utf-8') as f:
                json.dump(self.enhanced_data, f, indent=2)
            
            logger.info(f"Successfully saved enhanced data to {output_file}")
        except Exception as e:
            logger.error(f"Failed to save data to {output_file}: {e}")


def main():
    """Main function to run the LLM enhancement of clinical trial data."""
    parser = argparse.ArgumentParser(description='Enhance clinical trial data using OpenAI GPT-4o API.')
    parser.add_argument('input_file', help='Path to the input JSON file with extracted clinical trial data')
    parser.add_argument('-o', '--output', help='Path to the output enhanced JSON file')
    parser.add_argument('-k', '--api_key', help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)')
    
    args = parser.parse_args()
    
    # Set default output filename if not provided
    if not args.output:
        input_basename = os.path.basename(args.input_file)
        output_basename = os.path.splitext(input_basename)[0] + '_enhanced.json'
        args.output = os.path.join(os.path.dirname(args.input_file), output_basename)
    
    # Enhance the extracted data
    enhancer = LLMEnhancer(args.input_file, args.api_key)
    enhancer.enhance_all()
    enhancer.save_enhanced_data(args.output)
    
    # Print basic information about the enhancement
    print(f"Enhanced data from {args.input_file}")
    print(f"Saved enhanced data to {args.output}")


if __name__ == '__main__':
    main() 