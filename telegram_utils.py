import os
import re
import logging
import requests
import urllib.parse
from terabox_utils import extract_terabox_download_link

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Get bot token from environment
TELEGRAM_BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")

# Telegram API base URL
TELEGRAM_API_URL = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}"

def send_message(chat_id, text, parse_mode="HTML"):
    """
    Send a message to a specific Telegram chat.
    
    Args:
        chat_id (int): The chat ID to send the message to
        text (str): The message text to send
        parse_mode (str): The parse mode for the message (HTML or Markdown)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            logger.debug(f"Message sent successfully to chat {chat_id}")
            return True
        else:
            logger.error(f"Failed to send message: {response_data}")
            return False
            
    except Exception as e:
        logger.error(f"Error sending message: {str(e)}")
        return False


def send_video(chat_id, video_url, caption=None, parse_mode=None, existing_msg_id=None):
    """
    Send a video to a specific Telegram chat by URL.
    
    Args:
        chat_id (int): The chat ID to send the video to
        video_url (str): The URL of the video to send
        caption (str, optional): Caption for the video
        parse_mode (str, optional): Parse mode for the caption
        existing_msg_id (int, optional): ID of an existing progress message to update
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        payload = {
            'chat_id': chat_id,
            'video': video_url
        }
        
        if caption:
            payload['caption'] = caption
            
        if parse_mode:
            payload['parse_mode'] = parse_mode
        
        # Use existing message ID if provided, otherwise don't create a new one
        # (We're assuming the caller has already created a progress message)
        status_msg_id = existing_msg_id
        
        # Update progress to show video is being sent
        if status_msg_id:
            try:
                update_processing_message(chat_id, status_msg_id, 70)
            except Exception as e:
                logger.error(f"Error updating progress message: {e}")
        
        # Send the video
        response = requests.post(f"{TELEGRAM_API_URL}/sendVideo", json=payload)
        response_data = response.json()
        
        # Update progress to 100% (done)
        if status_msg_id:
            try:
                update_processing_message(chat_id, status_msg_id, 100)
                # Delete the progress message after successful upload
                delete_message(chat_id, status_msg_id)
            except Exception as e:
                logger.error(f"Error updating final progress: {e}")
        
        if response.status_code == 200 and response_data.get('ok'):
            logger.debug(f"Video sent successfully to chat {chat_id}")
            return True
        else:
            error_message = response_data.get('description', 'Unknown error')
            logger.error(f"Failed to send video: {error_message}")
            
            # If status message exists, update it with error
            if status_msg_id:
                try:
                    edit_message_text(
                        chat_id, 
                        status_msg_id, 
                        f"❌ <b>Error:</b> Could not send video directly.\n\n" +
                        ("The video file is too large (max 50MB)." if "file is too large" in error_message.lower() else f"Error: {error_message}")
                    )
                except Exception as e:
                    logger.error(f"Error updating error message: {e}")
                    # If we can't update, try sending a new message
                    if "file is too large" in error_message.lower():
                        send_message(chat_id, "❌ <b>Error:</b> The video file is too large to send directly through Telegram (max 50MB).\n\nPlease use the download link instead.")
                    else:
                        send_message(chat_id, f"❌ <b>Error sending video:</b> {error_message}\n\nPlease use the download link instead.")
            else:
                # If there's no status message, send a new error message
                if "file is too large" in error_message.lower():
                    send_message(chat_id, "❌ <b>Error:</b> The video file is too large to send directly through Telegram (max 50MB).\n\nPlease use the download link instead.")
                else:
                    send_message(chat_id, f"❌ <b>Error sending video:</b> {error_message}\n\nPlease use the download link instead.")
            
            return False
            
    except Exception as e:
        logger.error(f"Error sending video: {str(e)}")
        send_message(chat_id, f"❌ <b>Error:</b> Could not send video file. Please use the download link instead.")
        return False


