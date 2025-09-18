# === Procfile ===
# Created: September 18, 2025 - 12:00 PM
# Purpose: Railway deployment configuration for PDF generation service
# Process Definition:
#   - web: Main Flask application server process
# Notes:
#   - Uses gunicorn for production-grade serving
#   - Configures workers and timeout for PDF processing

web: gunicorn --bind 0.0.0.0:$PORT --workers 2 --timeout 120 --max-requests 1000 --max-requests-jitter 50 app:app

"""
 * === Procfile ===
 * Updated: September 18, 2025 - 12:00 PM
 * Summary: Railway process configuration for production deployment
 * Key Components:
 *   - gunicorn: Production WSGI server
 *   - 2 workers: Balanced for PDF processing workload
 *   - 120s timeout: Allows for PDF generation and compression
 *   - Request limits: Prevents memory buildup
 * Dependencies:
 *   - Requires: gunicorn (included in requirements.txt)
 * Version History:
 *   v1.0 - Initial Railway configuration
 * Notes:
 *   - Optimized for PDF processing workloads
 *   - Automatic worker recycling for memory management
 */
