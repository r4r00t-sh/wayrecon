#!/usr/bin/env python3
"""
Wayback Machine CDX API Query Tool

A terminal application for querying the Wayback Machine CDX API
to retrieve historical URLs of a given domain.
"""

import argparse
import json
import sys
import time
import threading
from typing import List, Dict, Any, Optional
from urllib.parse import urlparse
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry


print ("""
 █     █░ ▄▄▄     ▓██   ██▓ ██▀███  ▓█████  ▄████▄   ▒█████   ███▄    █ 
▓█░ █ ░█░▒████▄    ▒██  ██▒▓██ ▒ ██▒▓█   ▀ ▒██▀ ▀█  ▒██▒  ██▒ ██ ▀█   █ 
▒█░ █ ░█ ▒██  ▀█▄   ▒██ ██░▓██ ░▄█ ▒▒███   ▒▓█    ▄ ▒██░  ██▒▓██  ▀█ ██▒
░█░ █ ░█ ░██▄▄▄▄██  ░ ▐██▓░▒██▀▀█▄  ▒▓█  ▄ ▒▓▓▄ ▄██▒▒██   ██░▓██▒  ▐▌██▒
░░██▒██▓  ▓█   ▓██▒ ░ ██▒▓░░██▓ ▒██▒░▒████▒▒ ▓███▀ ░░ ████▓▒░▒██░   ▓██░
░ ▓░▒ ▒   ▒▒   ▓▒█░  ██▒▒▒ ░ ▒▓ ░▒▓░░░ ▒░ ░░ ░▒ ▒  ░░ ▒░▒░▒░ ░ ▒░   ▒ ▒ 
  ▒ ░ ░    ▒   ▒▒ ░▓██ ░▒░   ░▒ ░ ▒░ ░ ░  ░  ░  ▒     ░ ▒ ▒░ ░ ░░   ░ ▒░
  ░   ░    ░   ▒   ▒ ▒ ░░    ░░   ░    ░   ░        ░ ░ ░ ▒     ░   ░ ░ 
    ░          ░  ░░ ░        ░        ░  ░░ ░          ░ ░           ░ 
                   ░ ░                     ░                            
                                                                @r4r00t
""")


class LoadingSpinner:
    """A simple loading spinner for terminal output."""
    
    def __init__(self, message="Loading"):
        self.message = message
        self.spinner_chars = ['⠋', '⠙', '⠹', '⠸', '⠼', '⠴', '⠦', '⠧', '⠇', '⠏']
        self.running = False
        self.thread = None
    
    def start(self):
        """Start the spinner animation."""
        self.running = True
        self.thread = threading.Thread(target=self._spin)
        self.thread.daemon = True
        self.thread.start()
    
    def stop(self):
        """Stop the spinner animation."""
        self.running = False
        if self.thread:
            self.thread.join()
        # Clear the spinner line
        print('\r' + ' ' * (len(self.message) + 10), end='\r')
    
    def _spin(self):
        """Internal method to run the spinner animation."""
        i = 0
        while self.running:
            print(f'\r{self.spinner_chars[i % len(self.spinner_chars)]} {self.message}...', end='', flush=True)
            time.sleep(0.1)
            i += 1


class ProgressBar:
    """A simple progress bar for terminal output."""
    
    def __init__(self, total=100, width=50):
        self.total = total
        self.width = width
        self.current = 0
    
    def update(self, current):
        """Update the progress bar."""
        self.current = current
        percent = (current / self.total) * 100
        filled = int((current / self.total) * self.width)
        bar = '█' * filled + '░' * (self.width - filled)
        print(f'\r[{bar}] {percent:.1f}%', end='', flush=True)
    
    def complete(self):
        """Mark the progress bar as complete."""
        print(f'\r[{"█" * self.width}] 100.0%')


