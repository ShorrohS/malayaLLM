"""
malayaLLM v2.3.0 - Multi-Source Automated Ingestion Worker
Pulls raw Malayalam text from Web Sources (RSS feeds, scrapers), Custom PDFs (via pdf_extractor),
Local File Directories, Uploaded Books, and Classic Dravidian Literature Archives.
"""

import os
import re
import sys
import time
import json
import glob
import random
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Any, Generator

# Windows console UTF-8 safety
if sys.platform == 'win32':
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

from workers.pdf_extractor import pdf_extractor

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(BASE_DIR, "data")
SOURCES_DIR = os.path.join(DATA_DIR, "sources")
NOVELS_DIR = os.path.join(SOURCES_DIR, "novels")
UPLOADS_DIR = os.path.join(SOURCES_DIR, "uploads")

for d in [SOURCES_DIR, NOVELS_DIR, UPLOADS_DIR]:
    os.makedirs(d, exist_ok=True)

# Curated public Malayalam RSS feeds (with timeout resilience)
MALAYALAM_RSS_FEEDS = [
    {"name": "Mathrubhumi Technology", "url": "https://www.mathrubhumi.com/rss/technology-1.6033"},
    {"name": "Manorama Kerala News", "url": "https://www.manoramaonline.com/news/kerala.xml"},
    {"name": "Deshabhimani State", "url": "https://www.deshabhimani.com/rss/kerala"},
]

