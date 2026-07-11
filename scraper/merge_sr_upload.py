# -*- coding: utf-8 -*-
# ================================================================
# merge_sr_upload.py — SR (sarkari) upload merge entrypoint
# ================================================================
# User PC par scraper_sarkari.py roz chalate hain — wo apni local
# copy mein "merged_sarkari_data.json" (intermediate) banata hai.
# User us ek file ko repo root mein push karta hai. Ye script use
# repo ke Complete_Jobs_Full_Data.json mein merge karta hai — sirf
# "sarkari_data" source replace hota hai, baaki (freejobalert_unified,
# education_jobs) UNCHANGED rehte hain.
#
# Run (cwd = repo root):  python scraper/merge_sr_upload.py
# ================================================================

import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from scraper_merge import merge_into_json

SR_FILE = "merged_sarkari_data.json"


def main():
    if not os.path.exists(SR_FILE):
        print(f"[ERROR] {SR_FILE} not found at repo root — nothing to merge.")
        sys.exit(1)

    with open(SR_FILE, encoding="utf-8") as f:
        fresh_data = json.load(f)

    merge_into_json(source="sarkari_data", fresh_data=fresh_data, scraper_error="")
    print("[OK] sarkari_data merged into Complete_Jobs_Full_Data.json")


if __name__ == "__main__":
    main()
