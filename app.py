from flask import Flask, request, jsonify, render_template, redirect, url_for
from scope_creator import ScopeCreator
import json
import os
import datetime
import requests
from dotenv import load_dotenv
import re

# Load environment variables
load_dotenv()

app = Flask(__name__)
scope_creator = ScopeCreator()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/analyze', methods=['POST'])
def analyze():
    try:
        data = request.get_json()
        project_name = data.get('project_name')
        transcription = data.get('transcription', '')

        if not project_name:
            return jsonify({"error": "Project name is required"}), 400

        # Get initial project analysis and questions
        analysis = scope_creator.analyze_project(project_name, transcription)
        
        # Check if we got a raw response or parsed JSON
        if "raw_response" in analysis:
            return jsonify({
                "raw_response": analysis["raw_response"]
            })
        else:
            return jsonify(analysis)

    except Exception as e:
        print(f"Error in analyze: {str(e)}")
        return jsonify({"error": f"Error analyzing project requirements: {str(e)}"}), 500

@app.route('/get_follow_up', methods=['POST'])
def get_follow_up():
    try:
        data = request.get_json()
        project_name = data.get('project_name')
        current_info = data.get('current_info', {})

        if not project_name:
            return jsonify({"error": "Project name is required"}), 400

        # Get follow-up questions based on current information
        follow_up_questions = scope_creator.get_follow_up_questions(project_name, current_info)
        
        return jsonify({
            "questions": follow_up_questions
        })

    except Exception as e:
        print(f"Error in get_follow_up: {str(e)}")
        return jsonify({"error": f"Error getting follow-up questions: {str(e)}"}), 500

@app.route('/generate', methods=['POST'])
def generate():
    try:
        data = request.get_json()
        project_name = data.get('project_name')
        project_info = data.get('project_info', {})
        model = data.get('model')

        if not project_name:
            return jsonify({"error": "Project name is required"}), 400

        # Generate the scope document
        result = scope_creator.generate_scope(project_name, project_info, model)
        
        if "error" in result:
            return jsonify({"error": result["error"]}), 500
            
        return jsonify({
            "scope": result["scope"],
            "scope_id": result["id"]
        })

    except Exception as e:
        print(f"Error in generate: {str(e)}")
        return jsonify({"error": f"Error generating scope: {str(e)}"}), 500

@app.route('/save_api_key', methods=['POST'])
def save_api_key():
    try:
        data = request.get_json()
        api_key = data.get('api_key')
        
        if not api_key:
            return jsonify({'error': 'OpenRouter API key is required'}), 400
        
        # Read existing environment variables
        env_vars = {}
        if os.path.exists('.env'):
            with open('.env', 'r') as f:
                for line in f:
                    if '=' in line:
                        key, value = line.strip().split('=', 1)
                        env_vars[key] = value
        
        # Update or add OpenRouter API key
        env_vars['OPENROUTER_API_KEY'] = api_key
        
        # Write back to .env file
        with open('.env', 'w') as f:
            for key, value in env_vars.items():
                f.write(f'{key}={value}\n')
        
        return jsonify({'message': 'OpenRouter API key saved successfully'}), 200
    except Exception as e:
        return jsonify({'error': str(e)}), 500

def generate_scope(project_name, project_info, model):
    try:
        # Construct a detailed prompt that encourages comprehensive output
        prompt = f"""You are a professional scope document creator. Create an extremely detailed and comprehensive scope document for the project "{project_name}" using ALL the information provided.

Key Requirements:
1. Use EVERY piece of information from the initial analysis and ALL answers provided
2. Create an extensive, professional document with multiple detailed sections
3. Include specific technical details, timelines, and resource requirements
4. Add relevant sections even if not explicitly mentioned in the inputs
5. Format the output in clean, well-structured Markdown

Document Sections to Include:
1. Executive Summary
2. Project Overview
3. Detailed Requirements
4. Technical Specifications
5. Project Scope
6. Out of Scope Items
7. Deliverables
8. Timeline and Milestones
9. Resource Requirements
10. Risk Assessment
11. Success Criteria
12. Budget Considerations
13. Stakeholder Responsibilities
14. Quality Assurance Measures
15. Implementation Plan
16. Maintenance and Support
17. Appendices (if relevant)

Project Information:
{json.dumps(project_info, indent=2)}

Guidelines:
- Make each section HIGHLY detailed with multiple subsections
- Include specific technical requirements and implementation details
- Add relevant industry standards and best practices
- Provide clear metrics and measurable outcomes
- Include both functional and non-functional requirements
- Consider security, scalability, and maintenance aspects
- Add relevant diagrams or tables using ASCII/Markdown format
- Use bullet points and numbered lists for better readability
- Include specific technologies, tools, and methodologies
- Add contingency plans and alternative approaches
- Consider long-term maintenance and scalability

Format the entire document in clean, professional Markdown."""

        # Get the response from the AI model
        response = get_ai_response(prompt, model)
        
        # Process and clean up the response
        scope = clean_and_format_scope(response)
        
        return {"scope": scope}
    except Exception as e:
        print(f"Error generating scope: {str(e)}")
        return {"error": "Failed to generate scope document"}

