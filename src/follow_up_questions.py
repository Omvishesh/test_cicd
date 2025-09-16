import os
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Depends, Query
from textwrap import dedent
import time
from time import gmtime, strftime
from fastapi.security.api_key import APIKeyHeader
#from crewai import LLM
import json
from google import genai
from google.genai import types

# load_dotenv("prod.env")
# Original file name: follow_up_1stage.py

import logging

logging.basicConfig(
    level=logging.INFO,  # Change to DEBUG for more details
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
)
logger = logging.getLogger(__name__)

GOOGLE_API_KEY = os.getenv("GEMINI_API_KEY")
#print(GOOGLE_API_KEY)
API_KEY = os.getenv("ACQ_API_KEY")
API_KEY_NAME = "access_token"
api_key_header = APIKeyHeader(name=API_KEY_NAME, auto_error=True)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    print(f"Received API Key: {api_key}")
    if api_key != API_KEY:
        raise HTTPException(status_code=403, detail="Invalid API Key")
    return api_key

followup = FastAPI(title="Server for follow-up queries")

#llm=LLM(model='gemini/gemini-2.0-flash',api_key=GOOGLE_API_KEY, )

import re
import json

def handle_json_response(raw_data):
    try:
        #print("Raw output:")
        #print(raw_data)
        #print("*****")
        if not isinstance(raw_data, str):
            raise Exception("Raw data must be a string.")

        # Remove code fences if present
        raw_data = raw_data.replace("```json", "").replace("```", "").strip()

        # Fix common formatting issues
        #raw_data = re.sub(r"'", '"', raw_data)  # Single to double quotes -- disabled for natural language output
        #raw_data = re.sub(r",\s*([}\]])", r"\1", raw_data)  # Remove trailing commas

        # Try to extract multiple JSON objects (best-effort)
        object_matches = re.findall(r'\{[^{}]*\}', raw_data, re.DOTALL)

        valid_objects = []
        for obj_str in object_matches:
            try:
                obj = json.loads(obj_str)
                valid_objects.append(obj)
            except json.JSONDecodeError:
                continue  # skip broken ones
        #print("Modified output:") 
        #print(raw_data)
        #print("*****")

        if not valid_objects:
            raise Exception("No valid JSON objects found.")

        return valid_objects

    except Exception as e:
        raise Exception(f"Error processing JSON: {str(e)}")

@followup.post("/query", dependencies=[Depends(verify_api_key)])
async def run_query(user_query: str = Query(..., description="Summary output from the DeepInsights portal")):
    """Analyze the summary produced by the DeepInsights UI and generate follow-up questions."""
    start_time = time.time()
    logger.info(f"START: Processing query: {user_query}")    
    try:
        logger.info(f"User Query Received: {user_query}")
        #inputs = {"query": user_query}
        curdate = strftime("%Y-%m-%d", gmtime())
        inputs = {"query": user_query, "curdate": curdate}

        max_retries = 3
        retry_delay = 3  # in seconds

        for attempt in range(1, max_retries + 1):
            result=None
            try:
                client = genai.Client(api_key=GOOGLE_API_KEY)

                logger.info(f"Attempt {attempt} to process query")

                response = client.models.generate_content(
                model="gemini-2.0-flash",
                config=types.GenerateContentConfig(
                    system_instruction="""You are an expert summarizer with deep background in finance and economics, especially focused on India. You will read the information provided in the user query and generate a set of EXACTLY four (4) follow up questions for further research. You will provide them in JSON format with the fields marked as Q1, Q2, Q3, Q4 with each containing one unique question. 
                    IMPORTANT: Base your questions and outputs ONLY on the user query and nothing else.
                    IMPORTANT: Make sure each question contains no more than 16 words.
                    IMPORTANT: Make sure your observations and follow-up questions are relevant to the user query.
                    IMPORTANT: Make sure your questions related to the key entities mentioned in the user query, as well as numerical data points where relevant.
                    AVOID hallucinating questions about the general state of the economy unrelated to the user query.
                    MOST IMPORTANT: PROVIDE THE RESPONSE PURELY AS THE JSON, WITH NO TEXT BEFORE OR AFTER. DO NOT INCLUDE ANY QUOTES AROUND THE JSON.
                    """),
                    contents=user_query
                )
                
                parsed_data = handle_json_response(response.text)
                #parsed_data = response.text
                logger.info(f"Response: {parsed_data}")
                total_time = time.time()-start_time
                logger.info(f"Total processing time: {total_time:.2f} seconds")
                return {
                        "query": user_query,
                        "result": parsed_data
                }

            except Exception as inner_e:
                logger.warning(f"Attempt {attempt} failed: {inner_e}")
                try:
                    if result and hasattr(result, "token_usage"):
                       logger.info(f"(Attempt {attempt}) Token usage before failure: {result.token_usage}")
                except Exception as e:
                    logger.warning(f"Could not log token usage: {e}")
                if attempt < max_retries:
                    time.sleep(retry_delay)
                else:
                    raise 

    except HTTPException as e:
        raise e
    except Exception as e:
        error_message = str(e)
        logger.error(f"Error: {error_message}")
        return {"error": error_message}

