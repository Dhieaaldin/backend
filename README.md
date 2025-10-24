# AgriTech Backend Services

This directory contains the backend services for the AgriTech project, which appears to be an agricultural technology solution focusing on irrigation, weather data, and crop monitoring.

## File Descriptions

### Main Services
- `main.py` - The main entry point of the application
- `main_service.py` - Core service implementation handling the main business logic
- `main_live_data.py` - Service for handling real-time data processing
- `main_mock_data.py` - Service providing mock data for testing and development

### Specialized Services
- `et0_service.py` - Service for calculating ET0 (Reference Evapotranspiration)
- `kc_service.py` - Service for handling crop coefficient (Kc) calculations
- `ndvi_service.py` - Service for processing Normalized Difference Vegetation Index (NDVI) data
- `savings_service.py` - Service for calculating water and resource savings
- `weather_server.py` - Weather data service providing meteorological information

### Frontend
- `test_irrigation.html` - HTML file for testing irrigation functionality, likely a development/testing interface

## Overview
This backend system appears to be designed for precision agriculture, incorporating various environmental and agricultural metrics:
- Weather data monitoring
- Evapotranspiration calculations
- Crop health monitoring through NDVI
- Water savings calculations
- Support for both live and mock data for development/testing purposes

The architecture separates concerns into distinct services, making the system modular and maintainable. Each service focuses on a specific aspect of the agricultural monitoring and management system.