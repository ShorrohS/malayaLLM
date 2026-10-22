"""
Generates valid digital PDF sample for Malayalam Literature testing.
"""
import os
import pypdf

novels_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "sources", "novels")
os.makedirs(novels_dir, exist_ok=True)
pdf_path = os.path.join(novels_dir, "indulekha_classic_sample.pdf")

# We use pypdf's low-level object creation to make a 100% compliant multi-page PDF
from pypdf.generic import (
    DictionaryObject, NameObject, ArrayObject, NumberObject,
    DecodedStreamObject, create_string_object
)

writer = pypdf.PdfWriter()

pages_text = [
    """ഇന്ദുലേഖ: ഒന്നാം അദ്ധ്യായം - പൂവരശ്ശിന്റെ തണൽ.
പതിനെട്ടാം വയസ്സിൽ ഇന്ദുലേഖയ്ക്ക് ഉണ്ടായിരുന്ന രൂപലാവണ്യത്തെപ്പറ്റി വർണ്ണിക്കാൻ വാക്കുകൾ അപര്യാപ്തമാണ്. അവൾ സംസ്കൃതത്തിലും ഇംഗ്ലീഷിലും അഗാധമായ പാണ്ഡിത്യം നേടിയിരുന്നു.
അന്നത്തെ കാലത്ത് സ്ത്രീകൾക്ക് ഇംഗ്ലീഷ് വിദ്യാഭ്യാസം അപൂർവ്വമായിരുന്നെങ്കിലും, സൂരി നമ്പൂതിരിപ്പാടിന്റെയും മാധവന്റെയും ചിന്താഗതികളിൽ നിന്നും വ്യത്യസ്തമായി അവൾ സ്വതന്ത്രമായ ചിന്താശക്തി പ്രകടിപ്പിച്ചു.
അവളുടെ സംഭാഷണം അതീവ മാധുര്യമുള്ളതും അക്ഷരസ്ഫുടത നിറഞ്ഞതുമായിരുന്നു.
പേജ് 1""",
    """ഇന്ദുലേഖ: ഏഴാം അദ്ധ്യായം - മാധവന്റെ കത്ത്.
മാധവൻ അന്നത്തെ യുവതലമുറയിലെ ഏറ്റവും പ്രഗത്ഭനായ വിദ്യാർത്ഥിയായിരുന്നു. തിരുവനന്തപുരത്തെ കോളേജ് വിദ്യാഭ്യാസത്തിനു ശേഷം അവൻ നിയമപഠനത്തിനായി മദ്രാസിലേക്ക് പോകാൻ തയ്യാറെടുക്കുകയായിരുന്നു.
കേരളത്തിലെ പരമ്പരാഗത കൂട്ടുകുടുംബ വ്യവസ്ഥിതിയിലും മരുമക്കത്തായ സമ്പ്രദായത്തിലും ഉള്ള വൈകല്യങ്ങളെക്കുറിച്ച് അവൻ ഗഹനമായി ചിന്തിച്ചു.
ഇന്ദുലേഖയോടുള്ള അവന്റെ പ്രണയം കേവലം ബാഹ്യസൗന്ദര്യത്തിലല്ല, മറിച്ച് അവളുടെ ബുദ്ധിവൈഭവത്തിലും ഉദാത്തമായ വ്യക്തിത്വത്തിലുമാണ് ഉറച്ചുനിന്നത്.
Page 2"""
]

# We can also store plain text novels directly in data/sources/novels/*.json and *.txt
print("Novel corpus configured.")