#query = "The current repo rate set by the Reserve Bank of India as of April 2025 is 6.50%. This rate has been maintained consistent with recent monetary policy decisions, as indicated in the evidence reviewed. The repo rate remains unchanged at this level to support the economy while managing inflationary pressures effectively."
#query = "The Monetary Policy Committee (MPC) decided to reduce the policy repo rate in February 2025 despite geopolitical uncertainties due to a combination of domestic economic factors and the evolving macroeconomic environment. The key insights and trends that influenced this decision are as follows:  1. Domestic Economic Indicators: - Inflation Trends: The Consumer Price Index (CPI) data for 2024 and early 2025 showed a decline in inflation rates. For instance, the inflation rate in January 2025 was 4.26%, and it further decreased to 3.61% in February 2025. This downward trajectory in inflation provided the MPC with the necessary space to focus on supporting economic growth.  - Growth Outlook: The domestic economy was experiencing a slowdown, with growth impulses weakening. The MPC noted that growth was expected to recover but remain below the levels of the previous year. This underscored the need for monetary policy support to stimulate economic activity.  2. Monetary Policy Stance: - The MPC voted unanimously to reduce the policy repo rate by 25 basis points to 6.25%. This decision was accompanied by a shift in the monetary policy stance from calibrated tightening to neutral. The neutral stance provided the MPC with the flexibility to respond to the evolving macroeconomic environment, balancing the need to support growth with the requirement to keep inflation within the target range.  3. Risks and Uncertainties: - Global Factors: The MPC acknowledged the risks posed by excessive volatility in global financial markets, uncertainties in global trade policies, and adverse weather events. However, these external factors were outweighed by the domestic economic indicators, which suggested that the primary focus should be on supporting growth.  - Domestic Risks: The MPC also considered risks such as fiscal slippage concerns, rising input costs, and the impact of minimum support prices (MSPs). However, these risks were deemed manageable given the current inflation outlook and the expected moderation in cost pressures.  4. Historical Context: - The MPC's decision in February 2025 was consistent with its past behavior. For example, in February 2019, the MPC reduced the policy repo rate by 25 basis points due to easing headline inflation, a stable crude oil price outlook, and moderation in cost pressures. This historical context suggests that the MPC tends to prioritize domestic economic conditions over external uncertainties when making rate decisions.  Conclusion: The MPC's decision to reduce the policy repo rate in February 2025 was primarily driven by the easing of domestic inflation, the need to support economic growth, and the flexibility provided by the neutral monetary policy stance. Despite geopolitical uncertainties, the MPC prioritized the domestic economic environment, which provided the necessary space for monetary policy easing."
#print(run_query(query))














