from mem0 import Memory
from mem0.configs.base import MemoryConfig, LlmConfig, EmbedderConfig, VectorStoreConfig
import os
import json

gemini_api_key = os.getenv("GOOGLE_API_KEY")

llm_config_data = {
    'api_key': gemini_api_key,
    'model': 'gemini-2.5-flash'
}

embed_config_data = {
    'api_key': gemini_api_key,
    'model': 'models/text-embedding-004'
}

qdrant_specific_config_data = {
    "collection_name": "my_mem0_gemini_collection",
    "path": r"E:/qdrant_data_gemini",
    "embedding_model_dims": 768                    
}


configs = MemoryConfig(
    llm=LlmConfig(
        provider='gemini',
        config=llm_config_data
    ),
    embedder=EmbedderConfig(
        provider='gemini',
        config=embed_config_data
    ),
    vector_store=VectorStoreConfig(
        provider='qdrant',
        config=qdrant_specific_config_data # This dict will be used to initialize the Qdrant client
    )
)

client = Memory(config=configs)

result = client.add("Likes to play cricket at weekend",user_id="krishna",metadata={"category":"hobbies"})
print(json.dumps(result))

allmem = client.get_all(user_id="krishna")
print(json.dumps(allmem))
