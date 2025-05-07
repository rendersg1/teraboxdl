import os
import re
import json
import logging
import requests
import base64
import random
from urllib.parse import unquote, urlparse, parse_qs, quote
from bs4 import BeautifulSoup

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Constants
USER_AGENT = "Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36"
HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.9,id;q=0.8",
    "Accept-Encoding": "gzip, deflate, br",
    "Connection": "keep-alive",
    "Upgrade-Insecure-Requests": "1"
}

def normalize_url(url):
    """
    Normalize the Terabox URL to a standard format.
    
    Args:
        url (str): The Terabox URL to normalize
    
    Returns:
        str: The normalized URL
    """
    # Remove any additional path components or query parameters
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}{parsed_url.path}"
    
    # Replace teraboxapp.com with terabox.com if needed
    if 'teraboxapp.com' in base_url:
        base_url = base_url.replace('teraboxapp.com', 'terabox.com')
    
    return base_url

def extract_surl_parameter(url):
    """
    Extract the surl parameter from the URL.
    
    Args:
        url (str): The URL to extract the surl parameter from
    
    Returns:
        str: The surl parameter value or None if not found
    """
    parsed_url = urlparse(url)
    if parsed_url.query:
        query_params = parse_qs(parsed_url.query)
        if 'surl' in query_params:
            return query_params['surl'][0]
    
    # For URLs like terabox.com/s/1XXXX
    path_parts = parsed_url.path.split('/')
    if len(path_parts) >= 3 and path_parts[1] == 's':
        return path_parts[2]
    
    return None

class TeraboxFile:
    """
    Class to handle extraction of file information from Terabox URLs.
    Based on the implementation from TeraDL by Dapunta.
    """
    
    def __init__(self):
        """Initialize with session and default result structure"""
        self.r = requests.Session()
        self.headers = HEADERS
        self.result = {
            'status': 'failed', 
            'sign': '', 
            'timestamp': '', 
            'shareid': '', 
            'uk': '', 
            'list': []
        }
    
    def search(self, url):
        """Main entry point - process URL, get file info and sign"""
        try:
            req = self.r.get(url, allow_redirects=True)
            if req.status_code != 200:
                return False
                
            # Extract shorturl/surl from URL
            match = re.search(r'surl=([^ &]+)', str(req.url))
            if match:
                self.short_url = match.group(1)
            else:
                # Try another method to find surl
                self.short_url = extract_surl_parameter(url)
                if not self.short_url:
                    return False
                    
            logger.debug(f"Found surl: {self.short_url}")
            
            # Get main file and sign
            self.getMainFile()
            self.getSign()
            return True
        except Exception as e:
            logger.error(f"Error searching Terabox URL: {str(e)}")
            return False
    
    def getSign(self):
        """Get sign and timestamp from helper API"""
        api = 'https://terabox.hnn.workers.dev/api/get-info'
        post_url = f'{api}?shorturl={self.short_url}&pwd='
        
        headers_post = {
            'accept-language': 'en-US,en;q=0.9,id;q=0.8',
            'referer': 'https://terabox.hnn.workers.dev/',
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
        }
        
        try:
            r = requests.Session()
            pos = r.get(post_url, headers=headers_post, allow_redirects=True).json()
            if pos['ok']:
                self.result['sign'] = pos['sign']
                self.result['timestamp'] = pos['timestamp']
                self.result['status'] = 'success'
            else: 
                self.result['status'] = 'failed'
            r.close()
        except Exception as e:
            logger.error(f"Error getting sign: {str(e)}")
            self.result['status'] = 'failed'
    
    def getMainFile(self):
        """Get main file info from Terabox API"""
        url = f'https://www.terabox.com/api/shorturlinfo?app_id=250528&shorturl=1{self.short_url}&root=1'
        try:
            req = self.r.get(url, headers=self.headers, cookies={'cookie': ''}).json()
            all_file = self.packData(req, self.short_url)
            if len(all_file):
                self.result['shareid'] = req['shareid']
                self.result['uk'] = req['uk']
                self.result['list'] = all_file
        except Exception as e:
            logger.error(f"Error getting main file: {str(e)}")
    
    def getChildFile(self, short_url, path='', root='0'):
        """Get child files if directory"""
        params = {'app_id': '250528', 'shorturl': short_url, 'root': root, 'dir': path}
        url = 'https://www.terabox.com/share/list?' + '&'.join([f'{a}={b}' for a,b in params.items()])
        req = self.r.get(url, headers=self.headers, cookies={'cookie': ''}).json()
        return self.packData(req, short_url)
    
    def packData(self, req, short_url):
        """Process and format file information"""
        try:
            all_file = []
            if 'list' in req:
                for item in req['list']:
                    file_info = {
                        'is_dir': item['isdir'],
                        'path': item['path'],
                        'fs_id': item['fs_id'],
                        'name': item['server_filename'],
                        'type': self.checkFileType(item['server_filename']) if not bool(int(item.get('isdir'))) else 'other',
                        'size': item.get('size') if not bool(int(item.get('isdir'))) else '',
                        'image': item.get('thumbs', {}).get('url3', '') if not bool(int(item.get('isdir'))) else '',
                    }
                    
                    # If it's a directory, get child files
                    if bool(int(item.get('isdir'))):
                        file_info['child'] = self.getChildFile(short_url, item['path'])
                    
                    all_file.append(file_info)
            return all_file
        except Exception as e:
            logger.error(f"Error packing data: {str(e)}")
            return []
    
    def checkFileType(self, name):
        """Determine file type from extension"""
        name = name.lower()
        if any(name.endswith(ext) for ext in ['.jpg', '.jpeg', '.png', '.gif', '.webp']):
            return 'image'
        elif any(name.endswith(ext) for ext in ['.mp4', '.mkv', '.avi', '.mov', '.flv', '.webm']):
            return 'video'
        elif any(name.endswith(ext) for ext in ['.mp3', '.wav', '.flac', '.ogg', '.m4a']):
            return 'audio'
        else:
            return 'other'


