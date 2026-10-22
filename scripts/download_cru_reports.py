import urllib.request
import re
import os

os.makedirs('data/raw', exist_ok=True)

# Check publications page for 2022
urls_to_check = [
    'https://www.cru.ie/publications/27567/',
    'https://www.cru.ie/publications/27443/',
    'https://www.cru.ie/publications/26870/'
]

pdf_links = []
for u in urls_to_check:
    try:
        req = urllib.request.Request(u, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            html = resp.read().decode('utf-8', errors='ignore')
            found = re.findall(r'https?://[^\s"\'<>]+\.pdf', html, re.I)
            print(f"URL: {u} -> found {len(found)} PDFs")
            for f in found:
                print("  ", f)
                pdf_links.append(f)
    except Exception as e:
        print(f"Error checking {u}: {e}")

# If we found 2022 report PDF, download it
for link in set(pdf_links):
    fname = link.split('/')[-1]
    if 'energy' in fname.lower() or 'monitoring' in fname.lower() or 'cru' in fname.lower():
        dest = os.path.join('data/raw', fname)
        if not os.path.exists(dest):
            try:
                print(f"Downloading {fname} from {link}...")
                req = urllib.request.Request(link, headers={'User-Agent': 'Mozilla/5.0'})
                with urllib.request.urlopen(req) as resp:
                    with open(dest, 'wb') as out:
                        out.write(resp.read())
                print(f"Saved {dest} ({os.path.getsize(dest)} bytes)")
            except Exception as e:
                print(f"Failed to download {link}: {e}")
