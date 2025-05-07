import os
import logging
import requests
import urllib.parse
from flask import Flask, request, jsonify, render_template, redirect
from telegram_utils import send_message, process_message
import terabox_utils

# Configure logging
logging.basicConfig(level=logging.DEBUG, 
                   format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Create Flask app
app = Flask(__name__)
app.secret_key = os.environ.get("SESSION_SECRET")

# Get Telegram bot token from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
if not TELEGRAM_BOT_TOKEN:
    logger.error("No TELEGRAM_BOT_TOKEN environment variable set!")

# Set webhook URL from environment variables
WEBHOOK_URL = os.environ.get("WEBHOOK_URL")

@app.route('/')
def index():
    """Landing page for the application."""
    # Extract the bot username from the token (format: 123456:ABC-DEF)
    bot_info = None
    try:
        response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe")
        bot_info = response.json()
        logger.debug(f"Bot info: {bot_info}")
    except Exception as e:
        logger.error(f"Error getting bot info: {str(e)}")
    
    bot_username = ""
    if bot_info and bot_info.get("ok"):
        bot_username = bot_info.get("result", {}).get("username", "")
    
    return render_template('index.html', bot_username=bot_username)

@app.route(f'/webhook/{TELEGRAM_BOT_TOKEN}', methods=['POST'])
def webhook():
    """
    Handle incoming webhook requests from Telegram.
    Process the message and respond accordingly.
    """
    try:
        data = request.get_json()
        logger.debug(f"Received webhook data: {data}")
        
        # Process the incoming message
        if 'message' in data:
            chat_id = data['message']['chat']['id']
            
            # Extract the user's message text if available
            if 'text' in data['message']:
                message_text = data['message']['text']
                
                # Process the message and get a response
                response = process_message(message_text, chat_id)
                
                # Send the response back to the user only if not empty
                if response and response.strip():
                    send_message(chat_id, response)
            else:
                # If no text is found, send a generic response
                send_message(chat_id, "I can only process text messages. Please send me a Terabox link.")
                
        return jsonify({"status": "ok"})
    
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

@app.route('/set_webhook', methods=['GET'])
def set_webhook():
    """
    Set the webhook URL for the Telegram bot.
    This only needs to be called once or when the URL changes.
    """
    webhook_url = f"{WEBHOOK_URL}/webhook/{TELEGRAM_BOT_TOKEN}"
    success = terabox_utils.set_telegram_webhook(TELEGRAM_BOT_TOKEN, webhook_url)
    
    if success:
        return jsonify({"status": "success", "message": "Webhook set successfully"})
    else:
        return jsonify({"status": "error", "message": "Failed to set webhook"})

@app.route('/player')
def player():
    """Video player page for streaming Terabox videos."""
    video_url = request.args.get('url')
    filename = request.args.get('filename', 'Video')
    filesize = request.args.get('size', 'Unknown')
    
    if not video_url:
        return redirect('/')
    
    # Validate if the URL is a Terabox URL
    # This is just a basic check, actual validation would depend on your URL patterns
    if 'terabox' not in video_url and 'd-' not in video_url:
        return redirect('/')
    
    return render_template(
        'player.html', 
        video_url=video_url, 
        filename=filename,
        filesize=filesize
    )

@app.route('/health', methods=['GET'])
def health_check():
    """Simple health check endpoint."""
    return jsonify({"status": "healthy"})

@app.route('/setup')
def setup():
    """Setup page to initialize the bot and webhook."""
    # Try to initialize webhook when setup page is visited
    webhook_url = f"{WEBHOOK_URL}/webhook/{TELEGRAM_BOT_TOKEN}"
    logger.info(f"Setting webhook URL: {webhook_url}")
    
    bot_info = None
    try:
        # Get Bot Info
        info_response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/getMe")
        bot_info = info_response.json()
        
        # Set webhook
        webhook_response = requests.get(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/setWebhook?url={webhook_url}")
        webhook_result = webhook_response.json()
        
        return jsonify({
            "status": "success", 
            "bot_info": bot_info, 
            "webhook_result": webhook_result
        })
        
    except Exception as e:
        logger.error(f"Error in setup: {str(e)}")
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Start the Flask app
    app.run(host='0.0.0.0', port=5000, debug=True)