def clean_and_format_scope(scope):
    """Clean and format the scope document for better presentation"""
    # Remove any potential system messages or prefixes
    if "```markdown" in scope:
        scope = scope.split("```markdown")[1].split("```")[0]
    elif "```" in scope:
        scope = scope.split("```")[1].split("```")[0]
    
    # Ensure consistent heading formatting
    lines = scope.split('\n')
    formatted_lines = []
    for line in lines:
        # Ensure proper spacing for headings
        if line.strip().startswith('#'):
            formatted_lines.append('\n' + line.strip())
        else:
            formatted_lines.append(line)
    
    return '\n'.join(formatted_lines).strip()

@app.route('/scopes')
def list_scopes():
    """List all saved scopes."""
    scopes = scope_creator.list_saved_scopes()
    
    # Format timestamps for display
    for scope in scopes:
        timestamp = scope.get("date_created")
        if timestamp:
            scope["formatted_date"] = datetime.datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
    
    return render_template('scopes.html', scopes=scopes)

@app.route('/scope/<scope_id>')
def view_scope(scope_id):
    """View a specific scope."""
    # Try to get the scope directly first
    scope_data = scope_creator.get_saved_scope(scope_id)
    
    # If not found, try to find a match among available scopes
    if not scope_data:
        # Get all scopes and check if any filename contains our scope_id
        all_scopes = scope_creator.list_saved_scopes()
        for scope in all_scopes:
            if scope_id in scope.get("id", ""):
                # Found a potential match, try with this ID instead
                print(f"Original scope_id '{scope_id}' not found, using '{scope['id']}' instead")
                scope_data = scope_creator.get_saved_scope(scope["id"])
                if scope_data:
                    # Redirect to the correct URL with the actual ID
                    return redirect(url_for('view_scope', scope_id=scope["id"]))
    
    if not scope_data:
        return render_template('error.html', message="Scope not found"), 404
        
    return render_template('view_scope.html', scope=scope_data, scope_id=scope_id)

@app.route('/scope/<scope_id>/edit')
def edit_scope(scope_id):
    """Edit a specific scope."""
    # Try to get the scope directly first
    scope_data = scope_creator.get_saved_scope(scope_id)
    
    # If not found, try to find a match among available scopes
    if not scope_data:
        # Get all scopes and check if any filename contains our scope_id
        all_scopes = scope_creator.list_saved_scopes()
        for scope in all_scopes:
            if scope_id in scope.get("id", ""):
                # Found a potential match, try with this ID instead
                print(f"Original scope_id '{scope_id}' not found, using '{scope['id']}' instead")
                scope_data = scope_creator.get_saved_scope(scope["id"])
                if scope_data:
                    # Redirect to the correct URL with the actual ID
                    return redirect(url_for('edit_scope', scope_id=scope["id"]))
    
    if not scope_data:
        return render_template('error.html', message="Scope not found"), 404
        
    return render_template('edit_scope.html', scope=scope_data, scope_id=scope_id)

