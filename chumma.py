# from mem0 import Memory
# from mem0.configs.base import MemoryConfig, LlmConfig, EmbedderConfig, VectorStoreConfig
# import os
# import json

# gemini_api_key = os.getenv("GOOGLE_API_KEY")

# llm_config_data = {
#     'api_key': gemini_api_key,
#     'model': 'gemini-2.5-flash'
# }

# embed_config_data = {
#     'api_key': gemini_api_key,
#     'model': 'models/text-embedding-004'
# }

# qdrant_specific_config_data = {
#     "collection_name": "my_mem0_gemini_collection",
#     "path": r"E:/qdrant_data_gemini",
#     "on_disk": True,
#     "embedding_model_dims": 768                    
# }


# configs = MemoryConfig(
#     llm=LlmConfig(
#         provider='gemini',
#         config=llm_config_data
#     ),
#     embedder=EmbedderConfig(
#         provider='gemini',
#         config=embed_config_data
#     ),
#     vector_store=VectorStoreConfig(
#         provider='qdrant',
#         config=qdrant_specific_config_data # This dict will be used to initialize the Qdrant client
#     )
# )

# client = Memory(config=configs)

# result = client.add("Likes to play cricket at weekend",user_id="krishna",metadata={"category":"hobbies"})
# print(json.dumps(result))

# allmem = client.search("What kind of sports does user paly ?",user_id="krishna")
# print(json.dumps(allmem))



import json
import requests
from supabase import create_client, Client
import os
from dotenv import load_dotenv
from scraping import scrape_data

load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

#We are going to call this function at regular intervals
#Use relative paths here
def update_details():
    try:
        bucket_name = os.getenv("SUPABASE_BUCKET")
        names = ["RELATIVE_DETAILS","RELATIVE_FUNDS"]
        for i in names:
            json_mod_data = {}
            if i=="RELATIVE_DETAILS":
                modified_data = scrape_data.mutual_fund_details()
                json_mod_data = json.dumps(modified_data,indent=2)
            elif i=="RELATIVE_FUNDS":
                modified_data = scrape_data.mutual_funds()
                json_mod_data = json.dumps(modified_data,indent=2)
            # Upload the modified file back to the bucket
            path = os.getenv(i)
            result = supabase.storage.from_(bucket_name).update(
                path,
                json_mod_data.encode('utf-8'),
                file_options={"content-type": "application/json", "upsert": "true",}
            )
        return "fine"
    except Exception as e:
        return {}

#Use the absolute path here
def get_details(abs_path:str):
    try:
        response = requests.get(abs_path)
        response.raise_for_status()
        ans = response.json()
        return ans
    except Exception as e:
        return {}


def call(option:int,task:int):
    if task == 0:
        if option == 0:
            return get_details(os.getenv("DETAILS_BUCKET_URL"))
        elif option==1:
            return get_details(os.getenv("FUNDS_BUCKET_URL"))
        

print(get_details(os.getenv("DETAILS_BUCKET_URL")))