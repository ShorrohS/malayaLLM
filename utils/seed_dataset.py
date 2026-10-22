"""
Seed Realistic Malayalam Pending Batches for Human-in-the-Loop Review
"""

import os
import sys
import json
import io

if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.malayalam_cleaner import MalayalamCleaner

def generate_seed_data():
    pending_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "pending_approval")
    os.makedirs(pending_dir, exist_ok=True)

    sample_batches = [
        {
            "id": "batch_mal_tech_001",
            "name": "Regional Tech & AI Science Articles (Mathrubhumi & Tech Kerala)",
            "source": "https://mathrubhumi.com/technology",
            "timestamp": "2026-10-22 10:15:00",
            "status": "pending_approval",
            "items": [
                {
                    "id": "item_tech_01",
                    "title": "നിർമ്മിത ബുദ്ധിയും പ്രാദേശിക ഭാഷകളും",
                    "raw_text": "<div class='news-content'>നിർമ്മിത ബുദ്ധിയുടെ (AI) പുതിയ മുന്നേറ്റങ്ങൾ മലയാള ഭാഷാ സാങ്കേതികവിദ്യയെ പുതിയ ഉയരങ്ങളിലേക്ക് നയിക്കുന്നു. <p>കൂടുതൽ വിവരങ്ങൾക്ക് ബന്ധപ്പെടുക: contact@malayalam-ai.org അല്ലെങ്കിൽ ഫോൺ: +91-9847012345</p>. ഇന്റർനെറ്റിലെ ഡാറ്റ പരിശോധിക്കുമ്പോൾ ശാസ്ത്രീയമായ രീതിയിൽ അക്ഷരപ്പിശകുകൾ തിരുത്താൻ നല്&zwj;കണം.</div>"
                },
                {
                    "id": "item_tech_02",
                    "title": "ഓപ്പൺ സോഴ്സ് മലയാളം കമ്പ്യൂട്ടിംഗ്",
                    "raw_text": "സ്വതന്ത്ര മലയാളം കമ്പ്യൂട്ടിംഗ് (SMC) കൂട്ടായ്മ മലയാളം അക്ഷരക്കൂട്ടങ്ങൾക്കും ഡിജിറ്റൽ ഫോണ്ടുകൾക്കും വേണ്ടി സ്തുത്യർഹമായ പ്രവർത്തനങ്ങൾ നടത്തിവരുന്നു. യൂണിക്&zwj;കോഡ് മാനദണ്ഡങ്ങൾ പാലിക്കുന്നതിലൂടെ ഏത് ഉപകരണത്തിലും മലയാളം കൃത്യമായി വായിക്കാൻ സാധിക്കും. <span>Ref: info@smc.org.in</span>"
                },
                {
                    "id": "item_tech_03",
                    "title": "മെഷീൻ ട്രാൻസ്ലേഷൻ പരിമിതികൾ",
                    "raw_text": "<article>പലപ്പോഴും യാന്ത്രിക വിവർത്തനങ്ങൾ (Machine Translation) കൃത്യതയുള്ളതല്ല ആകുന്നു. വ്യാകരണപരമായ അബദ്ധങ്ങൾ ഒഴിവാക്കുന്നതിനായി വലിയ തോതിലുള്ള മലയാളം കോർപ്പസ് ഡാറ്റ ആവശ്യമുണ്ട്. Aadhaar: 1234 5678 9012 verification.</article>"
                }
            ]
        },
        {
            "id": "batch_mal_history_002",
            "name": "Kerala History & Cultural Archives (Wikipedia Excerpts)",
            "source": "https://ml.wikipedia.org/wiki/Kerala_History",
            "timestamp": "2026-10-22 11:45:00",
            "status": "pending_approval",
            "items": [
                {
                    "id": "item_hist_01",
                    "title": "കേരളത്തിന്റെ പ്രാചീന വാണിജ്യ ചരിത്രം",
                    "raw_text": "<p>പ്രാചീന കാലം മുതൽ തന്നെ കേരളം സുഗന്ധവ്യഞ്ജന വ്യാപാരത്തിന്റെ പ്രധാന കേന്ദ്രമായിരുന്നു. മുസിരിസ് തുറമുഖം വഴി റോമാക്കാരുമായും അറബികളുമായും ശക്തമായ വാണിജ്യബന്ധം നിലനിന്നിരുന്നു എന്ന് ചരിത്ര രേഖകൾ സാക്ഷ്യപ്പെടുത്തുന്നു.</p>"
                },
                {
                    "id": "item_hist_02",
                    "title": "സാഹിത്യ പാരമ്പര്യവും തുഞ്ചത്ത് എഴുത്തച്ഛനും",
                    "raw_text": "ആധുനിക മലയാള ഭാഷയുടെ പിതാവായി കണക്കാക്കപ്പെടുന്ന തുഞ്ചത്ത് രാമാനുജൻ എഴുത്തച്ഛൻ കിളിപ്പാട്ട് പ്രസ്ഥാനത്തിലൂടെ ഭാഷയ്ക്ക് പുതിയൊരു ദിശാബോധം നല്&zwj;കി. അദ്ധ്യാത്മരാമായണം കിളിപ്പാട്ട് ഇതിന് ഉത്തമ ഉദാഹരണമാണ്. Helplines: 0471-2345678."
                }
            ]
        }
    ]

    for batch in sample_batches:
        processed_items = []
        densities = []
        fluencies = []

        for item in batch["items"]:
            cleaned_data = MalayalamCleaner.clean_document(item["raw_text"], batch["source"])
            processed_items.append({
                "id": item["id"],
                "title": item["title"],
                "raw_text": item["raw_text"],
                "cleaned_text": cleaned_data["cleaned_text"],
                "malayalam_density": cleaned_data["malayalam_density"],
                "density_passed": cleaned_data["density_passed"],
                "chillu_fixes": cleaned_data["chillu_fixes_count"],
                "pii_redacted": cleaned_data["pii_redacted_count"],
                "fluency_score": cleaned_data["fluency_score"],
                "quality_rating": cleaned_data["quality_rating"],
                "passed_validation": cleaned_data["passed_validation"],
                "audit_notes": cleaned_data["quality_audit"]
            })
            densities.append(cleaned_data["malayalam_density"])
            fluencies.append(cleaned_data["fluency_score"])

        batch_record = {
            "id": batch["id"],
            "name": batch["name"],
            "source": batch["source"],
            "timestamp": batch["timestamp"],
            "status": batch["status"],
            "total_records": len(processed_items),
            "avg_density": round(sum(densities) / len(densities), 3),
            "avg_fluency": round(sum(fluencies) / len(fluencies), 3),
            "items": processed_items
        }

        target_file = os.path.join(pending_dir, f"{batch['id']}.json")
        with open(target_file, "w", encoding="utf-8") as f:
            json.dump(batch_record, f, ensure_ascii=False, indent=2)
        print(f"✅ Generated seed batch: {target_file}")

if __name__ == "__main__":
    generate_seed_data()