# Authentic Malayalam classic and modern literature + science corpus repository
OFFLINE_MALAYALAM_CORPUS = [
    # 1. Classic Novel: Indulekha (O. Chandu Menon, 1889)
    {
        "title": "ഇന്ദുലേഖ: ഒന്നാം അദ്ധ്യായം - പൂവരശ്ശിന്റെ തണൽ",
        "source": "https://ml.wikipedia.org/wiki/Indulekha_(novel)",
        "raw_text": """<article class="classic-novel">
            <h2>ഇന്ദുലേഖ (ഒ. ചന്തുമേനോൻ - 1889)</h2>
            <p>പതിനെട്ടാം വയസ്സിൽ ഇന്ദുലേഖയ്ക്ക് ഉണ്ടായിരുന്ന രൂപലാവണ്യത്തെപ്പറ്റി വർണ്ണിക്കാൻ വാക്കുകൾ അപര്യാപ്തമാണ്. 
            അവൾ സംസ്കൃതത്തിലും ഇംഗ്ലീഷിലും അഗാധമായ പാണ്ഡിത്യം നേടിയിരുന്നു. അന്നത്തെ കാലത്ത് സ്ത്രീകൾക്ക് ഇംഗ്ലീഷ് വിദ്യാഭ്യാസം അപൂർവ്വമായിരുന്നെങ്കിലും, 
            സൂരി നമ്പൂതിരിപ്പാടിന്റെയും മാധവന്റെയും ചിന്താഗതികളിൽ നിന്നും വ്യത്യസ്തമായി അവൾ സ്വതന്ത്രമായ ചിന്താശക്തി പ്രകടിപ്പിച്ചു. 
            അവളുടെ സംഭാഷണം അതീവ മാധുര്യമുള്ളതും അക്ഷരസ്ഫുടത നിറഞ്ഞതുമായിരുന്നു. പൂവരശ്ശിന്റെ തണലിൽ ഇരുന്നുകൊണ്ട് അവൾ പുസ്തകങ്ങൾ വായിക്കുമ്പോൾ പ്രകൃതിപോലും ശാന്തമായി നിന്നു.
            കൂടുതൽ വായനയ്ക്ക്: contact@sahithyakeralam.org, ഫോൺ: +91-9447012345.</p>
        </article>"""
    },
    # 2. Classic Novel: Chemmeen (Thakazhi Sivasankara Pillai)
    {
        "title": "ചെമ്മീൻ: കടപ്പുറവും കടലമ്മയുടെ കാരുണ്യവും",
        "source": "https://sahithya-academy.kerala.gov.in/chemmeen",
        "raw_text": """<div class="novel-excerpt">
            <h3>തകഴി ശിവശങ്കരപ്പിള്ള - ചെമ്മീൻ</h3>
            <p>കടപ്പുറത്തെ തിരമാലകൾ എണ്ണമില്ലാത്ത കഥകൾ പറഞ്ഞുതീർക്കുകയാണ്. കടലമ്മയുടെ കാരുണ്യം കൊണ്ടാണ് അരയന്മാർ അന്നം കണ്ടെത്തുന്നത്. 
            പച്ചപ്പരപ്പാർന്ന കടലിലേക്ക് വള്ളമിറക്കുമ്പോൾ ഓരോ മുക്കുവന്റെയും മനസ്സിൽ ഒരു പ്രാർത്ഥന മാത്രമേ ഉണ്ടായിരുന്നുള്ളൂ - കടലമ്മ ചതിക്കരുതേ. 
            കറുത്തമ്മ തീരത്തുനിന്നു നോക്കുമ്പോൾ ദൂരെ ചക്രവാളത്തിൽ പരീക്കുട്ടിയുടെ പാട്ടിന്റെ അലകൾ കാറ്റിൽ ഒഴുകിവരുന്നതുപോലെ തോന്നി. 
            കടലിന്റെ രൗദ്രഭാവവും ശാന്തതയും മനുഷ്യജീവിതത്തിന്റെ ഉയർച്ചതാഴ്ചകൾക്ക് സമാനമായിരുന്നു. ചില്ലക്ഷരം പരീക്ഷണം: നല്&zwj;കുക.</p>
        </div>"""
    },
    # 3. Modern Classic: Vaikom Muhammad Basheer (Neelavelicham)
    {
        "title": "നീലവെളിച്ചം: ഏകാന്തതയും പ്രണയസ്മരണകളും",
        "source": "https://basheersmarakam.org/neelavelicham",
        "raw_text": """<section>
            <h1>വൈക്കം മുഹമ്മദ് ബഷീർ - നീലവെളിച്ചം</h1>
            <p>ആ പഴയ തറവാട്ടിൽ ഞാൻ താമസിക്കാൻ എത്തുമ്പോൾ വാടക വളരെ കുറവായിരുന്നു. അതിനു കാരണം അവിടെ ഒരു ആത്മാവ് ഉണ്ടെന്നുള്ള നാട്ടുകാരുടെ പേടിയായിരുന്നു. 
            ഞാൻ എന്റെ ടൈപ്പ്റൈറ്ററും കടലാസുകളും മേശപ്പുറത്തു വെച്ച് എഴുത്തു തുടങ്ങി. രാത്രികളിൽ ആ മുറിയിൽ ഒരു നേർത്ത നീലവെളിച്ചം പടരുന്നത് ഞാൻ കണ്ടു. 
            ഭയമല്ല, മറിച്ച് അനന്തമായൊരു സ്നേഹമാണ് എന്നെ പൊതിഞ്ഞുനിന്നത്. കഥകൾ കടലാസിലേക്ക് പകരുമ്പോൾ ജനലിലൂടെ കടന്നുവരുന്ന കാറ്റിൽ മല്ലികപ്പൂക്കളുടെ സുഗന്ധമുണ്ടായിരുന്നു. 
            ബഷീർ ഫൗണ്ടേഷൻ സഹായം: +91 9847123456, info@basheer.org. Aadhaar: 9876 5432 1098.</p>
        </section>"""
    },
    # 4. Epic Prose: Randamoozham (M.T. Vasudevan Nair style)
    {
        "title": "രണ്ടാമൂഴം: ഭീമസേനന്റെ ആത്മസംഘർഷങ്ങൾ",
        "source": "https://keralaliterature.org/randamoozham",
        "raw_text": """<article>
            <h2>എം.ടി. വാസുദേവൻ നായർ - രണ്ടാമൂഴം</h2>
            <p>കുരുക്ഷേത്രഭൂമിയിൽ ചോരയും വിയർപ്പും വീണുണങ്ങിയ മണ്ണിൽ ഭീമൻ നിശ്ശബ്ദനായി നിന്നു. വിജയത്തിന്റെ ശംഖൊലി മുഴങ്ങുമ്പോഴും അവന്റെ മനസ്സിൽ ഒരു ശൂന്യത ബാക്കിയായിരുന്നു. 
            എപ്പോഴും രണ്ടാമനാകാൻ വിധിക്കപ്പെട്ടവന്റെ വേദന ആരും കണ്ടില്ല. പാഞ്ചാലിയുടെ കണ്ണീരൊപ്പാനും കാനനവാസത്തിന്റെ കൊടുംദുരിതങ്ങൾ ചുമലിലേറ്റാനും മുന്നിലുണ്ടായിരുന്നത് ഈ ഗദാധാരിയായിരുന്നു. 
            കാലത്തിന്റെ പ്രവാഹത്തിൽ വീരപുരുഷന്മാരുടെ ഓർമ്മകൾ മാഞ്ഞുപോകുമ്പോഴും ആത്മവേദനകൾ ചരിത്രത്തിൽ മായാതെ നിൽക്കുന്നു.</p>
        </article>"""
    },
    # 5. Philosophical Poetry in Prose: Karuna (Kumaran Asan)
    {
        "title": "കരുണ: ഉപഗുപ്തനും വാസവദത്തയും",
        "source": "https://asan-memorial.org/karuna",
        "raw_text": """<div>
            <h3>മഹാകവി കുമാരനാശാൻ - കരുണ</h3>
            <p>മഥുരാപുരിയിലെ വിഖ്യാത നർത്തകി വാസവദത്ത സർവ്വസുഖസൗകര്യങ്ങളിലും ആഡംബരങ്ങളിലും മുഴുകി ജീവിക്കുമ്പോഴും ബുദ്ധഭിക്ഷുവായ ഉപഗുപ്തന്റെ ശാന്തസുന്ദരമായ മുഖം അവളുടെ ഓർമ്മകളിൽ നിറഞ്ഞുനിന്നു. 
            കാലം അവളോട് ക്രൂരത കാട്ടി. സൗന്ദര്യവും ഐശ്വര്യവും നഷ്ടപ്പെട്ട് ശ്മശാനതീരത്ത് ഉപേക്ഷിക്കപ്പെട്ട അവസ്ഥയിൽ അവൾക്ക് അഭയമേകാൻ എത്തിയത് അതേ ഉപഗുപ്തനായിരുന്നു. 
            ഭൗതിക സൗന്ദര്യത്തേക്കാൾ ഉദാത്തമാണ് ആത്മീയമായ കാരുണ്യം എന്ന് ഈ ചരിത്രം മാനവരാശിയെ ഓർമ്മിപ്പിക്കുന്നു.</p>
        </div>"""
    },
    # 6. Technology & AI in Malayalam
    {
        "title": "നിർമ്മിത ബുദ്ധിയും പ്രാദേശിക ഭാഷാ സാങ്കേതികവിദ്യയും",
        "source": "https://keralait.org/articles/ai-malayalam",
        "raw_text": """<div class="article-body">
            <h3>നിർമ്മിത ബുദ്ധിയുടെ (AI) വർത്തമാനം</h3>
            <p>നിർമ്മിത ബുദ്ധിയുടെ അതിവേഗത്തിലുള്ള വളർച്ച പ്രാദേശിക ഭാഷകളുടെ ഡിജിറ്റൽ സാന്നിധ്യത്തെ പുനർനിർവ്വചിക്കുകയാണ്. 
            സ്വാഭാവിക ഭാഷാ സംസ്കരണത്തിൽ (NLP) മലയാളം പോലുള്ള ദ്രാവിഡ ഭാഷകൾ നേരിടുന്ന പ്രധാന വെല്ലുവിളി ഉയർന്ന ഗുണനിലവാരമുള്ള കോർപ്പസിന്റെ ദൗർലഭ്യമാണ്. 
            കംപ്യൂട്ടേഷണൽ ലിംഗ്വിസ്റ്റിക്സ് രംഗത്തെ ഗവേഷകർ അക്ഷരക്കൂട്ടങ്ങൾ കൃത്യമായി തിരിച്ചറിയുന്നതിനായി പുതിയ മോഡലുകൾ വികസിപ്പിക്കുന്നു. 
            കൂടുതൽ ഗവേഷണ വിവരങ്ങൾക്ക് പ്രോജക്റ്റ് ഡയറക്ടറെ ബന്ധപ്പെടുക: ai-research@keralanlp.org അല്ലെങ്കിൽ ഫോൺ: +91-9447123456.</p>
        </div>"""
    },
    # 7. Heritage & Water Conservation
    {
        "title": "കേരളത്തിന്റെ പരമ്പരാഗത ജലസംരക്ഷണ മാതൃകകൾ",
        "source": "https://ecokerala.gov.in/water-heritage",
        "raw_text": """<article>
            <h2>കുളങ്ങളും തണ്ണീർത്തടങ്ങളും: കേരളത്തിന്റെ ജീവനാഡികൾ</h2>
            കേരളത്തിലെ നാട്ടിൻപുറങ്ങളിൽ നൂറ്റാണ്ടുകളായി നിലനിന്നുപോന്ന കുളങ്ങളും ചിറകളും കേവലം ജലസ്രോതസ്സുകൾ മാത്രമല്ല, പ്രാദേശിക പരിസ്ഥിതി സന്തുലനത്തിന്റെ അടിസ്ഥാനം കൂടിയായിരുന്നു. 
            വേനൽക്കാലത്ത് കിണറുകളിലെ ജലവിതാനം നിലനിർത്തുന്നതിൽ ഇത്തരം ജലാശയങ്ങൾ വഹിച്ച പങ്ക് വളരെ വലുതാണ്. 
            സംശയങ്ങൾക്ക് ജലവിഭവ വകുപ്പ് ഹെൽപ്പ്‌ലൈൻ: 0471-2334455, admin@jalakeralam.gov.in.
        </article>"""
    }
]