class WaybackCDXQuery:
    """Main class for querying the Wayback Machine CDX API."""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.session = self._create_session()
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with retry strategy."""
        session = requests.Session()
        
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
        )
        
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def normalize_domain(self, domain: str) -> str:
        """
        Normalize domain input by stripping protocols and www.
        
        Args:
            domain: The domain to normalize
            
        Returns:
            Normalized domain string
        """
        # Remove protocols
        if domain.startswith(('http://', 'https://')):
            parsed = urlparse(domain)
            domain = parsed.netloc
        
        # Remove www prefix
        if domain.startswith('www.'):
            domain = domain[4:]
        
        return domain.lower().strip()
    
    def build_cdx_url(self, domain: str, text_mode: bool = False) -> str:
        """
        Build the CDX API URL for the given domain.
        
        Args:
            domain: The normalized domain
            text_mode: Whether to use text output format
            
        Returns:
            Complete CDX API URL
        """
        base_url = "https://web.archive.org/cdx/search/cdx"
        
        if text_mode:
            params = {
                'url': f'*.{domain}/*',
                'collapse': 'urlkey',
                'output': 'text',
                'fl': 'original'
            }
        else:
            params = {
                'url': f'*.{domain}/*',
                'collapse': 'urlkey',
                'output': 'json',
                'fl': 'original,timestamp,statuscode'
            }
        
        # Build URL with parameters
        url = f"{base_url}?"
        url += "&".join([f"{k}={v}" for k, v in params.items()])
        
        if self.verbose:
            print(f"[VERBOSE] Constructed CDX URL: {url}")
        
        return url
    
    def fetch_cdx_data(self, url: str, show_animation: bool = True) -> List[Any]:
        """
        Fetch data from the CDX API with retries.
        
        Args:
            url: The CDX API URL
            show_animation: Whether to show loading animation
            
        Returns:
            List of CDX records
            
        Raises:
            requests.RequestException: If the request fails after retries
        """
        if self.verbose:
            print(f"[VERBOSE] Making request to: {url}")
        
        # Start loading animation
        spinner = None
        if show_animation and not self.verbose:
            spinner = LoadingSpinner("Fetching data from Wayback Machine")
            spinner.start()
        
        try:
            # Simulate some processing steps with progress
            if show_animation and not self.verbose:
                time.sleep(0.5)  # Brief pause to show spinner
            
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            # Stop spinner before processing
            if spinner:
                spinner.stop()
            
            if self.verbose:
                print(f"[VERBOSE] HTTP Status: {response.status_code}")
                print(f"[VERBOSE] Response size: {len(response.content)} bytes")
            
            # Show processing animation
            if show_animation and not self.verbose:
                spinner = LoadingSpinner("Processing results")
                spinner.start()
            
            # Parse response based on content type
            if 'application/json' in response.headers.get('content-type', ''):
                data = response.json()
                if isinstance(data, list) and len(data) > 0:
                    # Remove header row if present
                    if data[0] == ['original', 'timestamp', 'statuscode']:
                        data = data[1:]
            else:
                # Text format - split by lines
                lines = response.text.strip().split('\n')
                data = [line.strip() for line in lines if line.strip()]
            
            # Stop processing spinner
            if spinner:
                spinner.stop()
            
            return data
                
        except requests.exceptions.RequestException as e:
            if spinner:
                spinner.stop()
            if self.verbose:
                print(f"[VERBOSE] Request failed: {e}")
            raise
    
    def filter_by_extensions(self, data: List[Any], extensions: List[str], text_mode: bool = False, show_animation: bool = True) -> List[Any]:
        """
        Filter URLs by file extensions.
        
        Args:
            data: List of CDX records
            extensions: List of file extensions to filter by
            text_mode: Whether data is in text format
            show_animation: Whether to show loading animation
            
        Returns:
            Filtered list of records
        """
        if not extensions:
            return data
        
        # Start filtering animation
        spinner = None
        if show_animation and not self.verbose:
            spinner = LoadingSpinner("Filtering by extensions")
            spinner.start()
        
        try:
            extensions = [ext.lower().lstrip('.') for ext in extensions]
            filtered_data = []
            
            # Simulate processing time for animation
            if show_animation and not self.verbose:
                time.sleep(0.3)
            
            for record in data:
                if text_mode:
                    url = record
                else:
                    url = record[0] if isinstance(record, list) else record
                
                # Check if URL ends with any of the specified extensions
                url_lower = url.lower()
                if any(url_lower.endswith(f'.{ext}') for ext in extensions):
                    filtered_data.append(record)
            
            # Stop spinner
            if spinner:
                spinner.stop()
            
            return filtered_data
            
        except Exception as e:
            if spinner:
                spinner.stop()
            raise
    
    def filter_by_status_codes(self, data: List[Any], status_codes: List[int], show_animation: bool = True) -> List[Any]:
        """
        Filter URLs by HTTP status codes.
        
        Args:
            data: List of CDX records
            status_codes: List of HTTP status codes to filter by
            show_animation: Whether to show loading animation
            
        Returns:
            Filtered list of records
        """
        if not status_codes:
            return data
        
        # Start filtering animation
        spinner = None
        if show_animation and not self.verbose:
            spinner = LoadingSpinner("Filtering by status codes")
            spinner.start()
        
        try:
            filtered_data = []
            
            # Simulate processing time for animation
            if show_animation and not self.verbose:
                time.sleep(0.3)
            
            for record in data:
                if isinstance(record, list) and len(record) >= 3:
                    # JSON format: [original, timestamp, statuscode]
                    status_code = int(record[2])
                    if status_code in status_codes:
                        filtered_data.append(record)
                elif isinstance(record, str):
                    # Text format - we can't filter by status code in text mode
                    # since status code is not included in text output
                    filtered_data.append(record)
            
            # Stop spinner
            if spinner:
                spinner.stop()
            
            return filtered_data
            
        except Exception as e:
            if spinner:
                spinner.stop()
            raise
    
    def format_json_table(self, data: List[List[str]]) -> str:
        """
        Format CDX data as a JSON table.
        
        Args:
            data: List of CDX records
            
        Returns:
            Formatted table string
        """
        if not data:
            return "No results."
        
        # Calculate column widths
        headers = ['original', 'timestamp', 'statuscode']
        widths = [len(h) for h in headers]
        
        for record in data:
            for i, field in enumerate(record):
                if i < len(widths):
                    widths[i] = max(widths[i], len(str(field)))
        
        # Create table
        lines = []
        
        # Header
        header_line = " | ".join(h.ljust(w) for h, w in zip(headers, widths))
        lines.append(header_line)
        lines.append("-" * len(header_line))
        
        # Data rows
        for record in data:
            row_line = " | ".join(str(field).ljust(w) for field, w in zip(record, widths))
            lines.append(row_line)
        
        return "\n".join(lines)
    
    def format_text_list(self, data: List[str]) -> str:
        """
        Format CDX data as a plain text list.
        
        Args:
            data: List of URLs
            
        Returns:
            Formatted text string
        """
        if not data:
            return "No results."
        
        return "\n".join(data)
    
    def save_to_file(self, content: str, filename: str) -> None:
        """
        Save content to a file.
        
        Args:
            content: Content to save
            filename: Output filename
        """
        try:
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(content)
            if self.verbose:
                print(f"[VERBOSE] Saved output to: {filename}")
        except IOError as e:
            print(f"Error saving to file {filename}: {e}")
            sys.exit(1)


def main():
    """Main function to run the Wayback CDX query tool."""
    parser = argparse.ArgumentParser(
        description="Query the Wayback Machine CDX API for historical URLs",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python wayback_cdx_query.py -u example.com
  python wayback_cdx_query.py -u example.com --ext js php -v
  python wayback_cdx_query.py -u example.com --text --ext zip -o zip_urls.txt
  python wayback_cdx_query.py -u example.com -s 404 403
  python wayback_cdx_query.py -u example.com --ext js --status 200 -o results.txt
        """
    )
    
    parser.add_argument(
        '-u', '--url',
        help='Domain name to query (e.g., example.com)'
    )
    
    parser.add_argument(
        '-o', '--output',
        help='Save raw response to specified output file'
    )
    
    parser.add_argument(
        '-v', '--verbose',
        action='store_true',
        help='Verbose mode (show constructed URL, HTTP status, retries, etc.)'
    )
    
    parser.add_argument(
        '--text',
        action='store_true',
        help='Output plain text (only original URLs). Default is JSON format.'
    )
    
    parser.add_argument(
        '--ext',
        nargs='+',
        help='One or more file extensions to filter results (e.g., --ext js php zip)'
    )
    
    parser.add_argument(
        '-s', '--status',
        nargs='+',
        type=int,
        help='One or more HTTP status codes to filter results (e.g., -s 404 403 200)'
    )
    
    args = parser.parse_args()
    
    # Check if no arguments provided
    if len(sys.argv) == 1:
        print("No arguments provided.")
        print("\nWayback Machine CDX Query Tool")
        print("=" * 40)
        print("\nAvailable Commands:")
        print("  -u, --url     Domain name to query (e.g., example.com)")
        print("  -o, --output  Save raw response to specified output file")
        print("  -v, --verbose Verbose mode (show constructed URL, HTTP status, retries, etc.)")
        print("  --text        Output plain text (only original URLs). Default is JSON format.")
        print("  --ext         One or more file extensions to filter results (e.g., --ext js php zip)")
        print("  -s, --status  One or more HTTP status codes to filter results (e.g., -s 404 403 200)")
        print("\nExample Queries:")
        print("  python main.py -u example.com")
        print("  python main.py -u example.com --ext js php -v")
        print("  python main.py -u example.com --text --ext zip -o zip_urls.txt")
        print("  python main.py -u example.com -s 404 403")
        print("  python main.py -u example.com --ext js --status 200 -o results.txt")
        print("\nUse --help for more detailed information.")
        sys.exit(0)
    
    # Get domain from command line
    domain = args.url
    if not domain:
        print("Error: Domain name is required. Use -u or --url to specify a domain.")
        print("Example: python main.py -u example.com")
        sys.exit(1)
    
    # Initialize query tool
    query_tool = WaybackCDXQuery(verbose=args.verbose)
    
    # Show startup animation
    if not args.verbose:
        print("🚀 Wayback Machine CDX Query Tool")
        print("=" * 40)
        spinner = LoadingSpinner("Initializing")
        spinner.start()
        time.sleep(0.5)
        spinner.stop()
        print("✓ Ready to query Wayback Machine")
        print()
    
    try:
        # Normalize domain
        normalized_domain = query_tool.normalize_domain(domain)
        if args.verbose:
            print(f"[VERBOSE] Normalized domain: {normalized_domain}")
        elif not args.verbose:
            print(f"🔍 Querying domain: {normalized_domain}")
            print()
        
        # Build CDX URL
        cdx_url = query_tool.build_cdx_url(normalized_domain, args.text)
        
        # Fetch data
        if args.verbose:
            print("[VERBOSE] Fetching data from Wayback Machine...")
        
        data = query_tool.fetch_cdx_data(cdx_url, show_animation=not args.verbose)
        
        if args.verbose:
            print(f"[VERBOSE] Retrieved {len(data)} records")
        else:
            print(f"✓ Retrieved {len(data)} records")
        
        # Filter by extensions if specified
        if args.ext:
            if args.verbose:
                print(f"[VERBOSE] Filtering by extensions: {args.ext}")
            data = query_tool.filter_by_extensions(data, args.ext, args.text, show_animation=not args.verbose)
            if args.verbose:
                print(f"[VERBOSE] After extension filtering: {len(data)} records")
            else:
                print(f"✓ Filtered to {len(data)} records matching extensions: {', '.join(args.ext)}")
        
        # Filter by status codes if specified
        if args.status:
            if args.text:
                print("⚠️  Warning: Status code filtering is not available in text mode (status codes not included in text output)")
            else:
                if args.verbose:
                    print(f"[VERBOSE] Filtering by status codes: {args.status}")
                data = query_tool.filter_by_status_codes(data, args.status, show_animation=not args.verbose)
                if args.verbose:
                    print(f"[VERBOSE] After status code filtering: {len(data)} records")
                else:
                    print(f"✓ Filtered to {len(data)} records matching status codes: {', '.join(map(str, args.status))}")
        
        # Format output
        if not args.verbose:
            spinner = LoadingSpinner("Formatting results")
            spinner.start()
            time.sleep(0.2)  # Brief pause for animation
            spinner.stop()
        
        if args.text:
            output = query_tool.format_text_list(data)
        else:
            output = query_tool.format_json_table(data)
        
        # Display or save output
        if args.output:
            if not args.verbose:
                spinner = LoadingSpinner("Saving to file")
                spinner.start()
                time.sleep(0.2)
                spinner.stop()
            query_tool.save_to_file(output, args.output)
            print(f"✓ Results saved to {args.output}")
        else:
            if not args.verbose:
                print("\n" + "="*60)
                print("RESULTS")
                print("="*60)
            print(output)
            if not args.verbose:
                print("\n" + "="*60)
                print(f"Query completed successfully! Found {len(data)} results.")
                print("="*60)
            
    except requests.exceptions.RequestException as e:
        print(f"Network error: {e}")
        sys.exit(1)
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {e}")
        sys.exit(1)
    except KeyboardInterrupt:
        print("\nOperation cancelled by user.")
        sys.exit(0)
    except Exception as e:
        print(f"Unexpected error: {e}")
        if args.verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
