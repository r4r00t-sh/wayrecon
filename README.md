# Wayback Machine CDX Query Tool

A simple Python terminal application for querying the Wayback Machine CDX API to retrieve historical URLs of a given domain.

## Features

- Query historical URLs for any domain (including subdomains)
- Filter by file extensions (`--ext`)
- Filter by HTTP status codes (`-s`, `--status`)
- Output in JSON table format (default) or plain text (`--text`)
- Save results to file (`-o`, `--output`)
- Verbose mode for debugging (`-v`, `--verbose`)
- Beautiful terminal animations

## Installation

```bash
pip install -r requirements.txt
```

## Usage

```bash
# Basic query
python wayrecon.py -u example.com

# Filter by extensions
python wayrecon.py -u example.com --ext js php

# Filter by status codes
python wayrecon.py -u example.com -s 404 403

# Save to file
python wayrecon.py -u example.com -o results.txt

# Verbose mode
python wayrecon.py -u example.com -v
```

## Command Line Arguments

- `-u, --url`: Domain name to query
- `-o, --output`: Save results to file
- `-v, --verbose`: Verbose mode
- `--text`: Plain text output (default: JSON table)
- `--ext`: Filter by file extensions
- `-s, --status`: Filter by HTTP status codes

## Examples

```bash
# Find JavaScript files
python wayrecon.py -u example.com --ext js

# Find 404 errors
python wayrecon.py -u example.com -s 404

# Save filtered results
python wayrecon.py -u example.com --ext zip -o zip_files.txt
```

## License

MIT License - see [LICENSE](LICENSE) file for details.