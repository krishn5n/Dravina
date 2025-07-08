from mem0 import Memory
from mem0.configs.base import MemoryConfig, LlmConfig, EmbedderConfig, VectorStoreConfig
import os
import json

# Make sure your Google API Key is set as an environment variable
# os.environ["GOOGLE_API_KEY"] = "YOUR_GEMINI_API_KEY"

# It's good practice to get API keys from environment variables
gemini_api_key = os.getenv("GOOGLE_API_KEY")

# 1. Define LLM Configuration
llm_config_data = {
    'api_key': gemini_api_key,
    'model': 'gemini-2.5-flash'
}

# 2. Define Embedder Configuration
embed_config_data = {
    'api_key': gemini_api_key,
    'model': 'models/text-embedding-004'
}

# 3. Define Vector Store Configuration (Qdrant specific)
# This is where you specify the Qdrant parameters, including the embedding_model_dims
qdrant_specific_config_data = {
    "collection_name": "my_mem0_gemini_collection", # Choose a meaningful name
    "path": r"E:/qdrant_data_gemini",                # Path for persistent storage
    "on_disk": True,                                # Enable persistent storage
    "embedding_model_dims": 768                    # Crucial: Match text-embedding-004's output
}


# Create the MemoryConfig object by instantiating the nested config classes
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

result = client.add("Likes to play football",user_id="krishna",metadata={"category":"hobbies"})
print(json.dumps(result))

allmem = client.get_all(user_id="krishna")
print(json.dumps(allmem))