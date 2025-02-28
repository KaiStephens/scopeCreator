from flask import Flask, request, jsonify, render_template
from scope_creator import ScopeCreator
import json
import os
import datetime

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
        scope = scope_creator.generate_scope(project_name, project_info, model)
        
        return jsonify(scope)

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
    scope_data = scope_creator.get_saved_scope(scope_id)
    
    if not scope_data:
        return render_template('error.html', message="Scope not found"), 404
        
    return render_template('view_scope.html', scope=scope_data, scope_id=scope_id)

@app.route('/scope/<scope_id>/edit')
def edit_scope(scope_id):
    """Edit a specific scope."""
    scope_data = scope_creator.get_saved_scope(scope_id)
    
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

if __name__ == '__main__':
    app.run(debug=True, port=5006) 