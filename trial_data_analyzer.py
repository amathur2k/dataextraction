#!/usr/bin/env python3
"""
Clinical Trial Data Analyzer

This script analyzes clinical trial data using OpenAI GPT-4o to provide enhanced
structured information and summaries with specific fields as required.
"""

import os
import json
import argparse
import logging
import shutil
from typing import Dict, List, Any, Optional, Union

import openai

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ClinicalTrialAnalyzer:
    """Class to analyze clinical trial data using OpenAI LLM APIs."""
    
    def __init__(self, input_file: str, api_key: Optional[str] = None, debug_mode: bool = False):
        """
        Initialize the analyzer with input file and API key.
        
        Args:
            input_file: Path to the JSON file containing extracted clinical trial data
            api_key: OpenAI API key (optional, can also be set via environment variable)
            debug_mode: Whether to save intermediate data for debugging
        """
        self.input_file = input_file
        self.extracted_data = None
        self.analyzed_data = {}
        self.debug_mode = debug_mode
        
        # Set up OpenAI API
        if api_key:
            openai.api_key = api_key
        elif 'OPENAI_API_KEY' in os.environ:
            openai.api_key = os.environ['OPENAI_API_KEY']
        else:
            logger.warning("No OpenAI API key provided. Please set OPENAI_API_KEY environment variable or provide it as an argument.")
    
    def load_data(self) -> None:
        """
        Load the extracted clinical trial data from the input file.
        
        Raises:
            FileNotFoundError: If the input file does not exist
            json.JSONDecodeError: If the input file is not valid JSON
        """
        try:
            with open(self.input_file, 'r', encoding='utf-8') as f:
                self.extracted_data = json.load(f)
            
            logger.info(f"Successfully loaded data from {self.input_file}")
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse JSON from {self.input_file}")
            raise
        except FileNotFoundError as e:
            logger.error(f"File not found: {self.input_file}")
            raise
    
    def _call_gpt4(self, messages: List[Dict[str, str]], max_tokens: int = 3500) -> str:
        """
        Call the OpenAI GPT-4o API.
        
        Args:
            messages: List of message dictionaries to send to the API
            max_tokens: Maximum number of tokens to generate
        
        Returns:
            The model's response text
            
        Raises:
            RuntimeError: If the API call fails
        """
        try:
            response = openai.chat.completions.create(
                model="gpt-4.1",
                messages=messages,
                max_tokens=max_tokens,
                temperature=0,  # Lower temperature for more consistent results
                n=1,
                stop=None
            )
            
            # Extract the response text
            return response.choices[0].message.content.strip()
        except Exception as e:
            error_msg = f"Error calling OpenAI API: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e

    def extract_mechanism_and_targets(self, interventions: List[Dict]) -> Dict:
        """
        Extract mechanism of action and target/pathway information using a specialized prompt.
        
        Args:
            interventions: List of intervention dictionaries
            
        Returns:
            Dictionary containing mechanism of action and target pathways
        """
        # Prepare intervention details for specialized analysis
        intervention_details = []
        for intervention in interventions:
            name = intervention.get('name', 'Unknown')
            type_val = intervention.get('type', 'Unknown')
            desc = intervention.get('description', 'Unknown')
            intervention_details.append(f"Name: {name}\nType: {type_val}\nDescription: {desc}")
        
        intervention_text = "\n\n".join(intervention_details)
        
        # Create specialized prompt for mechanism and targets
        prompt = f"""
You are a pharmaceutical scientist specializing in drug mechanisms and biological targets.
Analyze the following intervention descriptions from a clinical trial and extract:
1. Mechanism of Action
2. Target genes
3. Target proteins
4. Chemical compounds involved

INTERVENTIONS:
{intervention_text}

Focus only on these specific aspects. If any information is not explicitly mentioned or cannot be confidently inferred, mark it as "N/A".
Be specific and extract actual biological targets (gene names, protein names) rather than general concepts.

Respond in this JSON format:
```json
{{{{
  "mechanism_of_action": "Detailed description of how the intervention works",
  "target_pathway": {{{{
    "gene": ["Gene A", "Gene B"],
    "protein": ["Protein X", "Protein Y"],
    "chemical_compound": ["Compound Z"]
  }}}}
}}}}
```
"""
        
        # Call GPT-4o API with specialized prompt
        messages = [
            {"role": "system", "content": "You are a pharmaceutical scientist that extracts mechanism of action and target information."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_gpt4(messages, max_tokens=1000)
            
            # Extract JSON from the response
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
                mechanism_data = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                mechanism_data = json.loads(response)
            
            logger.info("Successfully extracted mechanism of action and targets")
            return mechanism_data
        except (json.JSONDecodeError, RuntimeError) as e:
            logger.warning(f"Failed to extract mechanism and targets: {e}")
            # Return default structure with N/A values if extraction fails
            return {
                "mechanism_of_action": "N/A",
                "target_pathway": {
                    "gene": "N/A",
                    "protein": "N/A",
                    "chemical_compound": "N/A"
                }
            }

    def extract_biomarkers(self, eligibility_criteria: Dict, outcomes: Dict) -> List[str]:
        """
        Extract biomarkers from eligibility criteria and outcomes.
        
        Args:
            eligibility_criteria: Dictionary of eligibility criteria
            outcomes: Dictionary of outcomes
            
        Returns:
            List of biomarkers
        """
        inclusion = eligibility_criteria.get('inclusion_criteria', [])
        exclusion = eligibility_criteria.get('exclusion_criteria', [])
        
        inclusion_text = "\n".join([f"- {criterion}" for criterion in inclusion])
        exclusion_text = "\n".join([f"- {criterion}" for criterion in exclusion])
        
        primary_outcomes = outcomes.get('primary_outcomes', [])
        secondary_outcomes = outcomes.get('secondary_outcomes', [])
        
        outcome_text = "\n".join([
            f"- {outcome.get('measure', '')}: {outcome.get('description', '')}"
            for outcome in primary_outcomes + secondary_outcomes
        ])
        
        # Create specialized prompt for biomarkers
        prompt = f"""
You are a clinical trial biomarker expert. Extract all biomarkers mentioned in the following clinical trial information.
Biomarkers can include genetic markers, protein markers, imaging markers, or any measurable biological indicators.

INCLUSION CRITERIA:
{inclusion_text}

EXCLUSION CRITERIA:
{exclusion_text}

OUTCOMES:
{outcome_text}

List only the specific biomarkers mentioned. If no biomarkers are mentioned, return ["N/A"].
Respond with a JSON array of biomarker names only:
```json
["Biomarker A", "Biomarker B", "Biomarker C"]
```
"""
        
        # Call GPT-4o API with specialized prompt
        messages = [
            {"role": "system", "content": "You are a biomarker extraction specialist."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_gpt4(messages, max_tokens=500)
            
            # Extract JSON from the response
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
                biomarkers = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                biomarkers = json.loads(response)
            
            logger.info("Successfully extracted biomarkers")
            return biomarkers
        except (json.JSONDecodeError, RuntimeError) as e:
            logger.warning(f"Failed to extract biomarkers: {e}")
            return ["N/A"]

    def validate_analysis(self, analyzed_data: Dict) -> Dict:
        """
        Validate the analysis against the original data to detect hallucinations or inaccuracies.
        
        Args:
            analyzed_data: Dictionary containing the structured analysis
            
        Returns:
            Dictionary containing the validation review
        """
        if not self.extracted_data:
            raise ValueError("No extracted data available for validation")
        
        # Convert the original data and analysis to strings for comparison
        original_json_str = json.dumps(self.extracted_data, indent=2)
        analysis_json_str = json.dumps(analyzed_data, indent=2)
        
        # Create prompt for validation
        prompt = f"""
You are a clinical trial data validation expert. Your task is to compare an AI-generated analysis of a clinical trial against the original trial data to identify any hallucinations, inaccuracies, or misrepresentations.

ORIGINAL CLINICAL TRIAL DATA:
```json
{original_json_str}
```

AI-GENERATED ANALYSIS:
```json
{analysis_json_str}
```

Please review the AI-generated analysis for accuracy and identify:
1. Any statements or information that is not supported by or directly contradicts the original data
2. Any potential hallucinations or fabricated details
3. Important information from the original data that was missed or under-emphasized
4. Any overly confident assertions made with limited evidence

Provide a detailed review of potential issues, specifying exactly where the analysis may be incorrect and what the correct information should be.
Format your response as a structured JSON with these sections:
- hallucinations: List specific inaccurate statements with corrections
- missing_info: Important information from original data that was omitted
- overall_assessment: Overall quality assessment (0-10) with rationale
- recommendations: Specific recommendations for improvement

```json
{{{{
  "hallucinations": [
    {{{{
      "field": "core_trial_metadata.status",
      "incorrect": "Completed",
      "correct": "Recruiting",
      "evidence": "Original data shows 'overall_status': 'Recruiting'"
    }}}},
    // additional issues...
  ],
  "missing_info": [
    {{{{
      "field": "scientific_content.intervention",
      "missing": "Dosage information is available in original data but missing in analysis",
      "evidence": "Original data includes 'dose' field with values"
    }}}},
    // additional missing items...
  ],
  "overall_assessment": {{{{
    "score": 7,
    "rationale": "Generally accurate but with some important discrepancies in status and intervention details"
  }}}},
  "recommendations": [
    "Verify trial status from original data",
    "Include complete dosage information from original data",
    // additional recommendations...
  ]
}}}}
```
"""
        
        # Call GPT-4o API
        messages = [
            {"role": "system", "content": "You are a clinical trial data validation expert that critically evaluates analyses for accuracy."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_gpt4(messages, max_tokens=2000)
            
            # Extract JSON from the response
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
                validation_results = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                validation_results = json.loads(response)
            
            logger.info("Successfully validated analysis against original data")
            return validation_results
        except (json.JSONDecodeError, RuntimeError) as e:
            logger.warning(f"Failed to validate analysis: {e}")
            # Return a basic structure if validation fails
            return {
                "hallucinations": [],
                "missing_info": [],
                "overall_assessment": {
                    "score": None,
                    "rationale": "Validation failed due to technical issues"
                },
                "recommendations": ["Review analysis manually due to validation failure"]
            }
    
    def correct_analysis(self, analyzed_data: Dict, validation_results: Dict) -> Dict:
        """
        Correct the analysis based on validation results.
        
        Args:
            analyzed_data: Dictionary containing the initial structured analysis
            validation_results: Dictionary containing validation review
            
        Returns:
            Dictionary containing the corrected analysis
        """
        if not self.extracted_data:
            raise ValueError("No extracted data available for correction")
        
        # Convert to strings for the prompt
        original_json_str = json.dumps(self.extracted_data, indent=2)
        analysis_json_str = json.dumps(analyzed_data, indent=2)
        validation_json_str = json.dumps(validation_results, indent=2)
        
        # Create prompt for correction
        prompt = f"""
You are a clinical trial data correction expert. Your task is to correct an AI-generated analysis based on a validation review and the original trial data.

ORIGINAL CLINICAL TRIAL DATA:
```json
{original_json_str}
```

INITIAL AI-GENERATED ANALYSIS:
```json
{analysis_json_str}
```

VALIDATION REVIEW (identifying issues):
```json
{validation_json_str}
```

Please create a corrected version of the analysis that:
1. Fixes all hallucinations and inaccuracies identified in the validation review
2. Adds any important missing information from the original data
3. Makes corrections based on the evidence in the original trial data
4. Maintains the same structure as the original analysis

Important: 
- Every field in your corrected analysis MUST be supported by evidence in the original data
- Use "N/A" for any fields where reliable information is not available in the original data
- Remove any statements that are not supported by the original data
- Ensure all corrections are factual and directly traceable to the original data

Respond with a complete corrected JSON structure that follows the same format as the initial analysis but addresses all the issues:

```json
{{{{
  "core_trial_metadata": {{{{...}}}},
  "scientific_content": {{{{...}}}},
  "patient_related_information": {{{{...}}}},
  "operational_aspects": {{{{...}}}}
}}}}
```
"""
        
        # Call GPT-4o API
        messages = [
            {"role": "system", "content": "You are a clinical trial data correction expert that ensures analyses are accurate and fact-based."},
            {"role": "user", "content": prompt}
        ]
        
        try:
            response = self._call_gpt4(messages, max_tokens=3000)
            
            # Extract JSON from the response
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
                corrected_data = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                corrected_data = json.loads(response)
            
            logger.info("Successfully corrected analysis based on validation review")
            return corrected_data
        except (json.JSONDecodeError, RuntimeError) as e:
            logger.warning(f"Failed to correct analysis: {e}")
            # Return the original analysis if correction fails
            return analyzed_data

    def analyze_trial_data(self) -> Dict:
        """
        Analyze trial data with comprehensive structured output.
        
        Returns:
            Dictionary containing structured trial analysis
            
        Raises:
            ValueError: If there is no extracted data or the analysis fails
        """
        if not self.extracted_data:
            self.load_data()
        
        if not self.extracted_data:
            raise ValueError(f"Failed to load data from {self.input_file}")
        
        # Check for API key
        if not openai.api_key:
            raise ValueError("No OpenAI API key provided. Set OPENAI_API_KEY environment variable or provide it as an argument.")
            
        basic_info = self.extracted_data.get('basic_info', {})
        eligibility = self.extracted_data.get('eligibility_criteria', {})
        interventions = self.extracted_data.get('interventions', [])
        outcomes = self.extracted_data.get('outcomes', {})
        design_info = self.extracted_data.get('design_info', {})
        locations = self.extracted_data.get('locations', [])
        
        # Step 1: Extract mechanism, targets, and biomarkers with specialized prompts
        mechanism_data = self.extract_mechanism_and_targets(interventions)
        biomarkers = self.extract_biomarkers(eligibility, outcomes)
        
        # Prepare inclusion and exclusion criteria
        inclusion_criteria = eligibility.get('inclusion_criteria', [])
        exclusion_criteria = eligibility.get('exclusion_criteria', [])
        
        inclusion_text = "\n".join([f"- {criterion}" for criterion in inclusion_criteria])
        exclusion_text = "\n".join([f"- {criterion}" for criterion in exclusion_criteria])
        
        # Prepare intervention text
        intervention_text = ""
        for idx, intervention in enumerate(interventions, 1):
            name = intervention.get('name', 'Unknown')
            type_val = intervention.get('type', 'Unknown')
            desc = intervention.get('description', 'No description')
            intervention_text += f"{idx}. {name} ({type_val}): {desc}\n"
        
        # Prepare outcome text
        primary_outcomes = outcomes.get('primary_outcomes', [])
        secondary_outcomes = outcomes.get('secondary_outcomes', [])
        
        primary_outcome_text = "\n".join([f"- {outcome.get('measure', 'Unknown')}: {outcome.get('description', 'No description')} (Time frame: {outcome.get('time_frame', 'Not specified')})" 
                                          for outcome in primary_outcomes])
        
        secondary_outcome_text = "\n".join([f"- {outcome.get('measure', 'Unknown')}: {outcome.get('description', 'No description')} (Time frame: {outcome.get('time_frame', 'Not specified')})" 
                                            for outcome in secondary_outcomes])
        
        # Create comprehensive prompt for structured analysis
        prompt = f"""
You are a clinical trial data analyst. Analyze the following clinical trial information and provide a comprehensive structured analysis.

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

SECONDARY OUTCOMES:
{secondary_outcome_text}

INCLUSION CRITERIA:
{inclusion_text}

EXCLUSION CRITERIA:
{exclusion_text}

I need a comprehensive structured analysis of this clinical trial with all the following fields organized into sections as shown below.
Use "N/A" for any fields where information is not available:

1. Core Trial Metadata:
   - NCT ID
   - Status (recruiting, completed, terminated, etc.)
   - Dates (registration, start, completion, last update)
   - Phase
   - Study Type (interventional, observational, expanded access)
   - Enrollment (target and actual counts)
   - Sponsor/Collaborators

2. Scientific Content:
   - Intervention details (drug name, dosage, route of administration)
   - Study Design (randomization, blinding, control types)
   - Arms/Groups (number, types, descriptions)
   - Primary/Secondary Outcomes (with endpoints and timeframes)

3. Patient-Related Information:
   - Eligibility Criteria (structured decomposition of complex criteria)
   - Demographics (age, sex, other demographic requirements)
   - Disease Characteristics (subtypes, stages, severity)
   - Prior Treatments (required or excluded previous therapies)

4. Operational Aspects:
   - Locations (trial sites, countries, regions)
   - Investigators (site PIs and leadership teams)
   - Enrollment Status (site-specific recruitment progress)
   - IPD Sharing (data sharing commitments and platforms)

IMPORTANT: Only include information that is explicitly stated in or can be directly inferred from the provided clinical trial data. Do not add speculative or unsupported details. Use "N/A" for any fields where information is not available.

Respond in this structured JSON format with these exact sections and fields. If information for a field is not available, use "N/A" as the value:

```json
{{{{
  "core_trial_metadata": {{{{
    "nct_id": "NCT12345678",
    "status": "Recruiting",
    "dates": {{{{
      "registration": "2023-01-01",
      "start": "2023-03-15",
      "completion": "2024-12-31",
      "last_update": "2023-05-20"
    }}}},
    "phase": "Phase 2",
    "study_type": "Interventional",
    "enrollment": {{{{
      "target": 100,
      "actual": 45
    }}}},
    "sponsor_collaborators": {{{{
      "primary_sponsor": "University Medical Center",
      "collaborators": ["Pharmaceutical Company A", "Research Institute B"]
    }}}}
  }}}},
  "scientific_content": {{{{
    "intervention": [
      {{{{
        "name": "Drug X",
        "type": "Drug",
        "description": "Small molecule inhibitor",
        "dosage": "100mg twice daily",
        "route": "Oral"
      }}}}
    ],
    "study_design": {{{{
      "allocation": "Randomized",
      "intervention_model": "Parallel Assignment",
      "masking": "Double-blind",
      "primary_purpose": "Treatment"
    }}}},
    "arms_groups": [
      {{{{
        "arm_name": "Experimental",
        "arm_type": "Experimental",
        "description": "Participants receive Drug X"
      }}}},
      {{{{
        "arm_name": "Placebo",
        "arm_type": "Placebo Comparator",
        "description": "Participants receive placebo"
      }}}}
    ],
    "outcomes": {{{{
      "primary": [
        {{{{
          "measure": "Overall Survival",
          "description": "Time from randomization to death from any cause",
          "timeframe": "Up to 24 months"
        }}}}
      ],
      "secondary": [
        {{{{
          "measure": "Progression-Free Survival",
          "description": "Time from randomization to disease progression",
          "timeframe": "Up to 12 months"
        }}}}
      ]
    }}}}
  }}}},
  "patient_related_information": {{{{
    "eligibility_criteria": {{{{
      "inclusion": [
        "Adults aged 18 years or older",
        "Histologically confirmed diagnosis"
      ],
      "exclusion": [
        "Prior treatment with similar agents",
        "Significant comorbidities"
      ]
    }}}},
    "demographics": {{{{
      "age": {{{{
        "min": 18,
        "max": null,
        "description": "18 years and older"
      }}}},
      "sex": "All",
      "other": ["No restrictions based on race or ethnicity"]
    }}}},
    "disease_characteristics": {{{{
      "subtypes": ["Subtype A", "Subtype B"],
      "stages": ["Stage III", "Stage IV"],
      "severity": "Advanced disease"
    }}}},
    "prior_treatments": {{{{
      "required": ["First-line therapy with standard of care"],
      "excluded": ["Prior experimental treatments"]
    }}}}
  }}}},
  "operational_aspects": {{{{
    "locations": [
      {{{{
        "facility": "University Hospital",
        "city": "Boston",
        "state": "Massachusetts",
        "country": "United States",
        "status": "Recruiting"
      }}}}
    ],
    "investigators": [
      {{{{
        "name": "John Smith, MD",
        "role": "Principal Investigator",
        "facility": "University Hospital"
      }}}}
    ],
    "enrollment_status": {{{{
      "overall": "Recruiting",
      "site_specific": [
        {{{{
          "facility": "University Hospital",
          "status": "Recruiting",
          "participants_enrolled": 20
        }}}}
      ]
    }}}},
    "ipd_sharing": {{{{
      "plan": "Yes",
      "description": "Data will be shared through platform X after study completion"
    }}}}
  }}}}
}}}}
```
"""
        
        # Call GPT-4o API for initial analysis
        messages = [
            {"role": "system", "content": "You are a clinical trial analyst that creates comprehensive structured summaries of clinical trials."},
            {"role": "user", "content": prompt}
        ]
        
        response = self._call_gpt4(messages, max_tokens=3000)
        
        if not response:
            raise ValueError(f"Empty response from LLM for trial {basic_info.get('nct_id', 'Unknown')}")
        
        # Extract JSON from the response
        try:
            # Find the JSON part within the response (between ```json and ```)
            if "```json" in response and "```" in response.split("```json")[1]:
                json_str = response.split("```json")[1].split("```")[0].strip()
                initial_analyzed_data = json.loads(json_str)
            else:
                # Try to parse the entire response as JSON
                initial_analyzed_data = json.loads(response)
            
            # Merge specialized extracted data into the main analysis
            if "scientific_content" not in initial_analyzed_data:
                initial_analyzed_data["scientific_content"] = {}
                
            # Add the specialized mechanism and target data to the analysis
            initial_analyzed_data["scientific_content"]["mechanism_of_action"] = mechanism_data.get("mechanism_of_action", "N/A")
            initial_analyzed_data["scientific_content"]["target_pathway"] = mechanism_data.get("target_pathway", {
                "gene": "N/A",
                "protein": "N/A",
                "chemical_compound": "N/A"
            })
            
            # Add biomarkers information
            initial_analyzed_data["scientific_content"]["biomarkers"] = biomarkers
            
            logger.info(f"Successfully created initial analysis for {basic_info.get('nct_id', 'Unknown')}")
            
            # Step 2: Validate the analysis for hallucinations and inaccuracies
            logger.info("Validating analysis against original data...")
            validation_results = self.validate_analysis(initial_analyzed_data)
            
            # Step 3: Correct the analysis based on validation results
            logger.info("Correcting analysis based on validation results...")
            final_analyzed_data = self.correct_analysis(initial_analyzed_data, validation_results)
            
            # Store both the structured analysis, validation results, and original data
            self.analyzed_data = {
                "analyzed_data": final_analyzed_data,
                "validation_results": validation_results,
                "original_data": self.extracted_data,
                "llm_responses": {
                    "initial_analysis": response
                }
            }
            
            logger.info(f"Successfully completed full analysis with validation and correction for {basic_info.get('nct_id', 'Unknown')}")
            
        except json.JSONDecodeError as e:
            error_msg = f"Failed to parse analysis JSON: {e}"
            logger.error(error_msg)
            raise ValueError(error_msg) from e
        
        return self.analyzed_data
    
    def save_analyzed_data(self, output_file: str) -> None:
        """
        Save the analyzed data to a JSON file.
        
        Args:
            output_file: Path to the output JSON file
            
        Raises:
            ValueError: If no analyzed data is available
        """
        if not self.analyzed_data:
            raise ValueError("No analyzed data available. Run analyze_trial_data() first.")
        
        # Create output directory structure
        output_dir = os.path.dirname(output_file)
        os.makedirs(output_dir, exist_ok=True)
        
        # Create debug directory if in debug mode
        debug_dir = None
        if self.debug_mode:
            debug_dir = os.path.join(output_dir, "debug")
            os.makedirs(debug_dir, exist_ok=True)
        
        try:
            # Save the final corrected analysis to the main output file
            final_data = {"analyzed_data": self.analyzed_data.get("analyzed_data", {})}
            
            # Use a temporary file to avoid file access issues
            temp_output_file = f"{output_file}.tmp"
            with open(temp_output_file, 'w', encoding='utf-8') as f:
                json.dump(final_data, f, indent=2)
            
            # Rename the temporary file to the final file
            if os.path.exists(output_file):
                os.remove(output_file)
            os.rename(temp_output_file, output_file)
            
            logger.info(f"Successfully saved final analyzed data to {output_file}")
            
            # Save the full data with validation results to debug directory if in debug mode
            if self.debug_mode and debug_dir:
                # Save extracted data
                extracted_file = os.path.join(debug_dir, os.path.basename(self.input_file))
                
                # Use a temporary file for extracted data
                temp_extracted_file = f"{extracted_file}.tmp"
                shutil.copy2(self.input_file, temp_extracted_file)
                
                # Rename the temporary file
                if os.path.exists(extracted_file):
                    os.remove(extracted_file)
                os.rename(temp_extracted_file, extracted_file)
                
                logger.info(f"Saved extracted data to {extracted_file}")
                
                # Save full analysis with validation results
                debug_file = os.path.join(debug_dir, os.path.basename(output_file).replace('.json', '_full.json'))
                
                # Use a temporary file for debug data
                temp_debug_file = f"{debug_file}.tmp"
                with open(temp_debug_file, 'w', encoding='utf-8') as f:
                    json.dump(self.analyzed_data, f, indent=2)
                
                # Rename the temporary file
                if os.path.exists(debug_file):
                    os.remove(debug_file)
                os.rename(temp_debug_file, debug_file)
                
                logger.info(f"Saved full analysis with validation results to {debug_file}")
        except Exception as e:
            error_msg = f"Failed to save data to {output_file}: {e}"
            logger.error(error_msg)
            raise RuntimeError(error_msg) from e


def clean_output_directory(output_dir: str) -> None:
    """
    Clean the output directory by removing all files and subdirectories.
    
    Args:
        output_dir: Directory to clean
    """
    if os.path.exists(output_dir):
        for item in os.listdir(output_dir):
            item_path = os.path.join(output_dir, item)
            try:
                if os.path.isfile(item_path):
                    os.unlink(item_path)
                elif os.path.isdir(item_path):
                    shutil.rmtree(item_path)
                logger.info(f"Removed {item_path}")
            except Exception as e:
                logger.warning(f"Failed to remove {item_path}: {e}")
    else:
        os.makedirs(output_dir, exist_ok=True)
    
    logger.info(f"Cleaned output directory: {output_dir}")


def main():
    """Main function to run the clinical trial analyzer."""
    parser = argparse.ArgumentParser(description='Analyze clinical trial data using OpenAI GPT-4o API.')
    parser.add_argument('input_file', help='Path to the input JSON file with extracted clinical trial data')
    parser.add_argument('-o', '--output', help='Path to the output analyzed JSON file')
    parser.add_argument('-k', '--api_key', help='OpenAI API key (can also be set via OPENAI_API_KEY environment variable)')
    parser.add_argument('-d', '--debug', action='store_true', help='Enable debug mode to save intermediate data')
    parser.add_argument('--clean', action='store_true', help='Clean output directory before processing')
    
    args = parser.parse_args()
    
    # Set default output filename if not provided
    if not args.output:
        input_basename = os.path.basename(args.input_file)
        output_basename = os.path.splitext(input_basename)[0] + '_analyzed.json'
        args.output = os.path.join(os.path.dirname(args.input_file), output_basename)
    
    # Clean output directory if requested
    output_dir = os.path.dirname(args.output)
    if args.clean and output_dir:
        clean_output_directory(output_dir)
    
    # Analyze the extracted data
    analyzer = ClinicalTrialAnalyzer(args.input_file, args.api_key, args.debug)
    analyzer.analyze_trial_data()
    analyzer.save_analyzed_data(args.output)
    
    # Print basic information about the analysis
    print(f"Analyzed data from {args.input_file}")
    print(f"Saved analyzed data to {args.output}")
    if args.debug:
        debug_dir = os.path.join(os.path.dirname(args.output), "debug")
        print(f"Debug data saved to {debug_dir}")


if __name__ == '__main__':
    main() 