def send_processing_message(chat_id, progress=0):
    """
    Send an animated processing message with progress bar.
    
    Args:
        chat_id (int): The chat ID to send the message to
        progress (int): Progress percentage (0-100)
        
    Returns:
        dict: The API response if successful, None otherwise
    """
    try:
        # Create progress bar
        progress_bar = create_progress_bar(progress)
        
        # Create a more visually appealing processing message
        text = (
            f"🚀 <b>Processing Your Terabox Video</b> 🚀\n\n"
            f"{progress_bar} <b>{progress}%</b>\n\n"
            f"{'🔍' if progress < 30 else '✅'} <b>Getting video info</b>: {'In progress...' if progress < 30 else 'Complete'}\n"
            f"{'⏳' if progress < 30 else '🔍' if progress < 70 else '✅'} <b>Processing video</b>: {'Waiting...' if progress < 30 else 'In progress...' if progress < 70 else 'Complete'}\n"
            f"{'⏳' if progress < 70 else '🔍' if progress < 100 else '✅'} <b>Preparing delivery</b>: {'Waiting...' if progress < 70 else 'In progress...' if progress < 100 else 'Complete'}\n\n"
            f"<i>Please wait, your video will be ready soon...</i>"
        )
        
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(f"{TELEGRAM_API_URL}/sendMessage", json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            logger.debug(f"Processing message sent successfully to chat {chat_id}")
            return response_data
        else:
            logger.error(f"Failed to send processing message: {response_data}")
            return None
            
    except Exception as e:
        logger.error(f"Error sending processing message: {str(e)}")
        return None


def update_processing_message(chat_id, message_id, progress):
    """
    Update the processing message with new progress.
    
    Args:
        chat_id (int): The chat ID
        message_id (int): The message ID to update
        progress (int): Progress percentage (0-100)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Create progress bar
        progress_bar = create_progress_bar(progress)
        
        # Create a more visually appealing processing message
        text = (
            f"🚀 <b>Processing Your Terabox Video</b> 🚀\n\n"
            f"{progress_bar} <b>{progress}%</b>\n\n"
            f"{'🔍' if progress < 30 else '✅'} <b>Getting video info</b>: {'In progress...' if progress < 30 else 'Complete'}\n"
            f"{'⏳' if progress < 30 else '🔍' if progress < 70 else '✅'} <b>Processing video</b>: {'Waiting...' if progress < 30 else 'In progress...' if progress < 70 else 'Complete'}\n"
            f"{'⏳' if progress < 70 else '🔍' if progress < 100 else '✅'} <b>Preparing delivery</b>: {'Waiting...' if progress < 70 else 'In progress...' if progress < 100 else 'Complete'}\n\n"
            f"<i>Please wait, your video will be ready soon...</i>"
        )
        
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        
        response = requests.post(f"{TELEGRAM_API_URL}/editMessageText", json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            logger.debug(f"Processing message updated successfully for chat {chat_id}")
            return True
        else:
            logger.error(f"Failed to update processing message: {response_data}")
            return False
            
    except Exception as e:
        logger.error(f"Error updating processing message: {str(e)}")
        return False


def edit_message_text(chat_id, message_id, text, parse_mode="HTML"):
    """
    Edit a message text.
    
    Args:
        chat_id (int): The chat ID
        message_id (int): The message ID to edit
        text (str): The new text
        parse_mode (str): The parse mode for the text
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        payload = {
            'chat_id': chat_id,
            'message_id': message_id,
            'text': text,
            'parse_mode': parse_mode
        }
        
        response = requests.post(f"{TELEGRAM_API_URL}/editMessageText", json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            logger.debug(f"Message edited successfully for chat {chat_id}")
            return True
        else:
            logger.error(f"Failed to edit message: {response_data}")
            return False
            
    except Exception as e:
        logger.error(f"Error editing message: {str(e)}")
        return False


def delete_message(chat_id, message_id):
    """
    Delete a message.
    
    Args:
        chat_id (int): The chat ID
        message_id (int): The message ID to delete
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        payload = {
            'chat_id': chat_id,
            'message_id': message_id
        }
        
        response = requests.post(f"{TELEGRAM_API_URL}/deleteMessage", json=payload)
        response_data = response.json()
        
        if response.status_code == 200 and response_data.get('ok'):
            logger.debug(f"Message deleted successfully for chat {chat_id}")
            return True
        else:
            logger.error(f"Failed to delete message: {response_data}")
            return False
            
    except Exception as e:
        logger.error(f"Error deleting message: {str(e)}")
        return False


def create_progress_bar(progress, length=10):
    """
    Create a text-based progress bar.
    
    Args:
        progress (int): Progress percentage (0-100)
        length (int): Length of the progress bar
        
    Returns:
        str: Text-based progress bar
    """
    # Calculate the number of filled and empty blocks
    filled_length = int(length * progress / 100)
    empty_length = length - filled_length
    
    # Create a more visually appealing progress bar with different emojis
    if progress < 30:
        # Initial stage - blue
        bar = '🟦' * filled_length + '⬜' * empty_length
    elif progress < 70:
        # Middle stage - purple
        bar = '🟪' * filled_length + '⬜' * empty_length
    else:
        # Final stage - green
        bar = '🟩' * filled_length + '⬜' * empty_length
    
    return bar

def process_message(message_text, chat_id):
    """
    Process incoming messages and generate appropriate responses.
    
    Args:
        message_text (str): The text of the message to process
        chat_id (int): The chat ID where the message originated
        
    Returns:
        str: The response message to send back
    """
    # Handle commands
    if message_text.startswith('/'):
        return handle_command(message_text.lower())
    
    # Check if the message contains a Terabox link
    terabox_domains = [
        'terabox.com', 
        'teraboxapp.com', 
        '1024terabox.com', 
        'terabox.app', 
        'www.terabox.app', 
        'terabox.hnn.workers.dev', 
        'dm.terabox.com',
        'teraboxshare.com'
    ]
    if any(domain in message_text for domain in terabox_domains):
        logger.info(f"Processing Terabox link: {message_text}")
        
        # Extract the Terabox link
        terabox_link = extract_url_from_text(message_text)
        if not terabox_link:
            return "❌ Could not find a valid Terabox link in your message. Please make sure the URL is correct."
        
        # Send animated processing message
        status_msg = send_processing_message(chat_id, 0)
        status_msg_id = None
        if not status_msg:
            # Fallback to simple message if animated message fails
            send_message(chat_id, "🔄 Processing your Terabox link... Please wait.")
        else:
            status_msg_id = status_msg.get('result', {}).get('message_id')
        
        # Define progress callback
        def update_progress(progress, step=None):
            if status_msg_id:
                try:
                    update_processing_message(chat_id, status_msg_id, progress)
                except Exception as e:
                    logger.error(f"Error updating progress: {e}")
                
        # Get the direct download link with progress updates
        result = extract_terabox_download_link(terabox_link, progress_callback=update_progress)
        
        if result['success']:
            # Create a caption with both video info and download link
            video_caption = (
                f"📹 <b>{result['filename']}</b> ({result['size']})\n\n"
                f"📥 <b>Download Link:</b>\n"
                f"<a href='{result['url']}'>{result['filename']}</a>\n\n"
                f"<i>Direct link expires in a few hours.</i>"
            )
            
            # Always try to send the video directly first - pass the existing status message ID
            if send_video(
                chat_id, 
                result['url'], 
                caption=video_caption, 
                parse_mode="HTML",
                existing_msg_id=status_msg_id
            ):
                return ""  # Return empty string instead of None to prevent "null" message
            else:
                # In case of error, the send_video function already sends an error message
                # Just provide a reliable download link as a fallback
                
                # Generate a more reliable download link
                response = (
                    f"✅ <b>Download Link Generated:</b>\n\n"
                    f"<b>Filename:</b> {result['filename']}\n"
                    f"<b>Size:</b> {result['size']}\n\n"
                    f"<b>📥 Download Link:</b>\n"
                    f"<a href='{result['url']}'>{result['filename']}</a>\n\n"
                    f"<i>⚠️ Important: This direct download link expires in a few hours. Download soon!</i>\n\n"
                    f"<i>Note: The file is too large to send directly through Telegram (max 50MB). Please use the download link above.</i>\n\n"
                    f"<i>💡 Tip: Copy the link and paste it in your browser's address bar for better download reliability.</i>"
                )
                return response
        else:
            return f"❌ Error: {result['error']}"
    
    # Default response for unrecognized messages
    return (
        "Please send me a Terabox link to extract the direct download URL.\n\n"
        "Type /help to see available commands."
    )

def handle_command(command):
    """
    Handle bot commands.
    
    Args:
        command (str): The command to handle
        
    Returns:
        str: The response to the command
    """
    if command == '/start':
        return (
            "👋 <b>Welcome to the Terabox Downloader Bot!</b>\n\n"
            "I can help you download videos from Terabox URLs.\n\n"
            "Simply send me a Terabox link, and I'll send you the video directly with a download link included. "
            "For files larger than 50MB, I'll provide a direct download link instead.\n\n"
            "To improve download success, you can copy the download link and paste it directly in your browser's address bar.\n\n"
            "Type /help to see available commands."
        )
    
    elif command == '/help':
        return (
            "📖 <b>Terabox Downloader Bot - Help</b>\n\n"
            "<b>Available Commands:</b>\n"
            "/start - Start the bot\n"
            "/help - Show this help message\n"
            "/about - About this bot\n\n"
            "<b>How to use:</b>\n"
            "1. Send me a Terabox link\n"
            "2. Wait a moment while I process it with animated progress\n"
            "3. I'll send you the video directly with a download link\n"
            "4. For larger files (over 50MB), you'll get a direct download link instead\n\n"
            "<i>Note: Direct links expire in a few hours</i>\n"
            "<i>Note: Video files include download links in the caption</i>\n"
            "<i>Note: For better download experience, copy the link and paste it directly in your browser</i>"
        )
    
    elif command == '/about':
        return (
            "ℹ️ <b>About Terabox Downloader Bot</b>\n\n"
            "This bot helps you download videos directly from Terabox URLs.\n\n"
            "It works by processing the Terabox page and extracting the direct video file, "
            "allowing you to download it directly without going through the Terabox website.\n\n"
            "All videos come with a direct download link in the caption. "
            "For larger files (over 50MB), the bot will provide a direct download link instead, "
            "which you can use to download the file to your device.\n\n"
            "For the best download experience, copy the download link and paste it directly in your browser's address bar.\n\n"
            "The animated progress bar shows real-time status of your video processing.\n\n"
            "<i>Made with ❤️</i>"
        )
    
    # Unknown command
    return "Unknown command. Type /help to see available commands."

def extract_url_from_text(text):
    """
    Extract a Terabox URL from a text message.
    
    Args:
        text (str): The text to extract the URL from
        
    Returns:
        str: The extracted URL or None if no URL found
    """
    # List of known Terabox domains
    terabox_domains = [
        'terabox.com', 
        'teraboxapp.com', 
        '1024terabox.com',
        'terabox.app',
        'www.terabox.app',
        'terabox.hnn.workers.dev',
        'dm.terabox.com',
        'd-jp02-cpt.terabox.com',
        'd-jp02-zen.terabox.com',
        'teraboxshare.com'
    ]
    
    # First try to match a direct download URL (they can be very long)
    direct_download_patterns = [
        r'(https?://d\-[a-z0-9\-]+\.terabox\.com/file/[^\s]+)',
    ]
    
    for pattern in direct_download_patterns:
        match = re.search(pattern, text)
        if match:
            return match.group(1)
    
    # If no direct download URL is found, try word by word
    words = text.split()
    for word in words:
        if any(domain in word for domain in terabox_domains):
            # Clean up the URL by removing any trailing characters
            url = word
            for char in ['.', ',', '!', '?', ')']:
                if url.endswith(char):
                    url = url[:-1]
            return url
            
    return None