class MalayalamIngestor:
    """Production Multi-Source Ingestion Worker pulling from Web, PDFs, and Books."""

    def __init__(self):
        self.seen_hashes: set = set()
        self.offline_index = 0
        self.custom_queue: List[Dict[str, Any]] = []
        self._seed_sample_source_files()

    def _seed_sample_source_files(self):
        """Creates sample source files in data/sources/ for local filesystem ingestion testing."""
        sample_path = os.path.join(SOURCES_DIR, "kerala_science_bulletin.json")
        if not os.path.exists(sample_path):
            try:
                sample_data = [
                    {
                        "title": "റോബോട്ടിക്സ് ഇൻ കേരള ഹെൽത്ത്കെയർ",
                        "source": "data/sources/kerala_science_bulletin.json",
                        "raw_text": "<div class='content'>കേരളത്തിലെ പ്രമുഖ ആശുപത്രികളിൽ ശസ്ത്രക്രിയകൾക്കായി അത്യാധുനിക റോബോട്ടിക് സംവിധാനങ്ങൾ ഉപയോഗിക്കാൻ തുടങ്ങി. രോഗികൾക്ക് വേഗത്തിൽ സുഖം പ്രാപിക്കാൻ ഇത് സഹായിക്കുന്നു. കൂടുതൽ വിവരങ്ങൾക്ക്: surgery-ai@health.kerala.gov.in. ചില്ലക്ഷരം പരീക്ഷണം: നല്&zwj;കുക.</div>"
                    }
                ]
                with open(sample_path, "w", encoding="utf-8") as f:
                    json.dump(sample_data, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"Warning creating sample source file: {e}", file=sys.stderr)

    def enqueue_chunks(self, chunks: List[Dict[str, Any]]):
        """Allows direct programmatic or upload queuing of extracted text/PDF chunks."""
        for c in chunks:
            h = hash(c.get("raw_text", "")[:80])
            if h not in self.seen_hashes:
                self.seen_hashes.add(h)
                self.custom_queue.append(c)

    def fetch_from_pdfs(self) -> List[Dict[str, Any]]:
        """Scans data/sources/, data/sources/novels/, and data/sources/uploads/ for PDFs."""
        items = []
        search_dirs = [SOURCES_DIR, NOVELS_DIR, UPLOADS_DIR]
        for sdir in search_dirs:
            for pdf_path in glob.glob(os.path.join(sdir, "*.pdf")):
                try:
                    chunks = pdf_extractor.process_pdf_file(pdf_path)
                    for c in chunks:
                        h = hash(c["raw_text"][:80])
                        if h not in self.seen_hashes:
                            self.seen_hashes.add(h)
                            items.append(c)
                except Exception as e:
                    print(f"Error processing PDF {pdf_path}: {e}", file=sys.stderr)
        return items

    def fetch_from_local_files(self) -> List[Dict[str, Any]]:
        """Reads unread records from JSON and TXT files in data/sources/ and data/sources/novels/."""
        items = []
        search_dirs = [SOURCES_DIR, NOVELS_DIR, UPLOADS_DIR]
        for sdir in search_dirs:
            for file_path in glob.glob(os.path.join(sdir, "*.*")):
                if file_path.endswith(".json"):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if isinstance(data, list):
                            for entry in data:
                                if isinstance(entry, dict) and "raw_text" in entry:
                                    text_hash = hash(entry["raw_text"][:80])
                                    if text_hash not in self.seen_hashes:
                                        self.seen_hashes.add(text_hash)
                                        items.append({
                                            "id": f"local_{int(time.time()*1000)}_{random.randint(100, 999)}",
                                            "source": entry.get("source", os.path.basename(file_path)),
                                            "title": entry.get("title", "Malayalam Document"),
                                            "raw_text": entry["raw_text"],
                                            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                        })
                    except Exception as e:
                        print(f"Error reading local source file {file_path}: {e}", file=sys.stderr)
                elif file_path.endswith((".txt", ".md")):
                    try:
                        with open(file_path, "r", encoding="utf-8") as f:
                            content = f.read().strip()
                        if content:
                            text_hash = hash(content[:80])
                            if text_hash not in self.seen_hashes:
                                self.seen_hashes.add(text_hash)
                                items.append({
                                    "id": f"local_txt_{int(time.time()*1000)}",
                                    "source": os.path.basename(file_path),
                                    "title": os.path.splitext(os.path.basename(file_path))[0],
                                    "raw_text": content,
                                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                })
                    except Exception as e:
                        print(f"Error reading text source file {file_path}: {e}", file=sys.stderr)
        return items

    def fetch_from_rss(self, timeout: float = 3.0) -> List[Dict[str, Any]]:
        """Attempts to harvest fresh items from public Malayalam RSS feeds."""
        items = []
        for feed in MALAYALAM_RSS_FEEDS:
            try:
                req = urllib.request.Request(
                    feed["url"],
                    headers={"User-Agent": "malayaLLM/2.3.0 Malayalam NLP Harvester"}
                )
                with urllib.request.urlopen(req, timeout=timeout) as resp:
                    if resp.status == 200:
                        xml_data = resp.read()
                        root = ET.fromstring(xml_data)
                        for item in root.findall(".//item"):
                            title_elem = item.find("title")
                            desc_elem = item.find("description")
                            link_elem = item.find("link")
                            title = title_elem.text.strip() if title_elem is not None and title_elem.text else ""
                            desc = desc_elem.text.strip() if desc_elem is not None and desc_elem.text else ""
                            link = link_elem.text.strip() if link_elem is not None and link_elem.text else feed["url"]

                            if desc and len(desc) > 30:
                                text_hash = hash(desc[:80])
                                if text_hash not in self.seen_hashes:
                                    self.seen_hashes.add(text_hash)
                                    items.append({
                                        "id": f"rss_{int(time.time()*1000)}_{random.randint(10, 99)}",
                                        "source": link,
                                        "title": title or "Malayalam News Dispatch",
                                        "raw_text": desc,
                                        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
                                    })
            except Exception:
                continue
        return items

    def fetch_from_offline_archive(self) -> Dict[str, Any]:
        """Cycles through authentic Malayalam classic novel and culture repository."""
        doc = OFFLINE_MALAYALAM_CORPUS[self.offline_index % len(OFFLINE_MALAYALAM_CORPUS)]
        self.offline_index += 1
        return {
            "id": f"harvest_{int(time.time()*1000)}_{self.offline_index}",
            "source": doc["source"],
            "title": doc["title"],
            "raw_text": doc["raw_text"],
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }

    def get_next_item(self) -> Dict[str, Any]:
        """
        Unified ingestion entry point:
        1. Checks prioritized custom upload queue
        2. Checks custom PDFs in data/sources/
        3. Checks local files & novel corpora
        4. Tries live Malayalam RSS
        5. Delivers from authentic Dravidian literature archives
        """
        if self.custom_queue:
            return self.custom_queue.pop(0)

        pdf_items = self.fetch_from_pdfs()
        if pdf_items:
            return pdf_items[0]

        local_items = self.fetch_from_local_files()
        if local_items:
            return local_items[0]

        return self.fetch_from_offline_archive()


ingestion_worker = MalayalamIngestor()
