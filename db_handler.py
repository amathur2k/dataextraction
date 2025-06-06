#!/usr/bin/env python3
"""
Database Handler for Clinical Trial Analysis Data

This module provides functionality to store analyzed clinical trial data in PostgreSQL.
"""

import psycopg2
import json
import logging
from typing import Dict, Any, Optional
from datetime import datetime

logger = logging.getLogger(__name__)

class ClinicalTrialDatabaseHandler:
    """Handler for PostgreSQL database operations for clinical trial data."""
    
    def __init__(self, host='localhost', port=5432, database=None, user='postgres', password='admin'):
        """
        Initialize database handler.
        
        Args:
            host: Database host
            port: Database port
            database: Database name
            user: Database user
            password: Database password
        """
        self.connection_params = {
            'host': host,
            'port': port,
            'database': database,
            'user': user,
            'password': password
        }
        self.connection = None
    
    def connect(self):
        """Establish database connection."""
        try:
            self.connection = psycopg2.connect(**self.connection_params)
            logger.info(f"Connected to PostgreSQL database {self.connection_params['database']}")
        except psycopg2.Error as e:
            logger.error(f"Failed to connect to database: {e}")
            raise
    
    def disconnect(self):
        """Close database connection."""
        if self.connection:
            self.connection.close()
            self.connection = None
            logger.info("Database connection closed")
    
    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()
    
    def _safe_get_nested(self, data: Dict[Any, Any], path: str, default=None):
        """
        Safely get nested dictionary values using dot notation.
        
        Args:
            data: Dictionary to search
            path: Dot-separated path (e.g., 'analyzed_data.core_trial_metadata.nct_id')
            default: Default value if path not found
        
        Returns:
            Value at path or default
        """
        try:
            keys = path.split('.')
            value = data
            for key in keys:
                value = value[key]
            return value
        except (KeyError, TypeError):
            return default
    
    def _parse_age(self, age_info: Dict[str, Any]) -> tuple:
        """
        Parse age information from demographics.
        
        Args:
            age_info: Age information dictionary
        
        Returns:
            Tuple of (min_age, max_age)
        """
        min_age = None
        max_age = None
        
        if isinstance(age_info, dict):
            min_age = age_info.get('min')
            max_age = age_info.get('max')
            
            # Handle string values
            if isinstance(min_age, str) and min_age.isdigit():
                min_age = int(min_age)
            elif isinstance(min_age, str):
                min_age = None
                
            if isinstance(max_age, str) and max_age.isdigit():
                max_age = int(max_age)
            elif isinstance(max_age, str):
                max_age = None
        
        return min_age, max_age
    
    def _clean_text_field(self, value: Any, max_length: Optional[int] = None) -> Optional[str]:
        """
        Clean and truncate text fields.
        
        Args:
            value: Value to clean
            max_length: Maximum length to truncate to
        
        Returns:
            Cleaned string or None
        """
        if value is None or value == "N/A":
            return None
        
        text = str(value).strip()
        if not text or text == "N/A":
            return None
        
        if max_length and len(text) > max_length:
            text = text[:max_length]
        
        return text
    
    def insert_analysis_data(self, analysis_file_path: str, table_name: str = 'myclinicaltrials') -> bool:
        """
        Insert analyzed clinical trial data into the database.
        
        Args:
            analysis_file_path: Path to the analysis JSON file
            table_name: Name of the database table
        
        Returns:
            True if successful, False otherwise
        """
        if not self.connection:
            raise Exception("Database connection not established. Call connect() first.")
        
        try:
            # Load the analysis data
            with open(analysis_file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Extract analyzed data section
            analyzed_data = data.get('analyzed_data', {})
            core_metadata = analyzed_data.get('core_trial_metadata', {})
            scientific_content = analyzed_data.get('scientific_content', {})
            patient_info = analyzed_data.get('patient_related_information', {})
            operational = analyzed_data.get('operational_aspects', {})
            
            # Parse demographics
            demographics = patient_info.get('demographics', {})
            age_info = demographics.get('age', {})
            min_age, max_age = self._parse_age(age_info)
            
            # Parse enrollment
            enrollment = core_metadata.get('enrollment', {})
            target_enrollment = enrollment.get('target')
            actual_enrollment = enrollment.get('actual')
            
            # Convert enrollment to integers if possible
            if isinstance(target_enrollment, str) and target_enrollment.isdigit():
                target_enrollment = int(target_enrollment)
            elif target_enrollment == "N/A" or not target_enrollment:
                target_enrollment = None
                
            if isinstance(actual_enrollment, str) and actual_enrollment.isdigit():
                actual_enrollment = int(actual_enrollment)
            elif actual_enrollment == "N/A" or not actual_enrollment:
                actual_enrollment = None
            
            # Parse dates
            dates = core_metadata.get('dates', {})
            
            # Prepare SQL insert statement
            insert_sql = f"""
            INSERT INTO {table_name} (
                nct_id, status, phase, study_type,
                registration_date, start_date, completion_date, last_update_date,
                target_enrollment, actual_enrollment,
                primary_sponsor, collaborators,
                allocation, intervention_model, masking, primary_purpose,
                interventions, arms_groups, primary_outcomes, secondary_outcomes,
                mechanism_and_targets, biomarkers,
                inclusion_criteria, exclusion_criteria,
                min_age, max_age, eligible_sex, demographics_other,
                disease_subtypes, disease_stages, disease_severity,
                required_prior_treatments, excluded_prior_treatments,
                locations, investigators, enrollment_status, ipd_sharing,
                analysis_score, analysis_rationale, missing_info, recommendations,
                original_data, analyzed_data
            ) VALUES (
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s,
                %s, %s,
                %s, %s, %s, %s,
                %s, %s, %s, %s,
                %s, %s
            ) ON CONFLICT (nct_id) DO UPDATE SET
                status = EXCLUDED.status,
                phase = EXCLUDED.phase,
                study_type = EXCLUDED.study_type,
                registration_date = EXCLUDED.registration_date,
                start_date = EXCLUDED.start_date,
                completion_date = EXCLUDED.completion_date,
                last_update_date = EXCLUDED.last_update_date,
                target_enrollment = EXCLUDED.target_enrollment,
                actual_enrollment = EXCLUDED.actual_enrollment,
                primary_sponsor = EXCLUDED.primary_sponsor,
                collaborators = EXCLUDED.collaborators,
                allocation = EXCLUDED.allocation,
                intervention_model = EXCLUDED.intervention_model,
                masking = EXCLUDED.masking,
                primary_purpose = EXCLUDED.primary_purpose,
                interventions = EXCLUDED.interventions,
                arms_groups = EXCLUDED.arms_groups,
                primary_outcomes = EXCLUDED.primary_outcomes,
                secondary_outcomes = EXCLUDED.secondary_outcomes,
                mechanism_and_targets = EXCLUDED.mechanism_and_targets,
                biomarkers = EXCLUDED.biomarkers,
                inclusion_criteria = EXCLUDED.inclusion_criteria,
                exclusion_criteria = EXCLUDED.exclusion_criteria,
                min_age = EXCLUDED.min_age,
                max_age = EXCLUDED.max_age,
                eligible_sex = EXCLUDED.eligible_sex,
                demographics_other = EXCLUDED.demographics_other,
                disease_subtypes = EXCLUDED.disease_subtypes,
                disease_stages = EXCLUDED.disease_stages,
                disease_severity = EXCLUDED.disease_severity,
                required_prior_treatments = EXCLUDED.required_prior_treatments,
                excluded_prior_treatments = EXCLUDED.excluded_prior_treatments,
                locations = EXCLUDED.locations,
                investigators = EXCLUDED.investigators,
                enrollment_status = EXCLUDED.enrollment_status,
                ipd_sharing = EXCLUDED.ipd_sharing,
                analysis_score = EXCLUDED.analysis_score,
                analysis_rationale = EXCLUDED.analysis_rationale,
                missing_info = EXCLUDED.missing_info,
                recommendations = EXCLUDED.recommendations,
                original_data = EXCLUDED.original_data,
                analyzed_data = EXCLUDED.analyzed_data,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            # Prepare values
            values = (
                # Core metadata
                core_metadata.get('nct_id'),
                self._clean_text_field(core_metadata.get('status')),
                self._clean_text_field(core_metadata.get('phase')),
                self._clean_text_field(core_metadata.get('study_type')),
                
                # Dates
                self._clean_text_field(dates.get('registration')),
                self._clean_text_field(dates.get('start')),
                self._clean_text_field(dates.get('completion')),
                self._clean_text_field(dates.get('last_update')),
                
                # Enrollment
                target_enrollment,
                actual_enrollment,
                
                # Sponsors
                self._clean_text_field(core_metadata.get('sponsor_collaborators', {}).get('primary_sponsor')),
                self._clean_text_field(core_metadata.get('sponsor_collaborators', {}).get('collaborators')),
                
                # Study design
                self._clean_text_field(scientific_content.get('study_design', {}).get('allocation')),
                self._clean_text_field(scientific_content.get('study_design', {}).get('intervention_model')),
                self._clean_text_field(scientific_content.get('study_design', {}).get('masking')),
                self._clean_text_field(scientific_content.get('study_design', {}).get('primary_purpose')),
                
                # JSON fields
                json.dumps(scientific_content.get('intervention', [])),
                json.dumps(scientific_content.get('arms_groups', [])),
                json.dumps(scientific_content.get('outcomes', {}).get('primary', [])),
                json.dumps(scientific_content.get('outcomes', {}).get('secondary', [])),
                json.dumps(scientific_content.get('mechanism_and_targets', [])),
                json.dumps(scientific_content.get('biomarkers', [])),
                
                # Eligibility
                json.dumps(patient_info.get('eligibility_criteria', {}).get('inclusion', [])),
                json.dumps(patient_info.get('eligibility_criteria', {}).get('exclusion', [])),
                
                # Demographics
                min_age,
                max_age,
                self._clean_text_field(demographics.get('sex')),
                json.dumps(demographics.get('other', [])),
                
                # Disease characteristics
                json.dumps(patient_info.get('disease_characteristics', {}).get('subtypes', [])),
                json.dumps(patient_info.get('disease_characteristics', {}).get('stages', [])),
                self._clean_text_field(patient_info.get('disease_characteristics', {}).get('severity')),
                
                # Prior treatments
                json.dumps(patient_info.get('prior_treatments', {}).get('required', [])),
                json.dumps(patient_info.get('prior_treatments', {}).get('excluded', [])),
                
                # Operational
                json.dumps(operational.get('locations', [])),
                json.dumps(operational.get('investigators', [])),
                json.dumps(operational.get('enrollment_status', {})),
                json.dumps(operational.get('ipd_sharing', {})),
                
                # Quality assessment (from validation section if available)
                data.get('validation', {}).get('overall_assessment', {}).get('score'),
                self._clean_text_field(data.get('validation', {}).get('overall_assessment', {}).get('rationale')),
                json.dumps(data.get('validation', {}).get('missing_info', [])),
                json.dumps(data.get('validation', {}).get('recommendations', [])),
                
                # Full data
                json.dumps(data.get('original_data', {})),
                json.dumps(analyzed_data)
            )
            
            # Execute insert
            with self.connection.cursor() as cursor:
                cursor.execute(insert_sql, values)
                self.connection.commit()
            
            nct_id = core_metadata.get('nct_id', 'Unknown')
            logger.info(f"Successfully inserted/updated trial data for {nct_id} in table {table_name}")
            return True
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            logger.error(f"Failed to insert analysis data: {e}")
            return False
    
    def check_table_exists(self, table_name: str) -> bool:
        """
        Check if the specified table exists in the database.
        
        Args:
            table_name: Name of the table to check
        
        Returns:
            True if table exists, False otherwise
        """
        if not self.connection:
            raise Exception("Database connection not established. Call connect() first.")
        
        try:
            with self.connection.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS (
                        SELECT FROM information_schema.tables 
                        WHERE table_name = %s
                    );
                """, (table_name,))
                
                return cursor.fetchone()[0]
        except Exception as e:
            logger.error(f"Error checking if table exists: {e}")
            return False 