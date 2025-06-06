#!/usr/bin/env python3
"""
PostgreSQL Database Schema Creation Script for Clinical Trial Analysis Data

This script creates the necessary table structure to store analyzed clinical trial data.
"""

import psycopg2
import argparse
import logging
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_table_schema(cursor, table_name="myclinicaltrials"):
    """
    Create the clinical trials analysis table with comprehensive schema.
    
    Args:
        cursor: Database cursor object
        table_name: Name of the table to create
    """
    
    # Drop table if exists (for fresh creation)
    drop_sql = f"DROP TABLE IF EXISTS {table_name};"
    
    # Create table SQL
    create_sql = f"""
    CREATE TABLE {table_name} (
        -- Primary key and metadata
        id SERIAL PRIMARY KEY,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        
        -- ========== CORE TRIAL METADATA ==========
        -- Unique trial identifier for tracking and linking
        nct_id VARCHAR(20) UNIQUE NOT NULL,
        
        -- Current state (recruiting, completed, terminated, etc.)
        status VARCHAR(100),
        
        -- Dates: Registration, start, completion, update timestamps
        registration_date TEXT,
        start_date TEXT,
        completion_date TEXT,
        last_update_date TEXT,
        study_first_submit_date TEXT,
        primary_completion_date TEXT,
        
        -- Trial phase (I-IV, early phase, etc.)
        phase VARCHAR(50),
        
        -- Study Type: Interventional, observational, expanded access
        study_type VARCHAR(100),
        
        -- Enrollment: Target and actual participant counts
        target_enrollment INTEGER,
        actual_enrollment INTEGER,
        enrollment_type VARCHAR(50),
        
        -- Sponsor/Collaborators: Primary sponsor and key collaborators
        primary_sponsor TEXT,
        primary_sponsor_class VARCHAR(100),
        collaborators JSONB,
        lead_sponsor TEXT,
        
        -- Official trial titles
        brief_title TEXT,
        official_title TEXT,
        
        -- ========== SCIENTIFIC CONTENT ==========
        -- Study Design: Randomization, blinding, control types
        allocation VARCHAR(100),
        intervention_model VARCHAR(100),
        intervention_model_description TEXT,
        masking VARCHAR(100),
        masking_description TEXT,
        primary_purpose VARCHAR(100),
        
        -- Intervention: Drug details, dosages, administration routes
        interventions JSONB,
        intervention_types JSONB,
        drug_names JSONB,
        dosages JSONB,
        administration_routes JSONB,
        
        -- Mechanism of Action: Extracted from descriptions
        mechanisms_of_action JSONB,
        
        -- Target/Pathway: Biological targets being addressed
        target_pathways JSONB,
        
        -- Gene, Protein, Chemical compound (separate structured fields)
        target_genes JSONB,
        target_proteins JSONB,
        target_chemical_compounds JSONB,
        
        -- Biomarkers: Used for enrollment, stratification, or outcomes
        biomarkers JSONB,
        biomarker_types JSONB,
        
        -- Arms/Groups: Number, types, and descriptions
        arms_groups JSONB,
        number_of_arms INTEGER,
        
        -- Primary/Secondary Outcomes: Endpoints and timeframes
        primary_outcomes JSONB,
        secondary_outcomes JSONB,
        other_outcomes JSONB,
        
        -- ========== PATIENT-RELATED INFORMATION ==========
        -- Eligibility Criteria: Complete inclusion/exclusion criteria
        inclusion_criteria JSONB,
        exclusion_criteria JSONB,
        
        -- Structured eligibility parameters
        eligibility_criteria_structured JSONB,
        
        -- Demographics: Age, sex, and other demographic requirements
        min_age INTEGER,
        max_age INTEGER,
        eligible_sex VARCHAR(20),
        healthy_volunteers VARCHAR(20),
        demographics_other JSONB,
        
        -- Disease Characteristics: Subtypes, stages, severity
        conditions JSONB,
        disease_subtypes JSONB,
        disease_stages JSONB,
        disease_severity TEXT,
        keywords JSONB,
        
        -- Prior Treatments: Required or excluded previous therapies
        required_prior_treatments JSONB,
        excluded_prior_treatments JSONB,
        
        -- ========== OPERATIONAL ASPECTS ==========
        -- Locations: Trial sites, countries, and regions
        locations JSONB,
        countries JSONB,
        facility_names JSONB,
        facility_status JSONB,
        
        -- Investigators: Site PIs and leadership teams
        investigators JSONB,
        overall_officials JSONB,
        responsible_party JSONB,
        
        -- Enrollment Status: Site-specific recruitment progress
        enrollment_status JSONB,
        site_recruitment_status JSONB,
        
        -- IPD Sharing: Data sharing commitments and platforms
        ipd_sharing JSONB,
        ipd_sharing_plan TEXT,
        ipd_sharing_time_frame TEXT,
        ipd_sharing_access_criteria TEXT,
        ipd_sharing_url TEXT,
        
        -- Contact information
        central_contacts JSONB,
        overall_contact JSONB,
        overall_contact_backup JSONB,
        
        -- References and links
        trial_references JSONB,
        results_references JSONB,
        provided_documents JSONB,
        
        -- Study monitoring and oversight
        oversight_info JSONB,
        data_monitoring_committee TEXT,
        
        -- Additional metadata
        why_stopped TEXT,
        has_expanded_access TEXT,
        expanded_access_info JSONB,
        
        -- Quality assessment (if available)
        analysis_score INTEGER,
        analysis_rationale TEXT,
        missing_info JSONB,
        recommendations JSONB,
        
        -- Store original and analyzed data as JSON for reference
        original_data JSONB,
        analyzed_data JSONB,
        
        -- Full text search
        search_vector TSVECTOR
    );
    """
    
    # Create indexes for better performance
    indexes_sql = f"""
    -- Core metadata indexes
    CREATE INDEX idx_{table_name}_nct_id ON {table_name}(nct_id);
    CREATE INDEX idx_{table_name}_status ON {table_name}(status);
    CREATE INDEX idx_{table_name}_phase ON {table_name}(phase);
    CREATE INDEX idx_{table_name}_study_type ON {table_name}(study_type);
    CREATE INDEX idx_{table_name}_primary_sponsor ON {table_name}(primary_sponsor);
    CREATE INDEX idx_{table_name}_primary_sponsor_class ON {table_name}(primary_sponsor_class);
    CREATE INDEX idx_{table_name}_enrollment_type ON {table_name}(enrollment_type);
    CREATE INDEX idx_{table_name}_allocation ON {table_name}(allocation);
    CREATE INDEX idx_{table_name}_intervention_model ON {table_name}(intervention_model);
    CREATE INDEX idx_{table_name}_masking ON {table_name}(masking);
    CREATE INDEX idx_{table_name}_primary_purpose ON {table_name}(primary_purpose);
    CREATE INDEX idx_{table_name}_created_at ON {table_name}(created_at);
    CREATE INDEX idx_{table_name}_start_date ON {table_name}(start_date);
    CREATE INDEX idx_{table_name}_completion_date ON {table_name}(completion_date);
    
    -- Patient information indexes
    CREATE INDEX idx_{table_name}_eligible_sex ON {table_name}(eligible_sex);
    CREATE INDEX idx_{table_name}_healthy_volunteers ON {table_name}(healthy_volunteers);
    CREATE INDEX idx_{table_name}_min_age ON {table_name}(min_age);
    CREATE INDEX idx_{table_name}_max_age ON {table_name}(max_age);
    CREATE INDEX idx_{table_name}_target_enrollment ON {table_name}(target_enrollment);
    CREATE INDEX idx_{table_name}_actual_enrollment ON {table_name}(actual_enrollment);
    
    -- GIN indexes for JSONB fields (Core Scientific Content)
    CREATE INDEX idx_{table_name}_interventions_gin ON {table_name} USING GIN (interventions);
    CREATE INDEX idx_{table_name}_drug_names_gin ON {table_name} USING GIN (drug_names);
    CREATE INDEX idx_{table_name}_biomarkers_gin ON {table_name} USING GIN (biomarkers);
    CREATE INDEX idx_{table_name}_target_genes_gin ON {table_name} USING GIN (target_genes);
    CREATE INDEX idx_{table_name}_target_proteins_gin ON {table_name} USING GIN (target_proteins);
    CREATE INDEX idx_{table_name}_target_chemical_compounds_gin ON {table_name} USING GIN (target_chemical_compounds);
    CREATE INDEX idx_{table_name}_mechanisms_of_action_gin ON {table_name} USING GIN (mechanisms_of_action);
    
    -- GIN indexes for JSONB fields (Patient Information)
    CREATE INDEX idx_{table_name}_conditions_gin ON {table_name} USING GIN (conditions);
    CREATE INDEX idx_{table_name}_disease_subtypes_gin ON {table_name} USING GIN (disease_subtypes);
    CREATE INDEX idx_{table_name}_keywords_gin ON {table_name} USING GIN (keywords);
    CREATE INDEX idx_{table_name}_inclusion_criteria_gin ON {table_name} USING GIN (inclusion_criteria);
    CREATE INDEX idx_{table_name}_exclusion_criteria_gin ON {table_name} USING GIN (exclusion_criteria);
    
    -- GIN indexes for JSONB fields (Operational)
    CREATE INDEX idx_{table_name}_countries_gin ON {table_name} USING GIN (countries);
    CREATE INDEX idx_{table_name}_locations_gin ON {table_name} USING GIN (locations);
    CREATE INDEX idx_{table_name}_investigators_gin ON {table_name} USING GIN (investigators);
    CREATE INDEX idx_{table_name}_collaborators_gin ON {table_name} USING GIN (collaborators);
    
    -- GIN indexes for JSONB fields (Outcomes)
    CREATE INDEX idx_{table_name}_primary_outcomes_gin ON {table_name} USING GIN (primary_outcomes);
    CREATE INDEX idx_{table_name}_secondary_outcomes_gin ON {table_name} USING GIN (secondary_outcomes);
    
    -- GIN indexes for full data and analysis
    CREATE INDEX idx_{table_name}_analyzed_data_gin ON {table_name} USING GIN (analyzed_data);
    CREATE INDEX idx_{table_name}_original_data_gin ON {table_name} USING GIN (original_data);
    
    -- Full text search index
    CREATE INDEX idx_{table_name}_search_vector ON {table_name} USING GIN (search_vector);
    """
    
    # Create trigger for updating search vector and updated_at
    trigger_sql = f"""
    -- Function to update search vector and timestamp
    CREATE OR REPLACE FUNCTION update_{table_name}_search_vector() RETURNS TRIGGER AS $$
    BEGIN
        NEW.updated_at = CURRENT_TIMESTAMP;
        NEW.search_vector = 
            setweight(to_tsvector('english', COALESCE(NEW.nct_id, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(NEW.brief_title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(NEW.official_title, '')), 'A') ||
            setweight(to_tsvector('english', COALESCE(NEW.primary_sponsor, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(NEW.phase, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(NEW.status, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(NEW.study_type, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(NEW.primary_purpose, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(NEW.intervention_model, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(NEW.allocation, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(NEW.masking, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(NEW.disease_severity, '')), 'D') ||
            setweight(to_tsvector('english', COALESCE(NEW.eligible_sex, '')), 'D') ||
            setweight(to_tsvector('english', COALESCE(NEW.healthy_volunteers, '')), 'D');
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    
    -- Create trigger
    CREATE TRIGGER trigger_{table_name}_search_vector
        BEFORE INSERT OR UPDATE ON {table_name}
        FOR EACH ROW EXECUTE FUNCTION update_{table_name}_search_vector();
    """
    
    try:
        logger.info(f"Dropping existing table {table_name} if it exists...")
        cursor.execute(drop_sql)
        
        logger.info(f"Creating table {table_name}...")
        cursor.execute(create_sql)
        
        logger.info(f"Creating indexes for table {table_name}...")
        cursor.execute(indexes_sql)
        
        logger.info(f"Creating triggers for table {table_name}...")
        cursor.execute(trigger_sql)
        
        logger.info(f"Successfully created table {table_name} with all indexes and triggers")
        
    except Exception as e:
        logger.error(f"Error creating table schema: {e}")
        raise

