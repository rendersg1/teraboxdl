# Terabox Downloader Telegram Bot

A Telegram bot designed to efficiently extract and deliver Terabox video content, with advanced download and streaming capabilities.

## Key Features

- Automatic Terabox link extraction and processing
- Direct video sending and streaming functionality
- Multi-domain Terabox support
- Intelligent video download and streaming handling
- Enhanced error detection and user guidance

## Deploy to Koyeb

[![Deploy to Koyeb](https://www.koyeb.com/static/images/deploy/button.svg)](https://app.koyeb.com/deploy?type=git&repository=github.com/YOUR_USERNAME/YOUR_REPO_NAME&branch=main&name=terabox-bot)

## Environment Variables

The following environment variables are required:

- `TELEGRAM_BOT_TOKEN`: Your Telegram Bot Token (get it from @BotFather)
- `WEBHOOK_URL`: The public URL where your bot is deployed (e.g., https://terabox-bot-YOUR_NAME.koyeb.app)
- `SESSION_SECRET`: A random string used for Flask session encryption

## Detailed Deployment Steps for Koyeb

1. **Fork this Repository**:
   - Create a GitHub account if you don't already have one
   - Fork this repository to your GitHub account

2. **Create Koyeb Account**:
   - Sign up for a free account at [Koyeb](https://app.koyeb.com/auth/signup)
   - Verify your email address

3. **Deploy to Koyeb**:
   - Click the "Deploy to Koyeb" button above
   - Connect your GitHub account
   - Select your forked repository
   - Keep the main branch selected
   - Name your application (e.g., "terabox-bot")
   - Under "Environment variables" add:
     - Name: `TELEGRAM_BOT_TOKEN` | Secret: Your Telegram bot token
     - Name: `WEBHOOK_URL` | Secret: Leave blank for now (you'll update this after deployment)
     - Name: `SESSION_SECRET` | Secret: Generate a random string (e.g., `openssl rand -hex 16`)
   - Click "Deploy"

4. **Update Webhook URL**:
   - After deployment completes, Koyeb will assign a URL to your application
   - The URL will look like: `https://terabox-bot-YOUR_NAME.koyeb.app`
   - Go to Koyeb dashboard > Your App > Settings > Environment variables
   - Edit the `WEBHOOK_URL` variable to match your assigned URL
   - Save changes, this will automatically redeploy the application

5. **Set Up Webhook**:
   - Visit `https://terabox-bot-YOUR_NAME.koyeb.app/setup` in your browser
   - This will register your webhook URL with Telegram
   - You should see a success message confirming webhook registration

## Setup Instructions

1. **Create a Telegram Bot**:
   - Message [@BotFather](https://t.me/BotFather) on Telegram
   - Use the `/newbot` command to create a new bot
   - Save the token you receive

2. **Deploy to Koyeb**:
   - Click the "Deploy to Koyeb" button above
   - Connect your GitHub account if not already connected
   - Set your environment variables
   - Deploy the application

3. **Set up Webhook**:
   - Once deployed, visit `https://your-app-name.koyeb.app/setup` to set up the webhook
   - This connects your Telegram bot to your server

4. **Start Using**:
   - Send a Terabox link to your bot
   - The bot will process the link and send you the video or download link

## Local Development

To run this project locally:

1. Clone the repository:
   ```
   git clone https://github.com/YOUR_USERNAME/YOUR_REPO_NAME.git
   cd YOUR_REPO_NAME
   ```

2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

3. Set environment variables:
   ```
   export TELEGRAM_BOT_TOKEN=your_bot_token
   export WEBHOOK_URL=http://localhost:5000
   export SESSION_SECRET=your_secret_key
   ```

4. Run the application:
   ```
   python main.py
   ```

## Docker Support

This repository includes a Dockerfile for containerized deployment:

```
docker build -t terabox-bot .
docker run -p 5000:5000 \
  -e TELEGRAM_BOT_TOKEN=your_bot_token \
  -e WEBHOOK_URL=your_webhook_url \
  -e SESSION_SECRET=your_secret_key \
  terabox-bot
```

## Requirements

- Python 3.11+
- beautifulsoup4
- email-validator
- flask
- flask-sqlalchemy
- gunicorn
- psycopg2-binary
- python-telegram-bot
- requests
- trafilatura

## License

[MIT License](LICENSE)