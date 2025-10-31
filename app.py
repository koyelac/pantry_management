from flask import Flask, request, render_template, jsonify
#import json
from datetime import datetime
from werkzeug.utils import secure_filename
import send_msg as msgapp
import agent3
import agent_image as ImageAgent
import agent
import mytools

app = Flask(__name__)

@app.route('/')
def index():
    """Landing Page - Serve the main HTML template"""
    return render_template('index.html')


@app.route("/message", methods=['POST'])
def reply():
    """
    Handles incoming messages (e.g., from WhatsApp/Twilio webhook) and sends a
    RAG-generated response back to the user.
    """
    try:
        # Access data synchronously
        form_data = request.form
        from_value = form_data.get('From', '')
        # Split to get the number
        whatsapp_num = from_value.split("whatsapp:")[-1]
        # Extract the message
        body = form_data.get('Body', '')
        if not whatsapp_num or not body:
             print("Error: Missing 'From' or 'Body' in webhook data.")
             return "Missing data", 400
        if body == 'Donate':
            items = mytools.fetch_list()
            if items["success"]:
                print(f"Sending the RAG response to this number: {whatsapp_num}")
                msg = agent3.find_donation_centers(items["checklist"])
        
                message = f"Thank You for choosing to donate. You can consider the following centers\n"+msg
                msgapp.send_message(message)
                return ""
            else:
                print(f"Sorry system has encountered an error {items['error']}")
            
    except Exception as e:
        print(f"An error occurred during message processing: {e}")
        # Return a non-200 status code to signal failure 
        return "Internal Server Error", 500
    
@app.route('/upload', methods=['POST'])
def upload_file():
    #Checking if image file key is in the request.files dictionary
    if 'file' not in request.files:
        return jsonify({"success":False, "message":"No file part in the request"}), 400
    #2. Get file object from request
    file = request.files['file']
    # 3. Check if the user submitted the form without selecting a file
    # The browser might end an empty file part with no filename
    if file.filename == '':
        return jsonify({"success":False, "message": "No selected file"}), 400
    # 4. If a file is present and has a filename proceed
    if file:
        try:
            # Sanitize file name
            filename = secure_filename(file.filename)
            # read file bytes
            file_bytes = file.read()
            result = ImageAgent.upload_image(file_bytes)
            print("Upload result:", result)
            if result["success"]:
                message = f"File '{filename}' uploaded successfully and inventory updated"
                return jsonify({"success": True, "message": message, "plan": result.get("msg", "Inventory updated")})
            else:
                message = f'Upload failed: {result.get("error", result.get("message", "Unknown error"))}'
                return jsonify({"success": False, "message": message}), 500
        except Exception as e:
            print(f"Error occured {e}")
            return jsonify({"success": False, "message": "An error occurred during file processing."}), 500
     # This is a fallback, though the checks above should cover most cases
    return jsonify({"success": False, "message": "Unknown error occurred"}), 500

@app.route('/update-inventory', methods=['POST'])
def update_inventory():
    """Update pantry inventory using the routine agent"""
    try:
        # Call the routine agent function
        result = agent.routine_agent()
        
        if result:
            return jsonify({
                "success": True, 
                "message": "Inventory updated successfully",
                "timestamp": str(datetime.now())
            })
        else:
            return jsonify({
                "success": False,
                "message": result["error"]
            }), 500
            
    except Exception as e:
        print(f"Error during inventory update: {e}")
        return jsonify({
            "success": False,
            "message": f"An error occurred during inventory update: {str(e)}"
        }), 500
    
    
if __name__ == "__main__":
        app.run(debug=True)
