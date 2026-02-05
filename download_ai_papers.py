import os
import re
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin

# Configuration
BASE_URL = "https://papers.baulab.info/papers/"
OUTPUT_FOLDER = "Famous_Deep_Learning_Papers"

def sanitize_filename(name):
    """
    Removes characters that are illegal in filenames (/:*?"<>|).
    Truncates to 200 chars to avoid filesystem limits.
    """
    # Replace illegal characters with a dash or space
    name = re.sub(r'[\\/*?:"<>|]', "-", name)
    # Remove newlines and tabs
    name = name.replace('\n', ' ').replace('\r', '').replace('\t', ' ')
    # Remove multiple spaces
    name = re.sub(r'\s+', ' ', name).strip()
    return name[:200]

def download_file(url, folder, filename):
    """Downloads a file from a URL to the specific folder."""
    try:
        response = requests.get(url, stream=True)
        response.raise_for_status()
        
        file_path = os.path.join(folder, filename)
        
        with open(file_path, 'wb') as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)
        print(f"SUCCESS: {filename}")
    except Exception as e:
        print(f"FAILED: {filename} - {e}")

def main():
    # 1. Create Output Directory
    if not os.path.exists(OUTPUT_FOLDER):
        os.makedirs(OUTPUT_FOLDER)
        print(f"Created folder: {OUTPUT_FOLDER}")

    # 2. Fetch the Website
    print(f"Fetching {BASE_URL}...")
    try:
        response = requests.get(BASE_URL)
        response.raise_for_status()
    except Exception as e:
        print(f"Could not access website: {e}")
        return

    # 3. Parse HTML
    soup = BeautifulSoup(response.text, 'html.parser')
    
    # Find all links that end with .pdf
    pdf_links = soup.find_all('a', href=lambda x: x and x.endswith('.pdf'))
    
    if not pdf_links:
        print("Could not find any PDF links.")
        return

    print(f"Found {len(pdf_links)} PDF files. Preparing to download...")

    # 4. Collect all PDF information and extract years for sorting
    papers = []
    for link_tag in pdf_links:
        file_url = link_tag.get('href')
        
        if not file_url:
            continue
            
        # Handle relative URLs if necessary
        full_url = urljoin(BASE_URL, file_url)
        
        # Extract the filename from the URL (e.g., "Hinton-2006.pdf")
        base_filename = os.path.basename(file_url)
        
        # Try to extract year from filename using regex
        year_match = re.search(r'-(\d{4})\.pdf$', base_filename)
        year = int(year_match.group(1)) if year_match else 9999  # Use 9999 for files without year
        
        # Try to get the description text from the table row
        row = link_tag.find_parent('tr')
        description = ""
        
        if row:
            # Get all table cells
            cells = row.find_all('td')
            # The description is typically in the last cell
            if len(cells) >= 4:
                description = cells[3].get_text(strip=True)
        
        papers.append({
            'url': full_url,
            'base_filename': base_filename,
            'year': year,
            'description': description
        })
    
    # Sort papers by year
    papers.sort(key=lambda x: x['year'])
    
    print(f"Starting download of {len(papers)} papers in chronological order...")
    
    # 5. Download papers with sequential numbering
    for idx, paper in enumerate(papers, start=1):
        # Construct a descriptive filename with sequential number
        if paper['description']:
            name_without_ext = os.path.splitext(paper['base_filename'])[0]
            clean_name = sanitize_filename(f"{idx:03d} - {name_without_ext} - {paper['description']}") + ".pdf"
        else:
            clean_name = sanitize_filename(f"{idx:03d} - {paper['base_filename']}")
        
        print(f"Downloading [{idx}/{len(papers)}]: {clean_name}...")
        download_file(paper['url'], OUTPUT_FOLDER, clean_name)

    print("\nAll operations complete.")

if __name__ == "__main__":
    main()