class TeraboxLink:
    """
    Class to generate download links for Terabox files.
    Based on the implementation from TeraDL by Dapunta.
    """
    
    def __init__(self, shareid, uk, sign, timestamp, fs_id):
        """Initialize with necessary parameters for download link generation"""
        self.domain = 'https://terabox.hnn.workers.dev/'
        self.api = f'{self.domain}api'
        
        self.r = requests.Session()
        self.headers = {
            'accept-language': 'en-US,en;q=0.9,id;q=0.8',
            'referer': self.domain,
            'sec-fetch-mode': 'cors',
            'sec-fetch-site': 'same-origin',
            'user-agent': 'Mozilla/5.0 (Linux; Android 6.0; Nexus 5 Build/MRA58N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/134.0.0.0 Mobile Safari/537.36',
        }
        self.result = {'status': 'failed', 'download_link': {}}
        
        # Parameters for download link generation
        self.params = {
            'shareid': str(shareid),
            'uk': str(uk),
            'sign': str(sign),
            'timestamp': str(timestamp),
            'fs_id': str(fs_id),
        }
        
        # List of domains for URL wrapping
        self.base_urls = [
            'plain-grass-58b2.comprehensiveaquamarine',
            'royal-block-6609.ninnetta7875',
            'bold-hall-f23e.7rochelle',
            'winter-thunder-0360.belitawhite',
            'fragrant-term-0df9.elviraeducational',
            'purple-glitter-924b.miguelalocal'
        ]
    
    def generate(self):
        """Generate download links"""
        params = self.params
        
        # Download link 1
        try:
            url_1 = f'{self.api}/get-download'
            pos_1 = self.r.post(url_1, json=params, headers=self.headers, allow_redirects=True).json()
            self.result['download_link'].update({'url_1': pos_1['downloadLink']})
        except Exception as e:
            logger.error(f"Error generating download link 1: {str(e)}")
        
        # Download link 2
        try:
            url_2 = f'{self.api}/get-downloadp'
            pos_2 = self.r.post(url_2, json=params, headers=self.headers, allow_redirects=True).json()
            self.result['download_link'].update({'url_2': self.wrap_url(pos_2['downloadLink'])})
        except Exception as e:
            logger.error(f"Error generating download link 2: {str(e)}")
        
        if len(list(self.result['download_link'].keys())) != 0:
            self.result['status'] = 'success'
        
        self.r.close()
    
    def wrap_url(self, original_url):
        """Wrap URL with base64 encoding for compatibility"""
        selected_base = random.choice(self.base_urls)
        quoted_url = quote(original_url, safe='')
        b64_encoded = base64.urlsafe_b64encode(quoted_url.encode()).decode()
        return f'https://{selected_base}.workers.dev/?url={b64_encoded}'


