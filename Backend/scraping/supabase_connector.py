
from supabase import create_client, Client
from dotenv import load_dotenv
import os
import json
import requests
import logging
import scrape_data

load_dotenv()

logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

SUPABASE_URL:str = os.getenv("SUPABASE_URL","")
SUPABASE_KEY:str = os.getenv("SUPABASE_KEY","")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def update_details():
    try:
        bucket_name = os.getenv("SUPABASE_BUCKET","")
        names = ["RELATIVE_DETAILS","RELATIVE_FUNDS","RELATIVE_STONES"]
        for i in names:
            json_mod_data = {}
            if i=="RELATIVE_DETAILS":
                modified_data = scrape_data.mutual_fund_details()
                if len(modified_data) != 0:
                    json_mod_data = json.dumps(modified_data,indent=2)
            elif i=="RELATIVE_FUNDS":
                modified_data = scrape_data.mutual_funds()
                if len(modified_data) != 0:
                    json_mod_data = json.dumps(modified_data,indent=2)
            elif i=="RELATIVE_STONES":
                modified_data = scrape_data.gold_silver_details()
                if len(modified_data) != 0:
                    json_mod_data = json.dumps(modified_data,indent=2)
            path = os.getenv(i,"")
            result = supabase.storage.from_(bucket_name).update(
                path,
                json_mod_data.encode('utf-8'),
                file_options={"content-type": "application/json", "upsert": "true",}
            )

        logger.info("Data updated successfully")
        return {"status":200}
    except Exception as e:
        logger.error(f"Error updating details: {e}")
        return {"status":400}


#Use the absolute path here
def get_details(info:str):
    try:
        supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)
        # Generate a new signed URL
        abs_path:str = ""
        if info == "mutual_funds":
            # abs_path = os.getenv("FUNDS_BUCKET_URL","")
            abs_path = os.getenv("RELATIVE_FUNDS","")
        elif info == "mutual_funds_details":
            # abs_path = os.getenv("DETAILS_BUCKET_URL","")
            abs_path = os.getenv("RELATIVE_DETAILS","")
        elif info == "precious_stone_details":
            # abs_path = os.getenv("STONES_BUCKER_URL","")
            abs_path = os.getenv("RELATIVE_STONES","")
        else:
            return {"status":400}

        signed_url = supabase.storage.from_("scrape-dravina-data").create_signed_url(
            f"{abs_path}", 
            expires_in=3600  # 1 hour expiration
        )

        url = signed_url["signedURL"]
        response = requests.get(url)
        response.raise_for_status()
        if response.status_code != 200:
            return {"status":400}
        ans = response.json()
        return {"status":200,"data":ans}
    except Exception as e:
        logger.error(f"Error getting details: {e}")
        return {"status":400}
