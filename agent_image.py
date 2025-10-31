import google.generativeai as genai
import io
import asyncio
import base64
from typing import Dict, List, Optional, Any
from PIL import Image
from dataclasses import dataclass
import mytools
import json
import os
from dotenv import load_dotenv
# Image processing agent. Uses Gemini OCR to detect and extract image info 

load_dotenv()
api_key = os.getenv("API_KEY")
genai.configure(api_key = api_key)

class GeminiReceiptProcessor:
    """Handles receipt image processing using Gemini API"""
    def __init__(self, model_name:str = "gemini-flash-latest"):
        self.model = genai.GenerativeModel(model_name)
        self.extraction_prompt = self._create_extraction_prompt()
    def _create_extraction_prompt(self) -> str:
        """Create a comprehensive prompt for data extraction from image"""
        return """
        You are a food image data extraction expert.
        Analyze the uploaded image and
        extract ALL food-related information.
        The image can be of a fruit or vegetable or grain or it can be of a packaged
        item or a bottle. It can contain one or multiple items. In case of
        multiple items, there can be both packaged and non-packaged food products.
    
        EXTRACTION RULES:
        1. Identify the type of food as grocery or packaged. For eg if you
        identify this an image as potato classify that as 'grocery'. If the uploaded
        image looks like a packaged product classify as 'packaged'.
        2. Extract the name as singular. For example extract apples as apple
        even if the image contains multiple apples
        3. Extract the shelf life of the packaged food product image.
        Shelf life can be presented in any of the following ways presented as options.
        #Option 1: Check for keywords like exp or EXP or 'best before' followed with a date
        #Option 2: Check for words like 'Best before 3 days from date of manufacture'
        This time denomination can be days or months too. In this case extract the
        information the manufacturing date often represented as mfg date, the number as
        int variable and the time denomination as 'd' for days and 'm' for months.
        For eg : Suppose you see a pack of juice with a label like 'mfg 14.09.2025
        best before 7 days from the date of manufacture'. Extract the info as
        14.09.2025, 7, d.
        4. If there are two dates or mention of one month and another
        date, then the full date or the month that comes later than the other
        is going to be the expiry date. 
        5. Ignore all the non food items in the image.
        RESPONSE FORMAT:
        Return a JSON object with this exact structure:
        {
            "success" : true/false,
            "items":{
                "type" : "grocery/packaged",
                "name" : "name of the food item identified",
                "expiry_date": "DD-MM-YYYY or null",
                "mfg_date" : "DD-MM-YYYY or null",
                "time_remaining" : int or null,
                "time_denom" : "d or m or null"
                }
            "confidence_score": float(0-1)
            }
            EXAMPLE OUTPUT:
            {
                "success" : true,
                "items": [
                    {
                        "type" : "grocery",
                        "name": "banana",
                        "expiry_date": null,
                        "mfg_date": null,
                        "time_remaining":null,
                        "time_denom": null
                    },
                    {
                        "type" : "packaged",
                        "name": "curd",
                        "expiry_date": null,
                        "mfg_date": "12-10-2025",
                        "time_remaining": 180,
                        "time_denom": "d"
                    }
                ]
                "confidence_score": 0.95
            }
            If you cannot extract food information or the image is unclear,
            return:
            {
                "success": false,
                "error": "Reason for failure",
                "confidence_score":0.0
            }
            ANALYZE THE IMAGE NOW:
            """
    async def process_receipt_image(self, image_data:Any) -> Dict:
        """
            Process receipt image and extract medicine information
            ARGS:
                image_data: Can be a PIL image, file path or base 64 string
            Returns:
                Dictionary with extrcated medicine data
                """
        try:
            if isinstance(image_data, str):
                # For file path
                image = Image.open(image_data)
            elif isinstance(image_data, bytes):
                image = Image.open(io.BytesIO(image_data))
            else:
                image = image_data
            # Now content generation to be placed here.
            response = self.model.generate_content([self.extraction_prompt, image])
            print(response.text)
            # Parse and check if json there
            extracted_data = self._parse_gemini_response(response.text)
            return {"success" : True, "extracted_data" : extracted_data}
        except Exception as e:
            return {
                "success" : False,
                "error" : f"Error processing image : {str(e)}",
                "confidence_score" : 0.0
                }
    def _parse_gemini_response(self, response_text : str) ->Dict:
        """Check and parse Json data from gemini reponse"""
        try:
            response_text = response_text.strip()
            start_idx = response_text.find('{')
            end_idx = response_text.rfind('}')
            if start_idx == -1 or end_idx == -1:
                return {
                    "success" : False,
                    "error" : "No JSON found enclosed in response",
                    "confidence_score" : 0.0
                    }
            json_str = response_text[start_idx:end_idx+1]
            extracted_data = json.loads(json_str) # dict conversion
            # Validate the data extracted in json
            if not self._validate_extracted_data(extracted_data):
                return {
                    "success" : False,
                    "error" : "Invalid data structure returned",
                    "confidence_score" : 0.0
                    }
            return extracted_data
        except json.JSONDecodeError as e:
            return {
                "success" : False,
                "error" : f"Failed to parse JSON for error : {str(e)}",
                "confidence_score" : 0.0
                }
    def _validate_extracted_data(self, data:Dict) -> bool:
        """Validate if essential fields are there"""
        invalids = [None, "null", "", " "]
        required_fields = ["success", "items"]
        for field in required_fields:
            if field not in data:
                return False
        return True
async def img_process(image_fl):
    #image_file = "med_image.jpg"
    image_agent = GeminiReceiptProcessor()
    response = await image_agent.process_receipt_image(image_fl)
    if response["success"]:
        updated = mytools.update_stock(response["extracted_data"])
        return updated
    else:
        return {"success" : False, "message" : response["error"]}
def upload_image(image_fl):
    response = asyncio.run(img_process(image_fl))
    return response
    
    
# python ImageAgent.py
if __name__ == "__main__":
    image_file = "food_img.jpg"
    response = upload_image(image_file)
    if response["success"]:
        print("Inventory updated. Answering from Agent")
    else:
        print(response["message"])
    
        
