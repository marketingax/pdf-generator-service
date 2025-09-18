# PDF Generation Service

A cloud-based PDF generation service that creates template PDFs via webhook and provides downloadable links. Built for Railway deployment with automatic file compression and cleanup.

## Features

- **Webhook-based PDF Generation**: Create PDFs via HTTP POST requests
- **Automatic PDF Compression**: Reduces file sizes using PyMuPDF
- **File Management**: Automatic cleanup of expired files (24-hour default)
- **Cloud-Ready**: Optimized for Railway deployment
- **Health Monitoring**: Built-in health check endpoint
- **Error Handling**: Comprehensive error handling and logging

## API Endpoints

### POST /webhook
Generate a new PDF template.

**Request Body:**
```json
{
  "title": "Your Template Title",
  "canva_link": "https://canva.com/design/your-template",
  "etsy_design_link": "https://etsy.com/listing/your-service" // optional
}
```

**Response:**
```json
{
  "success": true,
  "file_id": "uuid-here",
  "filename": "uuid-here.pdf",
  "download_url": "https://your-domain.com/download/uuid-here.pdf",
  "file_size": 1234567,
  "compressed": true,
  "expires_at": "2025-09-19T12:00:00Z"
}
```

### GET /download/{filename}
Download a generated PDF file.

### GET /status/{file_id}
Check the status of a generated file.

### GET /health
Health check endpoint for monitoring.

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `8080` | Server port |
| `UPLOAD_FOLDER` | `generated_pdfs` | PDF storage directory |
| `MAX_FILE_AGE_HOURS` | `24` | File expiration time |
| `COMPRESSION_ENABLED` | `true` | Enable PDF compression |
| `COMPRESSION_LEVEL` | `3` | Compression level (0-4) |
| `API_KEY` | `None` | Optional API key for authentication |

## Deployment

### Railway Deployment

1. Connect your repository to Railway
2. Railway will automatically detect the Python app
3. Environment variables are configured in `railway.toml`
4. The service will be available at your Railway domain

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run the application
python app.py
```

## Usage Examples

### Generate PDF with curl
```bash
curl -X POST https://your-domain.com/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Birthday Party Flyer",
    "canva_link": "https://canva.com/design/DAB123456",
    "etsy_design_link": "https://etsy.com/listing/custom-design"
  }'
```

### With API Key Authentication
```bash
curl -X POST https://your-domain.com/webhook \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-secret-key" \
  -d '{"title": "My Template", "canva_link": "https://canva.com/design/123"}'
```

## File Management

- Files are automatically cleaned up after 24 hours (configurable)
- Background cleanup runs every 30 minutes
- Compressed PDFs typically 20-60% smaller than originals
- Failed generations are logged but don't affect service availability

## Monitoring

- Health check available at `/health`
- Comprehensive logging for debugging
- File statistics and disk usage monitoring
- Automatic service restart on failures

## Security

- Optional API key authentication
- Input validation on all endpoints
- Safe file handling with UUID-based names
- No external binary dependencies

## Technical Details

- **Framework**: Flask 3.0
- **PDF Generation**: ReportLab
- **PDF Compression**: PyMuPDF (no Ghostscript required)
- **Image Processing**: Pillow
- **Deployment**: Railway with Nixpacks
- **Process Management**: Gunicorn

## License

MIT License - see LICENSE file for details.
