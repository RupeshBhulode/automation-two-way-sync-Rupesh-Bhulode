# Two-Way Sync: Google Sheets ↔ Trello

A Python-based automation that keeps lead data synchronized between Google Sheets (Lead Tracker) and Trello (Work Tracker) in real-time.

---

## Overview

This project creates a bidirectional sync between:
- **Google Sheets** - Acts as our Lead Tracker where we store lead information (name, email, status, source, notes)
- **Trello** - Acts as our Work Tracker where we manage tasks related to each lead

The sync runs continuously, ensuring that changes in either system are reflected in the other within seconds.

### What It Does

- When you add or update a lead in Google Sheets → A Trello card is automatically created/updated
- When you move a Trello card between lists → The lead status in Google Sheets updates automatically
- When you edit card details in Trello → The corresponding lead data in Google Sheets is updated
- Handles edge cases like archiving cards, changing statuses to "LOST", and prevents duplicate entries

---

## Architecture & Flow

```
Google Sheets (Lead Tracker)          Trello Board (Work Tracker)
┌─────────────────────────┐          ┌─────────────────────────┐
│ ID | Name | Email       │          │   TODO List             │
│ Category | Note | Source│   sync   │   ├─ Card: John Doe    │
│                         │  <-----> │   └─ (LeadID: L001)     │
│ L001 | John | john@...  │          │                         │
│ new | Follow up | Web   │          │   INPROGRESS List       │
└─────────────────────────┘          │   DONE List             │
                                      └─────────────────────────┘

                    ↕
              sync_logic.py
           (Bidirectional Sync)
                    ↕
              data.json
         (Mapping & State Storage)
```

### Status Mapping

**Google Sheets → Trello:**
- `new` → `TODO` list
- `contacted` → `INPROGRESS` list
- `qualified` → `DONE` list
- `lost` → Card is archived (removed from board)

**Trello → Google Sheets:**
- `TODO` list → `new` category
- `INPROGRESS` list → `contacted` category
- `DONE` list → `qualified` category
- Card archived/deleted → `LOST` category

---

## Setup Instructions

### Prerequisites
- Python 3.8 or higher
- A Google account
- A Trello account (free)

### Step 1: Clone the Repository
```bash
git clone automation-two-way-sync-Rupesh-Bhulode
cd automation-two-way-sync
```

### Step 2: Install Dependencies
```bash
pip install -r requirements.txt
```

The `requirements.txt` includes:
```
gspread
google-auth
requests
python-dotenv
```

### Step 3: Set Up Google Sheets

