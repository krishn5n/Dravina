import json
import requests
import os
from google import genai
from google.genai import types
import getkb
from typing import List
from dotenv import load_dotenv

load_dotenv()

# Fixed function declaration - corrected ARRAY type
get_mutual_funds_set_declaration = {
    "name": "get_mutual_funds_set",
    "description": "Get specific mutual fund recommendations with detailed information using fund types as tags. This should be called AFTER getting fund types from details_to_types to get actual fund names and details.",
    "parameters": {
        "type": "object",
        "properties": {
            "tags": {
                "type": "array",  # Fixed: was "ARRAY", should be "array"
                "items": {
                    "type": "string"  # Fixed: was "STRING", should be "string"
                },
                "description": "Array of fund types (like 'Large Cap Funds', 'Multi Cap Funds') obtained from details_to_types tool to get specific fund recommendations"
            }
        },
        "required": ["tags"]
    }
}

def get_mutual_funds_set(tags: List[str]) -> List[dict[str, str]]:
    '''
    Get details of mutual funds using tags specified like equity or debt.

    Args:
        tags: List of tags used for accessing mutual funds

    Returns:
        List of dictionaries of data consisting of details
    '''
    try:
        mutual_list = getkb.obtain_mutual_funds(tags)
        return mutual_list
    except Exception as e:
        print(f"Error getting mutual funds: {e}")
        return []

# Fixed function declaration - corrected STRING type and enum values
get_info_about_fund_declaration = {
    "name": "get_info_about_fund",
    "description": "Get details about a specific fund type",
    "parameters": {
        "type": "object",
        "properties": {
            "based_category": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "enum": ["structure", "asset class", "investment objectives", "portfolio management", "speciality", "risk appetite"],
                "description": "Select the classification category under which to suggest mutual fund types"
            },
            "fund": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "description": "Type of fund like equity or debt for which details are required"
            }
        },
        "required": ["based_category", "fund"]
    }
}

def get_info_about_fund(based_category: str, fund: str):
    ''' 
    Get details about a specific fund type and a classification category.

    Args:
        based_category: Select the classification category under which to suggest mutual fund types
        fund: Type of fund like equity or debt for which details are required
        
    Returns:
        Dictionary with fund information
    '''
    try:
        fund_info = getkb.obtain_fund_type_info(based_category, fund)
        return fund_info
    except Exception as e:
        print(f"Error getting fund info: {e}")
        return {"result": "Error retrieving fund information"}

# Fixed function declaration - corrected STRING type
details_to_types_declaration = {
    "name": "details_to_types",
    "description": "Get fund types based on risk and duration preferences. This should be called FIRST to determine suitable fund types, then use get_mutual_funds_set with these types as tags.",
    "parameters": {
        "type": "object",
        "properties": {
            "risk": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "enum": ["high risk", "medium risk", "low risk", "all risk"],
                "description": "Risk level preference: high, medium, low or all risks. Provide as 'all risk' if unspecified."
            },
            "time": {
                "type": "string",  # Fixed: was "STRING", should be "string"
                "enum": ["short term", "medium term", "long term", "all term"],
                "description": "Duration best suited where less than 3 years implies short term, 3-5 implies medium and 5+ years for long term. Provide as 'all term' if unspecified."
            },
        },
        "required": ["risk", "time"]
    }
}

def details_to_types(risk: str, time: str):
    risk = risk.lower()
    time = time.lower()

    risk_data = {
        'high risk': {
            'short term': ['Credit Risk Fund', 'Hybrid Fund'],
            'medium term': ['Multi Cap Funds'],
            'long term': ['Mid Cap Funds', 'Small Cap Funds']
        },
        'medium risk': {
            'short term': ['Low duration funds', 'Ultra short duration funds'],
            'medium term': ['Balanced Advantage funds'],
            'long term': ['Multi Cap Funds'],
        },
        'low risk': {
            'short term': ['Overnight funds', 'Liquid Funds'],
            'medium term': ['Short duration funds', 'Gilt Funds'],
            'long term': ['Large Cap Funds']
        }
    }

    try:
        if risk == 'all risk' and time == 'all term':
            return risk_data
        elif risk == 'all risk':
            final_value = {'high risk': [], 'medium risk': [], 'low risk': []}
            for i in risk_data:
                if time in risk_data[i]:
                    final_value[i] = risk_data[i][time]
                else:
                    final_value[i] = []
            return final_value
        elif time == 'all term':  # Fixed: was 'all time', should be 'all term'
            return risk_data.get(risk, {})
        else:
            return risk_data.get(risk, {}).get(time, [])
    except Exception as e:
        print(f"Error in details_to_types: {e}")
        return []