def create_database_if_not_exists(host, port, user, password, database_name):
    """
    Create database if it doesn't exist.
    
    Args:
        host: Database host
        port: Database port
        user: Database user
        password: Database password
        database_name: Name of database to create
    """
    try:
        # Connect to the default postgres database to check/create the target database
        logger.info(f"Connecting to PostgreSQL server on {host}:{port} to check/create database")
        conn = psycopg2.connect(
            host=host,
            port=port,
            database='postgres',  # Connect to default postgres database
            user=user,
            password=password
        )
        
        # Set autocommit for database creation
        conn.autocommit = True
        
        with conn.cursor() as cursor:
            # Check if database exists
            cursor.execute("""
                SELECT 1 FROM pg_database WHERE datname = %s;
            """, (database_name,))
            
            exists = cursor.fetchone()
            
            if exists:
                logger.info(f"Database '{database_name}' already exists")
            else:
                # Create database
                logger.info(f"Creating database '{database_name}'...")
                cursor.execute(f'CREATE DATABASE "{database_name}";')
                logger.info(f"Database '{database_name}' created successfully")
        
        conn.close()
        return True
        
    except psycopg2.Error as e:
        logger.error(f"Error creating database: {e}")
        return False

def main():
    """Main function to create the database schema."""
    parser = argparse.ArgumentParser(description='Create PostgreSQL schema for clinical trial analysis data')
    
    # Database connection arguments
    parser.add_argument('--db-host', default='localhost', help='Database host (default: localhost)')
    parser.add_argument('--db-port', type=int, default=5432, help='Database port (default: 5432)')
    parser.add_argument('--db-name', default='ctdb', help='Database name (default: ctdb)')
    parser.add_argument('--db-user', default='postgres', help='Database user (default: postgres)')
    parser.add_argument('--db-password', default='admin', help='Database password (default: admin)')
    parser.add_argument('--table-name', default='myclinicaltrials', help='Table name (default: myclinicaltrials)')
    
    args = parser.parse_args()
    
    try:
        # Step 1: Create database if it doesn't exist
        if not create_database_if_not_exists(
            args.db_host, args.db_port, args.db_user, args.db_password, args.db_name
        ):
            logger.error("Failed to create/verify database existence")
            sys.exit(1)
        
        # Step 2: Connect to the target database and create table schema
        logger.info(f"Connecting to database {args.db_name} to create table schema")
        conn = psycopg2.connect(
            host=args.db_host,
            port=args.db_port,
            database=args.db_name,
            user=args.db_user,
            password=args.db_password
        )
        
        # Create table schema
        with conn.cursor() as cursor:
            create_table_schema(cursor, args.table_name)
        
        # Commit changes
        conn.commit()
        logger.info("Database schema created successfully!")
        
    except psycopg2.Error as e:
        logger.error(f"Database error: {e}")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)
    finally:
        if 'conn' in locals():
            conn.close()
            logger.info("Database connection closed")

if __name__ == '__main__':
    main() 