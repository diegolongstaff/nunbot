# Buscador de Códigos NUN

## Overview

This is a Streamlit-based medical procedure code search application that helps users find and lookup NUN (Nomenclador Único Nacional) procedure codes. The application provides a web interface for searching medical procedures with natural language queries using OpenAI's API for intelligent search capabilities.

## User Preferences

Preferred communication style: Simple, everyday language.

## System Architecture

### Frontend Architecture
- **Framework**: Streamlit - chosen for rapid development of data-driven web applications
- **Layout**: Wide layout with collapsed sidebar for maximum content visibility
- **Caching**: Utilizes Streamlit's caching decorators (`@st.cache_resource`, `@st.cache_data`) for performance optimization

### Backend Architecture
- **Runtime**: Python-based single-file application
- **Data Processing**: Pandas for CSV data manipulation and cleaning
- **AI Integration**: OpenAI API for intelligent search capabilities
- **Logging**: Built-in Python logging for debugging and monitoring

## Key Components

### Data Management
- **CSV Data Loader**: Loads NUN procedures from `nun_procedimientos.csv`
- **Data Cleaning**: Standardizes column names and handles currency formatting
- **Caching Strategy**: Data is cached to prevent repeated file reads

### AI Integration
- **OpenAI Client**: Initialized with API key from environment variables
- **Two-Step Search Process**: First determines region, then searches within filtered subset
- **Token Optimization**: Compact text format (CODE - DESCRIPTION) instead of JSON reduces token usage by ~70%
- **Anatomical Region Awareness**: Includes medical glossary for region identification
- **Resource Caching**: Client instance is cached for performance
- **Error Handling**: Graceful handling of missing API keys and token limits

### User Interface
- **Page Configuration**: Medical-themed with hospital icon
- **Error Display**: Clear error messages for configuration issues
- **Responsive Design**: Wide layout for better data visualization

## Data Flow

1. **Application Startup**: 
   - Initialize OpenAI client with environment variable
   - Load and clean CSV data with pandas
   - Apply caching for performance

2. **Data Processing**:
   - Clean column names by removing whitespace
   - Convert currency columns (Cirujano, Ayudantes, Total) to numeric format
   - Handle missing values with appropriate defaults

3. **Search Process** (Two-Step Approach):
   - **Step 1:** AI determines anatomical region using medical glossary (lightweight API call)
   - **Step 2:** Filter procedures by identified region to reduce dataset size
   - **Step 3:** AI searches within filtered subset for specific codes (optimized API call)
   - Results prioritized by region match and relevance
   - Display formatted results to user with confidence scores

## External Dependencies

### Required Libraries
- `streamlit`: Web application framework
- `pandas`: Data manipulation and analysis
- `openai`: OpenAI API integration
- `logging`: Application logging

### Data Sources
- `nun_procedimientos.csv`: Main procedures database
- `attached_assets/nun_procedimientos_1752847693324.json`: JSON backup/export of procedures

### External Services
- **OpenAI API**: For intelligent search capabilities with anatomical region awareness
- **Environment Variables**: `OPENAI_API_KEY` for API authentication

## Deployment Strategy

### Environment Requirements
- Python runtime with required dependencies
- OpenAI API key configured as environment variable
- CSV data file accessible in application directory

### Configuration
- Page optimized for wide layout viewing
- Logging configured at INFO level for production monitoring
- Error handling for missing configurations prevents application crashes

### Data Security
- API key stored in environment variables (not hardcoded)
- Graceful error handling prevents key exposure
- No sensitive data stored in repository

### Performance Considerations
- Caching implemented for both data loading and API client initialization
- Single CSV file approach for simplicity
- Streamlit's built-in optimization features utilized