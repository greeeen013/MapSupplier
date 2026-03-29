# Map Supplier App Instructions

## 1. Setup

### API Keys
1.  **Google Maps API Key**:
    *   Go to [Google Cloud Console](https://console.cloud.google.com/).
    *   Create a project.
    *   Enable **Places API** (specifically "Places API (New)" or standard Places API).
    *   Create Credentials -> API Key.
    *   Paste it into `.env` file as `GOOGLE_MAPS_API_KEY`.
    * zapnout street view static API https://console.cloud.google.com/apis/library/street-view-image-backend.googleapis.com?project=dhnfgbhtgrdaghdt
    * a Maps JavaScript API https://console.cloud.google.com/apis/library/maps-backend.googleapis.com?utm_source=Docs_EnableAPIs&utm_content=Docs_maps-backend&ref=%2Fmaps%2Fdocumentation%2Fjavascript%2Fget-api-key&_gl=1*1ju0we3*_ga*MTQwNDcyMTQ5My4xNzY3NDY0OTA4*_ga_NRWSTWS78N*czE3Njc0NjQ5MDgkbzEkZzEkdDE3Njc0NjY4ODckajIkbDAkaDA.&project=dhnfgbhtgrdaghdt

2.  **Gemini API Key**:
    *   Go to [Google AI Studio](https://makersuite.google.com/app/apikey).
    *   Create API Key.
    *   Paste it into `.env` as `GEMINI_API_KEY`.

### Email Setup (Gmail)
To send emails via Gmail, you need an **App Password**.
1.  Go to your **Google Account** settings.
2.  Go to **Security**.
3.  Enable **2-Step Verification** if not already enabled.
4.  In the search bar at the top, type **"App passwords"** and select it.
5.  Create a new app password (Name it e.g., "SupplierApp").
6.  Copy the 16-character password (without spaces).
7.  Open `.env` file:
    *   `EMAIL_USER=your.email@gmail.com`
    *   `EMAIL_PASSWORD=your_16_char_password`
    *   Leave `SMTP_SERVER` and `SMTP_PORT` as is for Gmail.

## 2. Running the App
Double-click `run.bat`.
It will install dependencies automatically on the first run and open the browser.
