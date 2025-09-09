"""
Data management module for the Real Estate Agent application.

This module provides all data operations including:
- Data cleaning and type inference
- Database setup and initialization
- Vector store setup
- Data loading utilities
"""

import os
import sys
import pandas as pd
from typing import Optional, Tuple, Dict, Any
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config import config
from src.services.db.sql import db_service
from cache import cache_manager
from langchain_postgres import PGVector
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document


def clean_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean a DataFrame by standardizing formats and handling missing values.
    
    Args:
        df: Input DataFrame to clean
        
    Returns:
        Cleaned DataFrame
    """
    # Create a copy to avoid modifying the original
    cleaned_df = df.copy()
    
    # Strip whitespace from string columns
    for col in cleaned_df.select_dtypes(include="object").columns:
        cleaned_df[col] = cleaned_df[col].astype(str).str.strip()
    
    # Replace common missing value indicators with NaN
    cleaned_df.replace({
        "": pd.NA, 
        "nan": pd.NA, 
        "N/A": pd.NA, 
        "NA": pd.NA
    }, inplace=True)
    
    # Add leading zero to 3-digit zip codes
    if "zip_code" in cleaned_df.columns:
        cleaned_df["zip_code"] = cleaned_df["zip_code"].astype(str).apply(
            lambda x: f"0{x}" if len(x) == 3 and x.isdigit() else x
        )
    
    # Drop duplicate rows
    cleaned_df = cleaned_df.drop_duplicates()
    
    # Fill missing values in numeric columns with median
    for col in cleaned_df.select_dtypes(include="number").columns:
        cleaned_df[col] = cleaned_df[col].fillna(cleaned_df[col].median())
    
    # Standardize nearby_amenities format
    if "nearby_amenities" in cleaned_df.columns:
        cleaned_df["nearby_amenities"] = (
            cleaned_df["nearby_amenities"]
            .astype(str)
            .str.strip()
            .str.lower()  # Convert to lowercase for consistency
            .str.replace(r"\s*\|\s*", "|", regex=True)  # Remove spaces around delimiters
        )
    
    return cleaned_df


class DataTypeInferencer:
    """
    A class to automatically infer and convert data types in pandas DataFrames.
    Handles messy real-world data by cleaning and converting to appropriate types.
    """
    
    def __init__(self, success_threshold: float = 0.80):
        """
        Initialize the data type inferencer.
        
        Args:
            success_threshold: Minimum ratio of successful conversions needed 
                             to accept a data type (default 80%)
        """
        self.threshold = success_threshold
        self.boolean_true_values = {"true", "t", "yes", "y", "1"}
        self.boolean_false_values = {"false", "f", "no", "n", "0"}
    
    def clean_and_convert_to_numeric(self, series: pd.Series) -> pd.Series:
        """
        Clean and convert a pandas Series to numeric type.
        
        Removes common formatting like:
        - Dollar signs ($)
        - Commas (,)
        - Percentage signs (%)
        - Extra whitespace
        
        Args:
            series: Input pandas Series
            
        Returns:
            Series with numeric values (NaN for unconvertible values)
            
        Example:
            Input: ["$1,500", "2,000", "3.5%", "invalid"]
            Output: [1500.0, 2000.0, 3.5, NaN]
        """
        # Convert to string and strip whitespace
        clean_series = series.astype(str).str.strip()
        
        # Replace empty strings and 'nan' with None
        clean_series = clean_series.replace({"": None, "nan": None})
        
        # Remove currency symbols, commas, and percentage signs
        clean_series = clean_series.str.replace(r"[,\s$%]", "", regex=True)
        
        # Convert to numeric, setting errors to NaN
        return pd.to_numeric(clean_series, errors="coerce")
    
    def clean_and_convert_to_datetime(self, series: pd.Series) -> pd.Series:
        """
        Clean and convert a pandas Series to datetime type.
        
        Args:
            series: Input pandas Series
            
        Returns:
            Series with datetime values (NaT for unconvertible values)
            
        Example:
            Input: ["2023-01-15", "15/01/2023", "invalid date"]
            Output: [2023-01-15, 2023-01-15, NaT]
        """
        # Convert to string and strip whitespace
        clean_series = series.astype(str).str.strip()
        
        # Replace empty strings and 'nan' with None
        clean_series = clean_series.replace({"": None, "nan": None})
        
        # Convert to datetime with automatic format inference
        return pd.to_datetime(clean_series, errors="coerce", infer_datetime_format=True)
    
    def clean_and_convert_to_boolean(self, series: pd.Series) -> Optional[pd.Series]:
        """
        Clean and convert a pandas Series to boolean type.
        
        Only converts if enough values match known boolean patterns.
        
        Args:
            series: Input pandas Series
            
        Returns:
            Series with boolean values if successful, None if not enough matches
            
        Example:
            Input: ["true", "false", "yes", "no", "1", "0"]
            Output: [True, False, True, False, True, False]
        """
        # Convert to lowercase strings and strip whitespace
        clean_series = series.astype(str).str.strip().str.lower()
        
        # Check how many values match known boolean patterns
        all_boolean_values = self.boolean_true_values | self.boolean_false_values
        known_boolean_mask = clean_series.isin(all_boolean_values)
        
        # Only proceed if enough values are recognizable booleans
        if known_boolean_mask.mean() >= self.threshold:
            # Map values to True/False/None
            def map_to_boolean(value):
                if value in self.boolean_true_values:
                    return True
                elif value in self.boolean_false_values:
                    return False
                else:
                    return None
            
            return clean_series.map(map_to_boolean)
        
        return None
    
    def analyze_and_convert_dataframe(self, df: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
        """
        Analyze a DataFrame and convert columns to appropriate data types.
        
        Process:
        1. Skip columns that already have proper types
        2. Try to convert to boolean, numeric, then datetime
        3. Keep as text if no conversion succeeds
        4. Generate a detailed report
        
        Args:
            df: Input DataFrame
            
        Returns:
            Tuple of (converted_dataframe, conversion_report)
            
        Example:
            Input DataFrame with mixed types
            Output: Clean DataFrame + report showing what was converted
        """
        conversion_info = []
        converted_df = df.copy()
        
        for column_name in df.columns:
            series = df[column_name]
            
            # Skip columns that already have proper data types
            if (pd.api.types.is_numeric_dtype(series) or 
                pd.api.types.is_datetime64_any_dtype(series) or 
                pd.api.types.is_bool_dtype(series)):
                
                conversion_info.append({
                    'column': column_name,
                    'inferred_type': str(series.dtype),
                    'success_rate': 1.0,
                    'null_percentage': series.isna().mean()
                })
                continue
            
            # Try boolean conversion first
            boolean_result = self.clean_and_convert_to_boolean(series)
            if boolean_result is not None:
                converted_df[column_name] = boolean_result
                conversion_info.append({
                    'column': column_name,
                    'inferred_type': 'boolean',
                    'success_rate': boolean_result.notna().mean(),
                    'null_percentage': boolean_result.isna().mean()
                })
                continue
            
            # Try numeric conversion
            numeric_result = self.clean_and_convert_to_numeric(series)
            numeric_success_rate = numeric_result.notna().mean()
            
            if numeric_success_rate >= self.threshold:
                converted_df[column_name] = numeric_result
                conversion_info.append({
                    'column': column_name,
                    'inferred_type': 'numeric',
                    'success_rate': numeric_success_rate,
                    'null_percentage': numeric_result.isna().mean()
                })
                continue
            
            # Try datetime conversion
            datetime_result = self.clean_and_convert_to_datetime(series)
            datetime_success_rate = datetime_result.notna().mean()
            
            if datetime_success_rate >= self.threshold:
                converted_df[column_name] = datetime_result
                conversion_info.append({
                    'column': column_name,
                    'inferred_type': 'datetime',
                    'success_rate': datetime_success_rate,
                    'null_percentage': datetime_result.isna().mean()
                })
                continue
            
            # Keep as cleaned text if no other type works
            text_result = series.astype(str).str.strip().replace({"nan": None})
            converted_df[column_name] = text_result
            conversion_info.append({
                'column': column_name,
                'inferred_type': 'text',
                'success_rate': text_result.notna().mean(),
                'null_percentage': text_result.isna().mean()
            })
        
        # Create detailed report
        report_df = pd.DataFrame(conversion_info)
        report_df = report_df.sort_values('column').reset_index(drop=True)
        
        return converted_df, report_df


class DataManager:
    """Manages all data operations for the Real Estate Agent application."""
    
    def __init__(self):
        """Initialize the data manager."""
        self.inferencer = DataTypeInferencer()
    
    def setup_properties_table(self) -> bool:
        """Load and setup the properties table."""
        print("🏠 Setting up properties table...")
        
        # Check if data file exists
        if not os.path.exists(config.properties_csv):
            print(f"❌ Properties CSV file not found: {config.properties_csv}")
            print("Please ensure the data file exists in the correct location.")
            return False
        
        try:
            # Load and clean data
            print("📊 Loading property data...")
            df_data = pd.read_csv(config.properties_csv)
            df_clean_data = clean_dataframe(df_data)
            
            # Infer data types
            print("🔍 Inferring data types...")
            converted_df, report = self.inferencer.analyze_and_convert_dataframe(df_clean_data)
            
            print(f"✅ Data type conversion report:")
            print(report.to_string(index=False))
            
            # Load into database
            print("💾 Loading data into database...")
            db_service.create_properties_table(converted_df)
            
            print(f"✅ Successfully loaded {len(converted_df):,} rows into properties table.")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up properties table: {e}")
            return False
    
    def setup_vector_store(self) -> bool:
        """Setup the vector store with data dictionary."""
        print("🔍 Setting up vector store...")
        
        # Check if dictionary file exists
        if not os.path.exists(config.data_dictionary_csv):
            print(f"❌ Data dictionary CSV file not found: {config.data_dictionary_csv}")
            print("Please ensure the data dictionary file exists in the correct location.")
            return False
        
        try:
            # Setup vector store
            print("📚 Initializing vector store...")
            embeddings = HuggingFaceEmbeddings(model_name=config.embedding.model_name)
            vs = PGVector(
                connection=config.database.connection_string,
                embeddings=embeddings,
                collection_name=config.collection_name,
                use_jsonb=config.use_jsonb,
            )
            
            # Load dictionary
            print("📖 Loading data dictionary...")
            df = pd.read_csv(config.data_dictionary_csv)
            
            docs, ids = [], []
            for i, row in df.iterrows():
                field = str(row["field_name"]).strip()
                desc = str(row["description"]).strip()
                if field and desc:
                    page_content = f"{field}: {desc}"
                    docs.append(Document(page_content=page_content, metadata={"field": field}))
                    ids.append(f"dict::{field}")
            
            # Add documents to vector store
            print("💾 Adding documents to vector store...")
            vs.add_documents(docs, ids=ids)
            
            print(f"✅ Successfully loaded {len(docs)} dictionary entries into vector store.")
            return True
            
        except Exception as e:
            print(f"❌ Error setting up vector store: {e}")
            return False
    
    def test_setup(self) -> bool:
        """Test the setup by running a simple query."""
        print("🧪 Testing setup...")
        
        try:
            # Test database connection
            schema = db_service.get_schema_info(include_types=True)
            print(f"✅ Database connection successful. Schema: {schema[:100]}...")
            
            # Test Redis cache
            cache_manager.set("test", "setup", "test_value", 60)
            cached_value = cache_manager.get("test", "setup")
            if cached_value == "test_value":
                print("✅ Redis cache working properly.")
            else:
                print("⚠️ Redis cache not working properly.")
            
            # Test vector store
            embeddings = HuggingFaceEmbeddings(model_name=config.embedding.model_name)
            vs = PGVector(
                connection=config.database.connection_string,
                embeddings=embeddings,
                collection_name=config.collection_name,
                use_jsonb=config.use_jsonb,
            )
            
            # Test similarity search
            results = vs.similarity_search("What is suburb?", k=1)
            if results:
                print(f"✅ Vector store working. Sample result: {results[0].page_content[:100]}...")
            else:
                print("⚠️ Vector store is empty or not working properly.")
            
            return True
            
        except Exception as e:
            print(f"❌ Setup test failed: {e}")
            return False
    
    def load_all_data(self) -> bool:
        """Load all data (properties + dictionary)."""
        print("🚀 Real Estate Agent - Data Setup")
        print("=" * 50)
        
        # Check environment
        if not config.llm.api_key:
            print("⚠️ Warning: OPENAI_API_KEY not set. Some features may not work.")
            print("Set it with: export OPENAI_API_KEY='your-key-here'")
        
        success = True
        
        # Setup properties table
        if not self.setup_properties_table():
            success = False
        
        print()
        
        # Setup vector store
        if not self.setup_vector_store():
            success = False
        
        print()
        
        # Test setup
        if not self.test_setup():
            success = False
        
        print()
        print("=" * 50)
        
        if success:
            print("🎉 Setup completed successfully!")
            print("You can now run the Real Estate Agent:")
            print("  streamlit run app.py")
        else:
            print("❌ Setup completed with errors.")
            print("Please check the error messages above and try again.")
        
        return success


# Global data manager instance
data_manager = DataManager()


def main():
    """Main data setup function."""
    success = data_manager.load_all_data()
    if not success:
        sys.exit(1)


if __name__ == "__main__":
    main()
