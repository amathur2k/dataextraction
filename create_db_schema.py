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
        
        -- Core trial metadata
        nct_id VARCHAR(20) UNIQUE NOT NULL,
        status VARCHAR(100),
        phase VARCHAR(50),
        study_type VARCHAR(100),
        
        -- Dates (stored as text due to inconsistent formats in source data)
        registration_date TEXT,
        start_date TEXT,
        completion_date TEXT,
        last_update_date TEXT,
        
        -- Enrollment information
        target_enrollment INTEGER,
        actual_enrollment INTEGER,
        
        -- Sponsor information
        primary_sponsor TEXT,
        collaborators TEXT,
        
        -- Study design
        allocation VARCHAR(100),
        intervention_model VARCHAR(100),
        masking VARCHAR(100),
        primary_purpose VARCHAR(100),
        
        -- JSON fields for complex nested data
        interventions JSONB,
        arms_groups JSONB,
        primary_outcomes JSONB,
        secondary_outcomes JSONB,
        mechanism_and_targets JSONB,
        biomarkers JSONB,
        
        -- Eligibility criteria
        inclusion_criteria JSONB,
        exclusion_criteria JSONB,
        
        -- Demographics and patient info
        min_age INTEGER,
        max_age INTEGER,
        eligible_sex VARCHAR(20),
        demographics_other JSONB,
        
        -- Disease characteristics
        disease_subtypes JSONB,
        disease_stages JSONB,
        disease_severity TEXT,
        
        -- Prior treatments
        required_prior_treatments JSONB,
        excluded_prior_treatments JSONB,
        
        -- Operational aspects
        locations JSONB,
        investigators JSONB,
        enrollment_status JSONB,
        ipd_sharing JSONB,
        
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
    -- Indexes for common queries
    CREATE INDEX idx_{table_name}_nct_id ON {table_name}(nct_id);
    CREATE INDEX idx_{table_name}_status ON {table_name}(status);
    CREATE INDEX idx_{table_name}_phase ON {table_name}(phase);
    CREATE INDEX idx_{table_name}_study_type ON {table_name}(study_type);
    CREATE INDEX idx_{table_name}_primary_sponsor ON {table_name}(primary_sponsor);
    CREATE INDEX idx_{table_name}_created_at ON {table_name}(created_at);
    
    -- GIN indexes for JSONB fields
    CREATE INDEX idx_{table_name}_interventions_gin ON {table_name} USING GIN (interventions);
    CREATE INDEX idx_{table_name}_biomarkers_gin ON {table_name} USING GIN (biomarkers);
    CREATE INDEX idx_{table_name}_analyzed_data_gin ON {table_name} USING GIN (analyzed_data);
    
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
            setweight(to_tsvector('english', COALESCE(NEW.primary_sponsor, '')), 'B') ||
            setweight(to_tsvector('english', COALESCE(NEW.phase, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(NEW.status, '')), 'C') ||
            setweight(to_tsvector('english', COALESCE(NEW.disease_severity, '')), 'D');
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