def extract_terabox_download_link(url, progress_callback=None):
    """
    Extract the direct download link from a Terabox URL.
    
    Args:
        url (str): The Terabox URL to extract the download link from
        progress_callback (callable, optional): A callback function to report progress
                                               The function should accept (progress, step_name)
    
    Returns:
        dict: A dictionary with the extraction result:
              - success (bool): Whether the extraction was successful
              - url (str): The direct download URL (if successful)
              - filename (str): The filename (if successful)
              - size (str): The file size (if successful)
              - error (str): The error message (if unsuccessful)
    """
    try:
        # Call progress callback if provided (start at 5%)
        if progress_callback:
            progress_callback(5, "Starting extraction")
            
        # Check if the URL is already a direct download URL
        if is_direct_download_url(url):
            logger.info("Direct download URL detected, extracting file info...")
            
            # Call progress callback if provided (direct URL - quick process)
            if progress_callback:
                progress_callback(40, "Direct URL detected")
                
            # Extract filename from URL
            filename = extract_filename_from_url(url)
            if not filename:
                filename = "TeraboxFile"
                
            # Try to extract size from URL
            size_match = re.search(r'size=(\d+)', url)
            file_size = "Unknown size"
            if size_match:
                size_bytes = int(size_match.group(1))
                file_size = format_file_size(size_bytes)
            
            # Call progress callback if provided (extraction complete)
            if progress_callback:
                progress_callback(60, "URL processed")
                
            return {
                "success": True,
                "url": url,
                "filename": filename,
                "size": file_size
            }
            
        # Normalize the URL
        url = normalize_url(url)
        logger.info(f"Processing normalized URL: {url}")
        
        # Call progress callback if provided (10%)
        if progress_callback:
            progress_callback(10, "URL normalized")
            
        # Step 1: Use TeraboxFile to get file info and sign
        tf = TeraboxFile()
        if not tf.search(url):
            return {"success": False, "error": "Failed to process the Terabox URL"}
        
        # Call progress callback if provided (30%)
        if progress_callback:
            progress_callback(30, "File information extracted")
            
        # Check if we have a successful result with sign parameter
        if tf.result['status'] != 'success':
            return {"success": False, "error": "Could not extract sign parameter"}
        
        # Check if we have any files in the list
        if not tf.result['list']:
            return {"success": False, "error": "No files found in the Terabox link"}
        
        # Get the first file from the list
        file_info = tf.result['list'][0]
        
        # Call progress callback if provided (50%)
        if progress_callback:
            progress_callback(50, "Generating download link")
            
        # Step 2: Use TeraboxLink to generate download links
        tl = TeraboxLink(
            shareid=tf.result['shareid'],
            uk=tf.result['uk'],
            sign=tf.result['sign'],
            timestamp=tf.result['timestamp'],
            fs_id=file_info['fs_id']
        )
        
        tl.generate()
        
        # Call progress callback if provided (70%)
        if progress_callback:
            progress_callback(70, "Download link generated")
            
        # Check if download link generation was successful
        if tl.result['status'] != 'success':
            return {"success": False, "error": "Failed to generate download links"}
        
        # Get the download link - prefer url_1 if available
        download_url = tl.result['download_link'].get('url_1') or tl.result['download_link'].get('url_2')
        if not download_url:
            return {"success": False, "error": "No download link generated"}
        
        # Format file size
        file_size = "Unknown size"
        if file_info.get('size'):
            file_size = format_file_size(int(file_info['size']))
        
        # Return the download information
        # Call progress callback if provided (80%)
        if progress_callback:
            progress_callback(80, "Ready for download")
            
        return {
            "success": True,
            "url": download_url,
            "filename": file_info['name'],
            "size": file_size
        }
    
    except Exception as e:
        logger.error(f"Error extracting download link: {str(e)}")
        return {"success": False, "error": f"Error processing Terabox link: {str(e)}"}


def is_direct_download_url(url):
    """
    Check if the URL is already a direct download URL from Terabox.
    
    Args:
        url (str): The URL to check
        
    Returns:
        bool: True if it's a direct download URL, False otherwise
    """
    # Direct download URLs typically contain these patterns
    patterns = [
        r'd\-[a-z0-9\-]+\.terabox\.com/file/',
        r'size=\d+',
        r'fin=.+?\.mp4',
        r'fid=\d+\-\d+\-\d+'
    ]
    
    # Check if the URL matches the patterns for a direct download URL
    return all(re.search(pattern, url) for pattern in patterns[:1]) and any(re.search(pattern, url) for pattern in patterns[1:])


def extract_filename_from_url(url):
    """
    Extract the filename from a direct download URL.
    
    Args:
        url (str): The direct download URL
        
    Returns:
        str: The extracted filename or None if not found
    """
    # Try to extract filename from fn parameter
    fn_match = re.search(r'fn=([^&]+)', url)
    if fn_match:
        filename = unquote(fn_match.group(1))
        return filename
    
    # Try to extract filename from fin parameter
    fin_match = re.search(r'fin=([^&]+)', url)
    if fin_match:
        filename = unquote(fin_match.group(1))
        return filename
    
    return None

def format_file_size(size_bytes):
    """
    Format file size from bytes to human-readable format.
    
    Args:
        size_bytes (int): File size in bytes
    
    Returns:
        str: Human-readable file size
    """
    if size_bytes < 1024:
        return f"{size_bytes} B"
    elif size_bytes < 1024 * 1024:
        return f"{size_bytes/1024:.2f} KB"
    elif size_bytes < 1024 * 1024 * 1024:
        return f"{size_bytes/(1024*1024):.2f} MB"
    else:
        return f"{size_bytes/(1024*1024*1024):.2f} GB"

def set_telegram_webhook(token, webhook_url):
    """
    Set the webhook URL for the Telegram bot.
    
    Args:
        token (str): The Telegram bot token
        webhook_url (str): The webhook URL to set
    
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        api_url = f"https://api.telegram.org/bot{token}/setWebhook"
        payload = {"url": webhook_url}
        
        response = requests.post(api_url, json=payload)
        data = response.json()
        
        if data.get("ok", False):
            logger.info(f"Webhook set successfully: {webhook_url}")
            return True
        else:
            logger.error(f"Failed to set webhook: {data.get('description', 'Unknown error')}")
            return False
            
    except Exception as e:
        logger.error(f"Error setting webhook: {str(e)}")
        return False
