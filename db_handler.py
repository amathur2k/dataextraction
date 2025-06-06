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
            
            # Extract main sections
            analyzed_data = data.get('analyzed_data', {})
            original_data = data.get('original_data', {})
            
            # Core sections from analyzed data
            core_metadata = analyzed_data.get('core_trial_metadata', {})
            scientific_content = analyzed_data.get('scientific_content', {})
            patient_info = analyzed_data.get('patient_related_information', {})
            operational = analyzed_data.get('operational_aspects', {})
            
            # Extract from original data for additional fields
            basic_info = original_data.get('basic_info', {})
            
            # ========== CORE TRIAL METADATA ==========
            nct_id = core_metadata.get('nct_id') or basic_info.get('nct_id')
            status = self._clean_text_field(core_metadata.get('status') or basic_info.get('overall_status'))
            
            # Dates
            dates = core_metadata.get('dates', {})
            registration_date = self._clean_text_field(dates.get('registration'))
            start_date = self._clean_text_field(dates.get('start') or basic_info.get('start_date'))
            completion_date = self._clean_text_field(dates.get('completion') or basic_info.get('primary_completion_date'))
            last_update_date = self._clean_text_field(dates.get('last_update'))
            study_first_submit_date = self._clean_text_field(dates.get('study_first_submit_date') or basic_info.get('study_first_submit_date'))
            primary_completion_date = self._clean_text_field(basic_info.get('primary_completion_date'))
            
            # Basic metadata
            phase = self._clean_text_field(core_metadata.get('phase') or basic_info.get('phases', [None])[0] if basic_info.get('phases') else None)
            study_type = self._clean_text_field(core_metadata.get('study_type') or basic_info.get('study_type'))
            
            # Enrollment
            enrollment = core_metadata.get('enrollment', {})
            target_enrollment = self._parse_integer(enrollment.get('target'))
            actual_enrollment = self._parse_integer(enrollment.get('actual') or basic_info.get('enrollment'))
            enrollment_type = self._clean_text_field(basic_info.get('enrollment_type'))
            
            # Sponsors
            sponsors = core_metadata.get('sponsor_collaborators', {})
            primary_sponsor = self._clean_text_field(sponsors.get('primary_sponsor') or basic_info.get('lead_sponsor'))
            primary_sponsor_class = self._clean_text_field(basic_info.get('lead_sponsor_class'))
            lead_sponsor = self._clean_text_field(basic_info.get('lead_sponsor'))
            
            # Process collaborators
            collaborators_raw = sponsors.get('collaborators')
            if isinstance(collaborators_raw, str) and collaborators_raw not in ['N/A', 'None', '']:
                collaborators = [collaborators_raw]
            elif isinstance(collaborators_raw, list):
                collaborators = collaborators_raw
            else:
                collaborators = []
            
            # Titles
            brief_title = self._clean_text_field(basic_info.get('brief_title'))
            official_title = self._clean_text_field(basic_info.get('official_title'))
            
            # ========== SCIENTIFIC CONTENT ==========
            study_design = scientific_content.get('study_design', {})
            allocation = self._clean_text_field(study_design.get('allocation') or basic_info.get('allocation'))
            intervention_model = self._clean_text_field(study_design.get('intervention_model') or basic_info.get('intervention_model'))
            intervention_model_description = self._clean_text_field(basic_info.get('intervention_model_description'))
            masking = self._clean_text_field(study_design.get('masking') or basic_info.get('masking'))
            masking_description = self._clean_text_field(basic_info.get('masking_description'))
            primary_purpose = self._clean_text_field(study_design.get('primary_purpose') or basic_info.get('primary_purpose'))
            
            # Interventions processing
            interventions_raw = scientific_content.get('intervention', [])
            interventions = self._process_interventions(interventions_raw)
            
            # Extract specific intervention data
            intervention_types = self._extract_intervention_types(interventions_raw)
            drug_names = self._extract_drug_names(interventions_raw)
            dosages = self._extract_dosages(interventions_raw)
            administration_routes = self._extract_administration_routes(interventions_raw)
            
            # Mechanism and targets
            mechanisms_raw = scientific_content.get('mechanism_and_targets', [])
            mechanisms_of_action = self._extract_mechanisms_of_action(mechanisms_raw)
            target_pathways = self._extract_target_pathways(mechanisms_raw)
            target_genes = self._extract_target_genes(mechanisms_raw)
            target_proteins = self._extract_target_proteins(mechanisms_raw)
            target_chemical_compounds = self._extract_target_chemical_compounds(mechanisms_raw)
            
            # Biomarkers
            biomarkers_raw = scientific_content.get('biomarkers', [])
            biomarkers = self._process_biomarkers(biomarkers_raw)
            biomarker_types = self._extract_biomarker_types(biomarkers_raw)
            
            # Arms and outcomes
            arms_groups = scientific_content.get('arms_groups', [])
            number_of_arms = len(arms_groups) if arms_groups else None
            
            outcomes = scientific_content.get('outcomes', {})
            primary_outcomes = outcomes.get('primary', [])
            secondary_outcomes = outcomes.get('secondary', [])
            other_outcomes = outcomes.get('other', [])
            
            # ========== PATIENT-RELATED INFORMATION ==========
            eligibility = patient_info.get('eligibility_criteria', {})
            inclusion_criteria = eligibility.get('inclusion', [])
            exclusion_criteria = eligibility.get('exclusion', [])
            
            # Structured eligibility (decompose complex criteria)
            eligibility_criteria_structured = self._structure_eligibility_criteria(inclusion_criteria, exclusion_criteria)
            
            # Demographics
            demographics = patient_info.get('demographics', {})
            age_info = demographics.get('age', {})
            min_age, max_age = self._parse_age(age_info)
            eligible_sex = self._clean_text_field(demographics.get('sex'))
            healthy_volunteers = self._clean_text_field(basic_info.get('healthy_volunteers'))
            demographics_other = demographics.get('other', [])
            
            # Disease characteristics
            disease_chars = patient_info.get('disease_characteristics', {})
            conditions = basic_info.get('conditions', [])
            disease_subtypes = disease_chars.get('subtypes', [])
            disease_stages = disease_chars.get('stages', [])
            disease_severity = self._clean_text_field(disease_chars.get('severity'))
            keywords = basic_info.get('keywords', [])
            
            # Prior treatments
            prior_treatments = patient_info.get('prior_treatments', {})
            required_prior_treatments = prior_treatments.get('required', [])
            excluded_prior_treatments = prior_treatments.get('excluded', [])
            
            # ========== OPERATIONAL ASPECTS ==========
            # Locations and geography
            locations_raw = operational.get('locations', [])
            locations = self._process_locations(locations_raw)
            countries = self._extract_countries(locations_raw)
            facility_names = self._extract_facility_names(locations_raw)
            facility_status = self._extract_facility_status(locations_raw)
            
            # Investigators and officials
            investigators = operational.get('investigators', [])
            overall_officials = basic_info.get('overall_officials', [])
            responsible_party = basic_info.get('responsible_party', {})
            
            # Enrollment status
            enrollment_status = operational.get('enrollment_status', {})
            site_recruitment_status = self._extract_site_recruitment_status(locations_raw)
            
            # IPD Sharing
            ipd_sharing_raw = operational.get('ipd_sharing', {})
            ipd_sharing = ipd_sharing_raw
            ipd_sharing_plan = self._clean_text_field(basic_info.get('ipd_sharing_plan'))
            ipd_sharing_time_frame = self._clean_text_field(basic_info.get('ipd_sharing_time_frame'))
            ipd_sharing_access_criteria = self._clean_text_field(basic_info.get('ipd_sharing_access_criteria'))
            ipd_sharing_url = self._clean_text_field(basic_info.get('ipd_sharing_url'))
            
            # Contact information
            central_contacts = basic_info.get('central_contacts', [])
            overall_contact = basic_info.get('overall_contact', {})
            overall_contact_backup = basic_info.get('overall_contact_backup', {})
            
            # References and documentation
            trial_references = basic_info.get('references', [])
            results_references = basic_info.get('results_references', [])
            provided_documents = basic_info.get('provided_documents', [])
            
            # Study monitoring
            oversight_info = basic_info.get('oversight_info', {})
            data_monitoring_committee = self._clean_text_field(basic_info.get('data_monitoring_committee'))
            
            # Additional metadata
            why_stopped = self._clean_text_field(basic_info.get('why_stopped'))
            has_expanded_access = self._clean_text_field(basic_info.get('has_expanded_access'))
            expanded_access_info = basic_info.get('expanded_access_info', {})
            
            # Prepare comprehensive SQL insert statement
            insert_sql = f"""
            INSERT INTO {table_name} (
                nct_id, status, registration_date, start_date, completion_date, last_update_date,
                study_first_submit_date, primary_completion_date, phase, study_type,
                target_enrollment, actual_enrollment, enrollment_type,
                primary_sponsor, primary_sponsor_class, collaborators, lead_sponsor,
                brief_title, official_title,
                allocation, intervention_model, intervention_model_description,
                masking, masking_description, primary_purpose,
                interventions, intervention_types, drug_names, dosages, administration_routes,
                mechanisms_of_action, target_pathways, target_genes, target_proteins, target_chemical_compounds,
                biomarkers, biomarker_types, arms_groups, number_of_arms,
                primary_outcomes, secondary_outcomes, other_outcomes,
                inclusion_criteria, exclusion_criteria, eligibility_criteria_structured,
                min_age, max_age, eligible_sex, healthy_volunteers, demographics_other,
                conditions, disease_subtypes, disease_stages, disease_severity, keywords,
                required_prior_treatments, excluded_prior_treatments,
                locations, countries, facility_names, facility_status,
                investigators, overall_officials, responsible_party,
                enrollment_status, site_recruitment_status,
                ipd_sharing, ipd_sharing_plan, ipd_sharing_time_frame, 
                ipd_sharing_access_criteria, ipd_sharing_url,
                central_contacts, overall_contact, overall_contact_backup,
                trial_references, results_references, provided_documents,
                oversight_info, data_monitoring_committee,
                why_stopped, has_expanded_access, expanded_access_info,
                analysis_score, analysis_rationale, missing_info, recommendations,
                original_data, analyzed_data
            ) VALUES (
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s, %s, %s,
                %s, %s, %s, %s, %s, %s, %s, %s
            ) ON CONFLICT (nct_id) DO UPDATE SET
                status = EXCLUDED.status,
                registration_date = EXCLUDED.registration_date,
                start_date = EXCLUDED.start_date,
                completion_date = EXCLUDED.completion_date,
                last_update_date = EXCLUDED.last_update_date,
                study_first_submit_date = EXCLUDED.study_first_submit_date,
                primary_completion_date = EXCLUDED.primary_completion_date,
                phase = EXCLUDED.phase,
                study_type = EXCLUDED.study_type,
                target_enrollment = EXCLUDED.target_enrollment,
                actual_enrollment = EXCLUDED.actual_enrollment,
                enrollment_type = EXCLUDED.enrollment_type,
                primary_sponsor = EXCLUDED.primary_sponsor,
                primary_sponsor_class = EXCLUDED.primary_sponsor_class,
                collaborators = EXCLUDED.collaborators,
                lead_sponsor = EXCLUDED.lead_sponsor,
                brief_title = EXCLUDED.brief_title,
                official_title = EXCLUDED.official_title,
                allocation = EXCLUDED.allocation,
                intervention_model = EXCLUDED.intervention_model,
                intervention_model_description = EXCLUDED.intervention_model_description,
                masking = EXCLUDED.masking,
                masking_description = EXCLUDED.masking_description,
                primary_purpose = EXCLUDED.primary_purpose,
                interventions = EXCLUDED.interventions,
                intervention_types = EXCLUDED.intervention_types,
                drug_names = EXCLUDED.drug_names,
                dosages = EXCLUDED.dosages,
                administration_routes = EXCLUDED.administration_routes,
                mechanisms_of_action = EXCLUDED.mechanisms_of_action,
                target_pathways = EXCLUDED.target_pathways,
                target_genes = EXCLUDED.target_genes,
                target_proteins = EXCLUDED.target_proteins,
                target_chemical_compounds = EXCLUDED.target_chemical_compounds,
                biomarkers = EXCLUDED.biomarkers,
                biomarker_types = EXCLUDED.biomarker_types,
                arms_groups = EXCLUDED.arms_groups,
                number_of_arms = EXCLUDED.number_of_arms,
                primary_outcomes = EXCLUDED.primary_outcomes,
                secondary_outcomes = EXCLUDED.secondary_outcomes,
                other_outcomes = EXCLUDED.other_outcomes,
                inclusion_criteria = EXCLUDED.inclusion_criteria,
                exclusion_criteria = EXCLUDED.exclusion_criteria,
                eligibility_criteria_structured = EXCLUDED.eligibility_criteria_structured,
                min_age = EXCLUDED.min_age,
                max_age = EXCLUDED.max_age,
                eligible_sex = EXCLUDED.eligible_sex,
                healthy_volunteers = EXCLUDED.healthy_volunteers,
                demographics_other = EXCLUDED.demographics_other,
                conditions = EXCLUDED.conditions,
                disease_subtypes = EXCLUDED.disease_subtypes,
                disease_stages = EXCLUDED.disease_stages,
                disease_severity = EXCLUDED.disease_severity,
                keywords = EXCLUDED.keywords,
                required_prior_treatments = EXCLUDED.required_prior_treatments,
                excluded_prior_treatments = EXCLUDED.excluded_prior_treatments,
                locations = EXCLUDED.locations,
                countries = EXCLUDED.countries,
                facility_names = EXCLUDED.facility_names,
                facility_status = EXCLUDED.facility_status,
                investigators = EXCLUDED.investigators,
                overall_officials = EXCLUDED.overall_officials,
                responsible_party = EXCLUDED.responsible_party,
                enrollment_status = EXCLUDED.enrollment_status,
                site_recruitment_status = EXCLUDED.site_recruitment_status,
                ipd_sharing = EXCLUDED.ipd_sharing,
                ipd_sharing_plan = EXCLUDED.ipd_sharing_plan,
                ipd_sharing_time_frame = EXCLUDED.ipd_sharing_time_frame,
                ipd_sharing_access_criteria = EXCLUDED.ipd_sharing_access_criteria,
                ipd_sharing_url = EXCLUDED.ipd_sharing_url,
                central_contacts = EXCLUDED.central_contacts,
                overall_contact = EXCLUDED.overall_contact,
                overall_contact_backup = EXCLUDED.overall_contact_backup,
                trial_references = EXCLUDED.trial_references,
                results_references = EXCLUDED.results_references,
                provided_documents = EXCLUDED.provided_documents,
                oversight_info = EXCLUDED.oversight_info,
                data_monitoring_committee = EXCLUDED.data_monitoring_committee,
                why_stopped = EXCLUDED.why_stopped,
                has_expanded_access = EXCLUDED.has_expanded_access,
                expanded_access_info = EXCLUDED.expanded_access_info,
                analysis_score = EXCLUDED.analysis_score,
                analysis_rationale = EXCLUDED.analysis_rationale,
                missing_info = EXCLUDED.missing_info,
                recommendations = EXCLUDED.recommendations,
                original_data = EXCLUDED.original_data,
                analyzed_data = EXCLUDED.analyzed_data,
                updated_at = CURRENT_TIMESTAMP;
            """
            
            # Prepare comprehensive values tuple
            logger.info(f"Debug: Preparing values tuple for NCT ID: {nct_id}")
            
            # Build values step by step for debugging
            values_list = []
            
            # Core metadata (19 fields)
            core_values = [
                nct_id, status, registration_date, start_date, completion_date, last_update_date,
                study_first_submit_date, primary_completion_date, phase, study_type,
                target_enrollment, actual_enrollment, enrollment_type,
                primary_sponsor, primary_sponsor_class, json.dumps(collaborators), lead_sponsor,
                brief_title, official_title
            ]
            values_list.extend(core_values)
            logger.info(f"Debug: Added {len(core_values)} core metadata values")
            
            # Study design (6 fields)
            study_design_values = [
                allocation, intervention_model, intervention_model_description,
                masking, masking_description, primary_purpose
            ]
            values_list.extend(study_design_values)
            logger.info(f"Debug: Added {len(study_design_values)} study design values")
            
            # Interventions and mechanisms (10 fields)
            intervention_values = [
                json.dumps(interventions), json.dumps(intervention_types), json.dumps(drug_names), 
                json.dumps(dosages), json.dumps(administration_routes),
                json.dumps(mechanisms_of_action), json.dumps(target_pathways), 
                json.dumps(target_genes), json.dumps(target_proteins), json.dumps(target_chemical_compounds)
            ]
            values_list.extend(intervention_values)
            logger.info(f"Debug: Added {len(intervention_values)} intervention/mechanism values")
            
            # Biomarkers and study structure (4 fields)
            biomarker_values = [
                json.dumps(biomarkers), json.dumps(biomarker_types), json.dumps(arms_groups), number_of_arms
            ]
            values_list.extend(biomarker_values)
            logger.info(f"Debug: Added {len(biomarker_values)} biomarker/structure values")
            
            # Outcomes (3 fields)
            outcome_values = [
                json.dumps(primary_outcomes), json.dumps(secondary_outcomes), json.dumps(other_outcomes)
            ]
            values_list.extend(outcome_values)
            logger.info(f"Debug: Added {len(outcome_values)} outcome values")
            
            # Patient information (15 fields)
            patient_values = [
                json.dumps(inclusion_criteria), json.dumps(exclusion_criteria), json.dumps(eligibility_criteria_structured),
                min_age, max_age, eligible_sex, healthy_volunteers, json.dumps(demographics_other),
                json.dumps(conditions), json.dumps(disease_subtypes), json.dumps(disease_stages), 
                disease_severity, json.dumps(keywords),
                json.dumps(required_prior_treatments), json.dumps(excluded_prior_treatments)
            ]
            values_list.extend(patient_values)
            logger.info(f"Debug: Added {len(patient_values)} patient information values")
            
            # Operational aspects (9 fields)
            operational_values = [
                json.dumps(locations), json.dumps(countries), json.dumps(facility_names), json.dumps(facility_status),
                json.dumps(investigators), json.dumps(overall_officials), json.dumps(responsible_party),
                json.dumps(enrollment_status), json.dumps(site_recruitment_status)
            ]
            values_list.extend(operational_values)
            logger.info(f"Debug: Added {len(operational_values)} operational values")
            
            # IPD and contacts (8 fields)
            ipd_contact_values = [
                json.dumps(ipd_sharing), ipd_sharing_plan, ipd_sharing_time_frame,
                ipd_sharing_access_criteria, ipd_sharing_url,
                json.dumps(central_contacts), json.dumps(overall_contact), json.dumps(overall_contact_backup)
            ]
            values_list.extend(ipd_contact_values)
            logger.info(f"Debug: Added {len(ipd_contact_values)} IPD/contact values")
            
            # Documentation (5 fields)
            documentation_values = [
                json.dumps(trial_references), json.dumps(results_references), json.dumps(provided_documents),
                json.dumps(oversight_info), data_monitoring_committee
            ]
            values_list.extend(documentation_values)
            logger.info(f"Debug: Added {len(documentation_values)} documentation values")
            
            # Additional metadata (3 fields)
            additional_values = [
                why_stopped, has_expanded_access, json.dumps(expanded_access_info)
            ]
            values_list.extend(additional_values)
            logger.info(f"Debug: Added {len(additional_values)} additional metadata values")
            
            # Quality assessment (4 fields)
            quality_values = [
                data.get('validation', {}).get('overall_assessment', {}).get('score'),
                self._clean_text_field(data.get('validation', {}).get('overall_assessment', {}).get('rationale')),
                json.dumps(data.get('validation', {}).get('missing_info', [])),
                json.dumps(data.get('validation', {}).get('recommendations', []))
            ]
            values_list.extend(quality_values)
            logger.info(f"Debug: Added {len(quality_values)} quality assessment values")
            
            # Full data (2 fields)
            full_data_values = [
                json.dumps(original_data), json.dumps(analyzed_data)
            ]
            values_list.extend(full_data_values)
            logger.info(f"Debug: Added {len(full_data_values)} full data values")
            
            # Convert to tuple
            values = tuple(values_list)
            logger.info(f"Debug: Total values in tuple: {len(values)}")
            
            # Debug: Count placeholders and values
            placeholder_count = insert_sql.count('%s')
            values_count = len(values)
            
            logger.info(f"Debug: SQL has {placeholder_count} placeholders, providing {values_count} values")
            
            # Debug: Count actual fields in INSERT statement
            insert_section = insert_sql.split('INSERT INTO')[1].split(') VALUES')[0]
            # Remove table name and extract just the field list
            field_list_start = insert_section.find('(') + 1
            field_list = insert_section[field_list_start:].strip()
            # Split by comma and count
            fields = [f.strip() for f in field_list.split(',') if f.strip()]
            actual_field_count = len(fields)
            
            logger.info(f"Debug: INSERT statement has {actual_field_count} actual fields")
            logger.info(f"Debug: First 10 fields: {fields[:10]}")
            logger.info(f"Debug: Last 10 fields: {fields[-10:]}")
            
            if placeholder_count != values_count:
                logger.error(f"MISMATCH: SQL expects {placeholder_count} values but got {values_count}")
                logger.error(f"DEBUG: INSERT has {actual_field_count} fields, values has {values_count} values")
                logger.error("SQL placeholders vs values mismatch - dumping details:")
                
                # Log the first few values for inspection
                for i, value in enumerate(values[:10]):
                    logger.error(f"  Value {i}: {type(value)} = {str(value)[:100]}...")
                
                # Count placeholders in each section
                insert_section_full = insert_sql.split('VALUES')[0]
                values_section = insert_sql.split('VALUES')[1].split('ON CONFLICT')[0]
                insert_placeholder_count = insert_section_full.count('%s')
                values_placeholder_count = values_section.count('%s')
                
                logger.error(f"INSERT section placeholders: {insert_placeholder_count}")
                logger.error(f"VALUES section placeholders: {values_placeholder_count}")
                
                return False
            
            # Execute insert
            try:
                with self.connection.cursor() as cursor:
                    cursor.execute(insert_sql, values)
                    self.connection.commit()
                
                logger.info(f"Successfully inserted/updated comprehensive trial data for {nct_id} in table {table_name}")
                return True
                
            except Exception as exec_error:
                logger.error(f"SQL execution error: {exec_error}")
                logger.error(f"SQL query length: {len(insert_sql)}")
                logger.error(f"Values tuple length: {len(values)}")
                
                # Log some of the SQL for debugging
                sql_lines = insert_sql.split('\n')
                logger.error("First 10 lines of SQL:")
                for i, line in enumerate(sql_lines[:10]):
                    logger.error(f"  {i+1}: {line}")
                
                raise exec_error
            
        except Exception as e:
            if self.connection:
                self.connection.rollback()
            logger.error(f"Failed to insert comprehensive analysis data: {e}")
            logger.error(f"Error type: {type(e)}")
            import traceback
            logger.error(f"Full traceback:\n{traceback.format_exc()}")
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
    
    def _parse_integer(self, value: Any) -> Optional[int]:
        """
        Parse integer values safely.
        
        Args:
            value: Value to parse
        
        Returns:
            Integer value or None
        """
        if value is None or value == "N/A" or value == "":
            return None
        
        if isinstance(value, int):
            return value
        
        if isinstance(value, str):
            if value.isdigit():
                return int(value)
            else:
                return None
        
        return None
    
    def _process_interventions(self, interventions_raw: list) -> list:
        """Process and clean interventions data."""
        if not interventions_raw:
            return []
        return interventions_raw
    
    def _extract_intervention_types(self, interventions_raw: list) -> list:
        """Extract intervention types from interventions."""
        types = []
        for intervention in interventions_raw or []:
            if isinstance(intervention, dict) and 'type' in intervention:
                intervention_type = intervention['type']
                if intervention_type and intervention_type not in types:
                    types.append(intervention_type)
        return types
    
    def _extract_drug_names(self, interventions_raw: list) -> list:
        """Extract drug names from interventions."""
        drugs = []
        for intervention in interventions_raw or []:
            if isinstance(intervention, dict):
                name = intervention.get('name')
                if name and intervention.get('type', '').lower() == 'drug':
                    if name not in drugs:
                        drugs.append(name)
        return drugs
    
    def _extract_dosages(self, interventions_raw: list) -> list:
        """Extract dosages from interventions."""
        dosages = []
        for intervention in interventions_raw or []:
            if isinstance(intervention, dict):
                dosage = intervention.get('dosage')
                if dosage and dosage != 'N/A' and dosage not in dosages:
                    dosages.append(dosage)
        return dosages
    
    def _extract_administration_routes(self, interventions_raw: list) -> list:
        """Extract administration routes from interventions."""
        routes = []
        for intervention in interventions_raw or []:
            if isinstance(intervention, dict):
                route = intervention.get('route')
                if route and route != 'N/A' and route not in routes:
                    routes.append(route)
        return routes
    
    def _extract_mechanisms_of_action(self, mechanisms_raw: list) -> list:
        """Extract mechanisms of action from mechanism data."""
        mechanisms = []
        for mechanism in mechanisms_raw or []:
            if isinstance(mechanism, dict):
                moa = mechanism.get('mechanism_of_action')
                if moa and moa not in mechanisms:
                    mechanisms.append(moa)
        return mechanisms
    
    def _extract_target_pathways(self, mechanisms_raw: list) -> list:
        """Extract target pathways from mechanism data."""
        pathways = []
        for mechanism in mechanisms_raw or []:
            if isinstance(mechanism, dict):
                target_pathway = mechanism.get('target_pathway', {})
                if target_pathway and target_pathway not in pathways:
                    pathways.append(target_pathway)
        return pathways
    
    def _extract_target_genes(self, mechanisms_raw: list) -> list:
        """Extract target genes from mechanism data."""
        genes = []
        for mechanism in mechanisms_raw or []:
            if isinstance(mechanism, dict):
                target_pathway = mechanism.get('target_pathway', {})
                mechanism_genes = target_pathway.get('gene', [])
                for gene in mechanism_genes:
                    if gene and gene not in genes:
                        genes.append(gene)
        return genes
    
    def _extract_target_proteins(self, mechanisms_raw: list) -> list:
        """Extract target proteins from mechanism data."""
        proteins = []
        for mechanism in mechanisms_raw or []:
            if isinstance(mechanism, dict):
                target_pathway = mechanism.get('target_pathway', {})
                mechanism_proteins = target_pathway.get('protein', [])
                for protein in mechanism_proteins:
                    if protein and protein not in proteins:
                        proteins.append(protein)
        return proteins
    
    def _extract_target_chemical_compounds(self, mechanisms_raw: list) -> list:
        """Extract target chemical compounds from mechanism data."""
        compounds = []
        for mechanism in mechanisms_raw or []:
            if isinstance(mechanism, dict):
                target_pathway = mechanism.get('target_pathway', {})
                mechanism_compounds = target_pathway.get('chemical_compound', [])
                for compound in mechanism_compounds:
                    if compound and compound not in compounds:
                        compounds.append(compound)
        return compounds
    
    def _process_biomarkers(self, biomarkers_raw: list) -> list:
        """Process and clean biomarkers data."""
        if not biomarkers_raw:
            return []
        return biomarkers_raw
    
    def _extract_biomarker_types(self, biomarkers_raw: list) -> list:
        """Extract biomarker types (could be enhanced based on biomarker categorization)."""
        # This could be enhanced to categorize biomarkers by type
        # For now, return the biomarkers as types
        return biomarkers_raw or []
    
    def _structure_eligibility_criteria(self, inclusion: list, exclusion: list) -> dict:
        """
        Structure eligibility criteria into decomposed parameters.
        
        Args:
            inclusion: List of inclusion criteria
            exclusion: List of exclusion criteria
        
        Returns:
            Structured eligibility criteria
        """
        structured = {
            'age_related': [],
            'condition_related': [],
            'treatment_related': [],
            'procedure_related': [],
            'laboratory_related': [],
            'general': []
        }
        
        # Simple keyword-based categorization
        age_keywords = ['age', 'years', 'months', 'older', 'younger']
        condition_keywords = ['diagnosis', 'disease', 'condition', 'cancer', 'tumor']
        treatment_keywords = ['treatment', 'therapy', 'medication', 'drug', 'chemotherapy']
        procedure_keywords = ['surgery', 'procedure', 'biopsy', 'scan']
        lab_keywords = ['laboratory', 'blood', 'serum', 'hemoglobin', 'creatinine', 'liver']
        
        for criteria_list, criteria_type in [(inclusion, 'inclusion'), (exclusion, 'exclusion')]:
            for criterion in criteria_list:
                if not isinstance(criterion, str):
                    continue
                    
                criterion_lower = criterion.lower()
                categorized = False
                
                if any(keyword in criterion_lower for keyword in age_keywords):
                    structured['age_related'].append({'type': criteria_type, 'criterion': criterion})
                    categorized = True
                elif any(keyword in criterion_lower for keyword in condition_keywords):
                    structured['condition_related'].append({'type': criteria_type, 'criterion': criterion})
                    categorized = True
                elif any(keyword in criterion_lower for keyword in treatment_keywords):
                    structured['treatment_related'].append({'type': criteria_type, 'criterion': criterion})
                    categorized = True
                elif any(keyword in criterion_lower for keyword in procedure_keywords):
                    structured['procedure_related'].append({'type': criteria_type, 'criterion': criterion})
                    categorized = True
                elif any(keyword in criterion_lower for keyword in lab_keywords):
                    structured['laboratory_related'].append({'type': criteria_type, 'criterion': criterion})
                    categorized = True
                
                if not categorized:
                    structured['general'].append({'type': criteria_type, 'criterion': criterion})
        
        return structured
    
    def _process_locations(self, locations_raw: list) -> list:
        """Process and clean locations data."""
        if not locations_raw:
            return []
        return locations_raw
    
    def _extract_countries(self, locations_raw: list) -> list:
        """Extract countries from locations data."""
        countries = []
        for location in locations_raw or []:
            if isinstance(location, dict):
                country = location.get('country')
                if country and country not in countries:
                    countries.append(country)
            elif isinstance(location, str):
                # Simple extraction if location is just a string
                countries.append(location)
        return countries
    
    def _extract_facility_names(self, locations_raw: list) -> list:
        """Extract facility names from locations data."""
        facilities = []
        for location in locations_raw or []:
            if isinstance(location, dict):
                facility = location.get('facility') or location.get('name')
                if facility and facility not in facilities:
                    facilities.append(facility)
        return facilities
    
    def _extract_facility_status(self, locations_raw: list) -> list:
        """Extract facility status from locations data."""
        statuses = []
        for location in locations_raw or []:
            if isinstance(location, dict):
                status = location.get('status')
                if status and status not in statuses:
                    statuses.append(status)
        return statuses
    
    def _extract_site_recruitment_status(self, locations_raw: list) -> dict:
        """Extract site-specific recruitment status."""
        site_status = {}
        for location in locations_raw or []:
            if isinstance(location, dict):
                facility = location.get('facility') or location.get('name')
                status = location.get('status')
                if facility and status:
                    site_status[facility] = status
        return site_status 