def call_tool(name, args):
    """Enhanced tool calling with error handling"""
    try:
        if name == "get_mutual_funds_set":
            return get_mutual_funds_set(**args)
        elif name == "get_info_about_fund":
            return get_info_about_fund(**args)
        elif name == "details_to_types":
            return details_to_types(**args)
        else:
            return {"error": f"Unknown tool: {name}"}
    except Exception as e:
        print(f"Error calling tool {name}: {e}")
        return {"error": f"Error executing {name}: {str(e)}"}

def get_finance_advice(query):
    system_prompt = '''
    You are a helpful finance assistant that provides personalized investment insights using reasoning and available tools.

    # MANDATORY TOOL USAGE WORKFLOW
    You MUST follow this exact sequence:
    
    1. **STEP 1 - Get Fund Types**: Call `details_to_types` based on user's risk appetite and investment timeline
    
    2. **STEP 2 - Get Specific Funds (MANDATORY)**: Call `get_mutual_funds_set` with fund types as tags
       - CRITICAL: Remove the word "fund" from tags when calling this tool
       - Example: "Large Cap Funds" → use tag "large cap"
       - Example: "Multi Cap Funds" → use tag "multi cap"  
       - Example: "Equity Funds" → use tag "equity"
       - Example: "Debt Funds" → use tag "debt"
    
    3. **STEP 3 - Optional Details**: Call `get_info_about_fund` for additional fund type information if needed
    
    4. **STEP 4 - Final Result**: Provide recommendations with actual fund names and details
    
    # CRITICAL RULES
    - **NEVER provide final results without calling get_mutual_funds_set**
    - **ALWAYS convert fund types to proper tags by removing "fund" and "funds"**
    - **Provide specific fund names, not just fund types**
    - **Start final results with "Result - " in markdown format**

    # Tax Information to Include
    - Investment money are taxable
    - For equity funds, Long Term Capital Gains (12+ months) are taxed at 10% above Rs 1 Lakh exemption
    - Short Term Capital Gains (<12 months) are taxed at 15%
    - For debt funds, indexation benefit is available for capital gains

    # Investment Focus Areas
    - Mutual funds (equity/debt mix based on age and risk profile)
    - Gold and silver as hedge against inflation (when relevant)
    '''

    try:
        client = genai.Client()
        tools = types.Tool(function_declarations=[
            get_mutual_funds_set_declaration,
            get_info_about_fund_declaration,
            details_to_types_declaration
        ])
        config = types.GenerateContentConfig(
            tools=[tools],
            thinking_config=types.ThinkingConfig(
                thinking_budget=-1  # Dynamic thinking
            )
        )
        
        contents = [
            types.Content(
                role="user", parts=[types.Part(text=f"{system_prompt}")]
            ),
            types.Content(
                role="user", parts=[types.Part(text=f"{query}")]
            )
        ]

        loop = 1
        max_loops = 10
        
        while loop < max_loops:
            try:
                response = client.models.generate_content(
                    model="gemini-2.5-flash",
                    contents=contents,
                    config=config
                )

                candidate = response.candidates[0]
                parts = candidate.content.parts

                # Check if we have a final result
                for part in parts:
                    if part.text and part.text.startswith("Result -"):
                        print("Final result received")
                        return part.text
                    
                    if part.function_call:
                        name = part.function_call.name
                        args = dict(part.function_call.args)  # Convert to dict
                        
                        print(f"Calling tool: {name} with args: {args}")
                        result = call_tool(name, args)
                        print(f"Tool result obtained",len(result))
                        
                        # If details_to_types was called, suggest calling get_mutual_funds_set next
                        if name == "details_to_types":
                            print("Hint: Next step should be calling get_mutual_funds_set with fund types as tags")
                        
                        function_response_text = json.dumps({
                            "tool_used": name,
                            "response": result
                        })
                        
                        contents.append(types.Content(
                            role="user",
                            parts=[types.Part(text=function_response_text)]
                        ))
                    else:
                        if part.text:
                            print(f"Model response: {part.text[:200]}...")
                        contents.append(types.Content(role="model", parts=[part]))
                
                loop += 1
                
            except Exception as e:
                print(f"Error in generation loop {loop}: {e}")
                return f"Error: {str(e)}"
        
        return "Maximum iterations reached without final result"
        
    except Exception as e:
        print(f"Error in get_finance_advice: {e}")
        return f"Error initializing finance advisor: {str(e)}"

# Test the function
if __name__ == "__main__":
    try:
        result = get_finance_advice(
            "I earn close to 40000 and i spend 10000 on fixed expenses, 1000 on variable and 15000 on casual expenses. I am of age 33 and i want to save money such that by to live happily and have savings by 50. I dont know if i am ready to take risk"
        )
        print(result)
    except Exception as e:
        print(f"Error running finance advisor: {e}")