1. **Create a Google Sheet:**
   - Go to [Google Sheets](https://sheets.google.com)
   - Create a new spreadsheet
   - Add headers in the first row: `id`, `name`, `email`, `category`, `note`, `source`
   - Add some sample data (category should be: new, contacted, qualified, or lost)

2. **Enable Google Sheets API:**
   - Go to [Google Cloud Console](https://console.cloud.google.com)
   - Create a new project or select an existing one
   - Enable the "Google Sheets API"
   - Go to "Credentials" → "Create Credentials" → "Service Account"
   - Download the JSON key file and save it as `credentials.json` in your project root
   - Copy the service account email (looks like `xxx@xxx.iam.gserviceaccount.com`)
   - Share your Google Sheet with this email address (give it Editor access)

3. **Get your Sheet ID:**
   - From your Google Sheet URL: `https://docs.google.com/spreadsheets/d/SHEET_ID_HERE/edit`
   - Copy the `SHEET_ID_HERE` part

### Step 4: Set Up Trello

1. **Create a Trello Board:**
   - Go to [Trello](https://trello.com)
   - Create a new board (any name you like)
   - The sync will automatically create three lists: TODO, INPROGRESS, DONE

2. **Get API Credentials:**
   - Visit [Trello API Key](https://trello.com/app-key)
   - Copy your API Key
   - Click on "Token" link to generate a token
   - Copy the Token

3. **Get Board ID:**
   - Open your Trello board
   - Add `.json` to the end of the URL and press Enter
   - Look for `"id":` near the top - that's your board ID

### Step 5: Configure Environment Variables

Create a `.env` file in the project root:

```bash
# Google Sheets
SHEET_ID=your_sheet_id_here
CREDENTIALS_FILE=credentials.json

# Trello
TRELLO_API_KEY=your_trello_api_key
TRELLO_TOKEN=your_trello_token
TRELLO_BOARD_ID=your_board_id

# Sync Settings
DATA_JSON_PATH=data.json
POLL_INTERVAL=5
```

**⚠️ IMPORTANT:** Never commit `.env` or `credentials.json` to Git! Add them to `.gitignore`.

---

## Usage

### Running the Sync

Simply run:
```bash
python main.py
```

The script will:
1. Connect to both Google Sheets and Trello
2. Perform an initial sync
3. Continue running and checking for changes every 5 seconds (configurable via `POLL_INTERVAL`)

### Testing the Sync

**Test Sheet → Trello:**
1. Open your Google Sheet
2. Add a new row: `L005 | Jane Smith | jane@example.com | new | Test lead | Website`
3. Wait 5 seconds
4. Check Trello - you should see a new card "Jane Smith (LeadID: L005)" in the TODO list

**Test Trello → Sheet:**
1. Open your Trello board
2. Drag a card from TODO to INPROGRESS
3. Wait 5 seconds
4. Check Google Sheets - the category should change from "new" to "contacted"

**Test Field Updates:**
1. Edit a Trello card's description (change email, note, or source)
2. Wait 5 seconds
3. Check Google Sheets - the corresponding fields should update

**Test Archiving:**
1. In Google Sheets, change a lead's category to "lost"
2. Wait 5 seconds
3. The Trello card should be archived (disappear from the board)

### Stopping the Sync

Press `Ctrl+C` to stop the script.

---

## Project Structure

```
.
├── lead_client.py          # Google Sheets API client
├── task_client.py          # Trello API client
├── sync_logic.py           # Core sync logic (bidirectional)
├── main.py                 # Entry point with polling loop
├── data.json              # State file (auto-generated)
├── credentials.json       # Google service account key (gitignored)
├── .env                   # Environment variables (gitignored)
├── requirements.txt       # Python dependencies
└── README.md             # This file
```

---

## How It Works

### Idempotency & Deduplication

The system maintains a mapping file (`data.json`) that tracks:
- Which lead ID corresponds to which Trello card ID
- The last known state of each lead/card

This ensures:
- Running the sync multiple times won't create duplicate cards
- Updates are only made when actual changes occur
- The system can recover gracefully after crashes

### Error Handling

- **API failures:** Each API call is wrapped in try-catch blocks with logging
- **Rate limiting:** The system uses polling with configurable intervals to avoid hitting rate limits
- **Bad data:** Empty or invalid records are skipped with warnings logged
- **Network issues:** Errors are logged but don't crash the entire sync process

### Logging

All operations are logged with timestamps:
- `INFO`: Normal operations (card created, field updated, etc.)
- `ERROR`: Failed operations with details
- `EXCEPTION`: Critical errors with full stack traces

Check the console output to see what's happening in real-time.

---

## Assumptions & Limitations

### Assumptions Made
- Lead IDs in Google Sheets are unique and don't change
- Category values are lowercase: "new", "contacted", "qualified", "lost"
- The Google Sheet has headers: id, name, email, category, note, source
- Users won't manually delete cards from Trello without updating the sheet

### Known Limitations
- **Polling-based:** Uses polling instead of webhooks (Trello webhooks require a publicly accessible endpoint)
- **Single sheet:** Only syncs the first worksheet in the spreadsheet
- **No conflict resolution:** If both systems are updated simultaneously, last-write-wins
- **Manual Trello deletions:** If you manually delete a card from Trello, the lead will be marked as "LOST" on next sync
- **Rate limits:** Google Sheets has rate limits - sync interval should not be too aggressive

### Not Implemented (Due to Time)
- Real-time webhooks (would require hosted server)
- Conflict detection and resolution
- Batch updates (currently one-by-one)
- Historical change tracking
- User authentication/multi-user support
- Undo functionality
- UI dashboard

---

## AI Usage Notes

### Tools Used
- **ChatGPT (GPT-4)** - For code structure planning, API documentation clarification, and debugging

### Where AI Helped
1. **API Documentation Summary:** Used ChatGPT to quickly understand Trello and Google Sheets API endpoints instead of reading lengthy docs
2. **Regex Pattern:** Generated the email extraction regex in `task_client.py`
3. **Error Handling Patterns:** Got suggestions for try-catch structure in `sync_logic.py`
4. **Code Comments:** Generated initial comments which I then refined

### What I Changed/Rejected
**Example:** ChatGPT initially suggested using a database (SQLite) for the state management instead of `data.json`. I rejected this because:
- Added unnecessary complexity for a small project
- JSON is human-readable and easier to debug
- No concurrent access concerns with single-threaded polling
- Keeps dependencies minimal

I also modified AI-generated logging statements to be more specific and actionable.

---

## Video Demo

**[📹 Watch the Demo Video](YOUR_GOOGLE_DRIVE_LINK_HERE)**

The video covers:
- Quick architecture overview
- Code walkthrough of key components
- Setup process demonstration
- Live sync demo (Sheet → Trello and Trello → Sheet)

---

## Troubleshooting

**"Failed to authenticate with Google Sheets"**
- Make sure `credentials.json` is in the project root
- Verify you've shared the sheet with the service account email

**"Trello list not found"**
- The script auto-creates lists - make sure the board ID is correct
- Check that your API key and token are valid

**"No module named 'gspread'"**
- Run `pip install -r requirements.txt`

**Sync is slow or not happening**
- Check the `POLL_INTERVAL` in `.env` (lower = faster, but watch rate limits)
- Look at console logs for errors

---

## Future Enhancements

If I had more time, I'd add:
- Webhook support for real-time updates
- Web dashboard to view sync status
- Conflict resolution strategy
- Support for custom field mappings
- Batch API calls for better performance
- Docker containerization
- Comprehensive test suite

---

## License

This is a take-home assignment project. Feel free to use it for learning purposes.

---

## Contact

If you have questions about the implementation, please reach out via GitHub issues or the interview process.

Happy syncing! 🚀