@app.route('/scope/<scope_id>/update', methods=['POST'])
def update_scope(scope_id):
    """Update a scope with edited data."""
    try:
        data = request.get_json()
        success = scope_creator.update_saved_scope(scope_id, data)
        
        if not success:
            return jsonify({"error": "Failed to update scope"}), 500
            
        return jsonify({"message": "Scope updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/scope/<scope_id>/history')
def scope_history(scope_id):
    """View the version history of a scope."""
    scope_data = scope_creator.get_saved_scope(scope_id)
    history = scope_creator.get_scope_history(scope_id)
    
    if not scope_data:
        return render_template('error.html', message="Scope not found"), 404
        
    return render_template('scope_history.html', scope=scope_data, scope_id=scope_id, history=history)

@app.route('/scope/<scope_id>/version/<timestamp>')
def view_scope_version(scope_id, timestamp):
    """View a specific version of a scope."""
    scope_data = scope_creator.get_saved_scope(scope_id)
    history = scope_creator.get_scope_history(scope_id)
    
    if not scope_data or not history:
        return render_template('error.html', message="Scope or history not found"), 404
    
    # Find the requested version
    timestamp = float(timestamp)
    version = None
    for v in history:
        if v.get("timestamp") == timestamp:
            version = v
            break
    
    if not version:
        return render_template('error.html', message="Version not found"), 404
        
    return render_template('view_scope_version.html', scope=scope_data, scope_id=scope_id, 
                          version=version, current_timestamp=timestamp)

@app.route('/scope/<scope_id>/restore/<timestamp>', methods=['POST'])
def restore_scope_version(scope_id, timestamp):
    """Restore a scope to a previous version."""
    try:
        timestamp = float(timestamp)
        success = scope_creator.restore_scope_version(scope_id, timestamp)
        
        if not success:
            return jsonify({"error": "Failed to restore version"}), 500
            
        return jsonify({"message": "Version restored successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/ai_chat', methods=['POST'])
def ai_chat():
    try:
        data = request.get_json()
        user_message = data.get('message', '')
        document_content = data.get('document_content', '')
        project_name = data.get('project_name', '')
        scope_id = data.get('scope_id', '')
        
        if not user_message or not document_content:
            return jsonify({"error": "Message and document content are required"}), 400
            
        # Add line numbers to document content for precise referencing
        content_lines = document_content.split('\n')
        numbered_content = ""
        for i, line in enumerate(content_lines, 1):
            numbered_content += f"{i:04d}: {line}\n"
            
        # Prepare the prompt for the AI model
        prompt = f"""You are an AI assistant helping a user edit their document. Your task is to provide suggestions, improvements, or edits based on the user's request.

Document Context (Project: {project_name}):
The document below includes line numbers at the start of each line in the format "NNNN: " where NNNN is the line number.
```
{numbered_content}
```

User Request: {user_message}

When providing edits, follow this format:
1. First, give a helpful explanation of what you're going to do
2. Then, if you want to edit a specific part of the document, output a JSON block enclosed in ```json and ``` tags with:
   - start_line: the first line number to replace (use the exact line number shown at the beginning of the line)
   - end_line: the last line number to replace (use the exact line number shown at the beginning of the line)
   - new_text: the complete text that should replace the content between start_line and end_line (do NOT include line numbers in your new text)

For example:
"I'll help improve the Executive Summary by adding more detail about the project goals.

```json
{{
  "start_line": 5,
  "end_line": 10,
  "new_text": "# Executive Summary\\n\\nThis project aims to develop a comprehensive solution that addresses...\\n\\nThe key objectives include..."
}}
```"

IMPORTANT:
- Be extremely precise with line numbers - use the line numbers shown at the beginning of each line (0001, 0002, etc.)
- Make sure your start_line and end_line values correspond to actual line numbers in the document
- Do not include the line number prefixes in your new_text - just provide the content that should replace the specified lines
- Only use the JSON format when you need to make specific text edits

Only use the JSON format when you need to make specific text edits. For general advice or when answering questions, just provide the explanation without the JSON.
"""
        
        # Call the Deepseek r-1 model through OpenRouter API
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            return jsonify({"error": "OpenRouter API key not found. Please set it in your .env file."}), 500
            
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": request.headers.get('Host', 'localhost')  # Optional
        }
        
        payload = {
            "model": "google/gemini-2.0-pro-exp-02-05:free",
            "messages": [
                {"role": "system", "content": "You are a helpful AI assistant specialized in document editing. You're careful about line numbers and precise editing."},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.5,  # Lower temperature for more precise output
            "max_tokens": 1500
        }
        
        response = requests.post(
            "https://openrouter.ai/api/v1/chat/completions",
            headers=headers,
            json=payload
        )
        
        if response.status_code != 200:
            return jsonify({"error": f"Error from AI service: {response.text}"}), 500

        ai_response = response.json()
        ai_message = ai_response['choices'][0]['message']['content']
        
        # Extract JSON if present
        edit_data = None
        json_match = re.search(r'```json\s*(.*?)\s*```', ai_message, re.DOTALL)
        
        if json_match:
            try:
                json_str = json_match.group(1)
                edit_data = json.loads(json_str)
                
                # Validate line numbers to ensure they are within bounds
                if edit_data.get('start_line') and edit_data.get('end_line'):
                    start_line = int(edit_data['start_line'])
                    end_line = int(edit_data['end_line'])
                    
                    if start_line < 1 or end_line > len(content_lines) or start_line > end_line:
                        print(f"Invalid line range: {start_line}-{end_line}, document has {len(content_lines)} lines")
                        edit_data = None
                        ai_message += "\n\nNote: I suggested an edit with invalid line numbers. Please provide more specific instructions about which section you'd like to edit."
            except json.JSONDecodeError as e:
                print(f"Error parsing JSON: {e}")
                # We'll still return the message even if JSON parsing fails
            except (ValueError, TypeError) as e:
                print(f"Error processing line numbers: {e}")
                edit_data = None
        
        return jsonify({
            "message": ai_message,
            "edit": edit_data
        })
        
    except Exception as e:
        print(f"Error in AI chat: {str(e)}")
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500

if __name__ == '__main__':
    app.run(debug=True, port=5006) 