import os
from pathlib import Path
from typing import Dict, Optional, List, Tuple
from dotenv import load_dotenv
from openai import OpenAI
import json
import time

# Load environment variables
load_dotenv()

class ScopeCreator:
    def __init__(self, model: str = "google/gemini-2.0-pro-exp-02-05:free"):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise ValueError("OPENROUTER_API_KEY environment variable is not set")
            
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=api_key,
            default_headers={
                "HTTP-Referer": os.getenv("SITE_URL", "http://localhost:5006"),
                "X-Title": os.getenv("SITE_NAME", "Scope Creator AI")
            }
        )
        self.model = model
        self.context = self._load_context()

    def _make_api_call(self, messages, max_retries=3, model=None):
        """Make an API call with retries and proper error handling."""
        for attempt in range(max_retries):
            try:
                completion = self.client.chat.completions.create(
                    model=model or self.model,  # Use provided model or fall back to default
                    messages=messages,
                    temperature=0.7,
                    max_tokens=8000
                )
                if not completion or not completion.choices:
                    raise ValueError("Empty response from API")
                    
                return completion.choices[0].message.content
                
            except Exception as e:
                print(f"Error on attempt {attempt + 1}: {str(e)}")
                if attempt == max_retries - 1:  # Last attempt
                    raise
                time.sleep(1 * (attempt + 1))  # Exponential backoff
                
        raise Exception("Max retries exceeded")

    def _load_context(self) -> str:
        """Load the context file that guides scope creation."""
        try:
            with open('context.txt', 'r') as f:
                return f.read()
        except FileNotFoundError:
            print("Warning: context.txt not found")
            return ""

    def analyze_project(self, project_name: str, transcription: Optional[str] = None) -> Dict:
        """Analyze the project and determine what information is needed."""
        prompt = f"""
        Based on this project name and any provided transcription, analyze what type of project this is
        and what specific information would be needed to create a comprehensive scope document.
        Consider ONLY the information explicitly provided - do not make assumptions.
        
        Project Name: {project_name}

        {"Meeting Transcription:\n" + transcription if transcription else ""}

        Context for good scope creation:
        {self.context}

        Important Guidelines:
        1. Only ask questions about information that is ABSOLUTELY NECESSARY for the scope
        2. Try to make the questions as user-friendly as possible (e.g. "What is the name of the project?" instead of "Who will be working on the project?")
        3. Do not make assumptions about the project or ask questions based on assumptions
        4. Do not ask about information that wasn't mentioned in the provided content
        5. Focus only on core project requirements and critical information
        6. If information is already provided, do not ask about it again

        Return a JSON object with:
        1. A brief analysis of the project type (based ONLY on provided information)
        2. A list of sections that would be relevant for this specific project
        3. Initial questions for ONLY the most critical missing information

        Format the response as:
        {{
            "project_type": "Brief description using ONLY provided information",
            "relevant_sections": ["Section 1", "Section 2", ...],
            "initial_questions": [
                {{
                    "question": "Question about CRITICAL missing information only",
                    "why_needed": "Why this information is ABSOLUTELY NECESSARY for the scope",
                    "section": "Which section this information belongs to"
                }}
            ]
        }}

        Important: Return ONLY the JSON object, no markdown code blocks or additional text.
        """

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a professional scope writer. Be conservative in your analysis and only ask for information that is absolutely necessary. Do not make assumptions or ask speculative questions. Return ONLY the JSON object without any markdown formatting or additional text."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            content = self._make_api_call(messages)
            print(f"Raw AI response:\n{content}")  # Debug print
            
            # Clean up the response if it contains markdown code blocks
            cleaned_content = content.strip()
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            try:
                # Try to parse the JSON
                parsed_json = json.loads(cleaned_content)
                return parsed_json
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw response for debugging
                return {
                    "raw_response": content
                }
            
        except Exception as e:
            print(f"Error analyzing project: {str(e)}")
            raise

    def get_follow_up_questions(self, project_name: str, current_info: Dict) -> List[Dict]:
        """Determine what additional information is needed based on current responses."""
        prompt = f"""
        Based ONLY on the information provided so far, determine if any CRITICAL information is still missing
        to create a comprehensive scope document for this specific project.

        Project Name: {project_name}

        Current Information:
        {json.dumps(current_info, indent=2)}

        Context for good scope creation:
        {self.context}

        Important Guidelines:
        1. Only ask follow-up questions if information is ABSOLUTELY NECESSARY for the scope
        2. Do not make assumptions about the project or ask questions based on assumptions
        3. Do not ask about information that wasn't mentioned in previous responses
        4. If the provided information is sufficient, return an empty array
        5. Do not ask speculative questions or questions about potential features/requirements
        6. Only ask about concrete, essential information that is missing

        Return ONLY a JSON array of critical follow-up questions, or an empty array if no more information is needed.
        Do not include any markdown formatting or additional text.

        Format:
        [
            {{
                "question": "Question about CRITICAL missing information only",
                "why_needed": "Why this information is ABSOLUTELY NECESSARY for the scope",
                "section": "Which section this information belongs to",
                "based_on": "What specific information from previous responses triggered this follow-up"
            }}
        ]

        If you have enough information to generate the scope, or if no CRITICAL information is missing, return an empty array: []
        """

        try:
            messages = [
                {
                    "role": "system",
                    "content": "You are a professional scope writer. Be conservative and only ask for information that is absolutely necessary. Do not make assumptions or ask speculative questions. Return ONLY the JSON array without any markdown formatting or additional text. Return an empty array [] if no critical information is missing."
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ]
            
            try:
                content = self._make_api_call(messages)
                print(f"Raw follow-up response:\n{content}")  # Debug print
            except ValueError as e:
                if "Empty response from API" in str(e):
                    # If we get an empty response, assume no more questions are needed
                    print("Empty API response - interpreting as no more questions needed")
                    return []
                raise
            
            # Clean up the response if it contains markdown code blocks
            cleaned_content = content.strip()
            if cleaned_content.startswith('```json'):
                cleaned_content = cleaned_content[7:]
            elif cleaned_content.startswith('```'):
                cleaned_content = cleaned_content[3:]
            if cleaned_content.endswith('```'):
                cleaned_content = cleaned_content[:-3]
            cleaned_content = cleaned_content.strip()
            
            # If we get an empty string or just whitespace, return empty array
            if not cleaned_content:
                print("Empty content - interpreting as no more questions needed")
                return []
            
            try:
                # Try to parse the JSON
                parsed_json = json.loads(cleaned_content)
                return parsed_json
            except json.JSONDecodeError:
                # If JSON parsing fails, return the raw response for debugging
                return [{
                    "question": "Error parsing AI response",
                    "why_needed": "Debug information",
                    "section": "Debug",
                    "based_on": "Raw response: " + content
                }]
            
        except Exception as e:
            print(f"Error getting follow-up questions: {str(e)}")
            raise

    def generate_scope(self, project_name: str, project_info: Dict, model: str) -> Dict:
        try:
            # Get the transcription and other info
            transcription = project_info.get('transcription', '')
            initial_questions = project_info.get('initial_questions', [])
            context = self._load_context()

            # Clean up project info
            cleaned_info = {}
            question_mapping = {str(i): q.get('question', '') for i, q in enumerate(initial_questions)}
            for key, value in project_info.items():
                if key.isdigit() and value.strip() and key in question_mapping:
                    cleaned_info[question_mapping[key]] = value

            # Single comprehensive prompt for a consistent, structured scope document
            scope_prompt = f"""You are a professional scope document creator. Create a comprehensive, DETAILED scope document (minimum 2000 words) following a specific structure with the following information:

PROJECT DETAILS:
Project Name: {project_name}

Meeting Transcription:
{transcription if transcription else "No transcription provided"}

Questions and Answers:
{json.dumps(cleaned_info, indent=2) if cleaned_info else "No additional information provided"}

CONTEXT AND EXAMPLES:
{context}

REQUIRED STRUCTURE:
The scope document MUST follow this exact structure:

1. Project Name and Header
   - Include project name at the top
   - Current date (month and year)
   - Optional revision history if applicable

2. Project Purpose (200-300 words)
   - Clear statement of what this project aims to accomplish
   - Business justification and value
   - Specific goals and objectives
   - Success criteria where applicable

3. Requirements (1500+ words)
   - Break down into logical categories based on the project type
   - Each requirement MUST be extremely detailed, clear, specific, and measurable
   - Include specific technical details, measurements, and parameters where available
   - Group related requirements together under appropriate subheadings
   - Each category should have at least 3-5 specific requirements
   - Use numbered lists for individual requirements
   - Include multiple levels of hierarchy (sections, subsections, sub-subsections)

4. Assumptions (300+ words)
   - List at least 5-7 specific, project-relevant assumptions (numbered list)
   - Base assumptions on the actual project details, NOT generic statements
   - Focus on technical constraints, design limitations, and project-specific factors
   - Include assumptions about tools, technologies, and implementation details
   - Avoid generic assumptions like "client will provide requirements in a timely manner"
   - Model your assumptions after the example provided, which are specific and technical

DO NOT INCLUDE these sections (they are boilerplate that will be added separately):
- User acceptance criteria
- Expected delivery schedule
- Project driving factors
- Project constraints

CRITICAL GUIDELINES:
1. The scope document MUST be extremely detailed (minimum 2000 words total)
2. The meeting transcription and answered questions are your PRIMARY sources - use ALL details from them
3. Be extremely specific and detailed - include exact measurements, parameters, and technical specifications
4. Never say "insufficient information" - use what's known or make reasonable project-specific assumptions
5. Format requirements in a hierarchical manner with detailed numbering and clear organization
6. Focus on creating specific, implementable requirements that could be directly acted upon
7. Requirements should be specific, measurable, achievable, relevant, and time-bound (SMART)
8. Use detailed examples, scenarios, and use cases where appropriate
9. When describing features or functionality, explain HOW they should work in detail

QUALITY CHECKS:
1. Is each section sufficiently detailed (especially Requirements at 1500+ words)?
2. Are the assumptions specific to this project (not generic statements)?
3. Are requirements organized hierarchically with proper numbering?
4. Is the total document around 2000 words or more?
5. Does each requirement include specific technical details when applicable?

FORMATTING:
1. Use Markdown formatting
2. Use ## for main section headers
3. Use ### for subsections
4. Use #### for sub-subsections
5. Use numbered lists for individual requirements (1., 2., 3., etc.)
6. Use bullet points for descriptive lists
7. Use bold for emphasis on key points

EXAMPLE FORMAT:
Follow the structure and level of detail shown in the examples provided in the context. The requirements should be highly detailed with multiple subsections like the game screen requirements example, and assumptions should be specific and technical like in the example.
"""

            # Execute the scope creation
            messages = [
                {"role": "system", "content": "You are a professional scope writer who creates detailed, structured scope documents."},
                {"role": "user", "content": scope_prompt}
            ]
            
            # Get response
            scope_response = self._make_api_call(messages, model=model)
            
            # Format the scope
            formatted_scope = self._clean_and_format_scope(scope_response)
            
            # Generate a unique scope ID based on name and timestamp
            timestamp = time.time()
            formatted_time = time.strftime("%Y%m%d%H%M%S", time.localtime(timestamp))
            scope_id = f"{project_name.replace(' ', '_').lower()}_{formatted_time}"
            
            # Save scope to JSON with version history
            scope_data = {
                "id": scope_id,
                "project_name": project_name,
                "project_info": project_info,
                "scope": formatted_scope,
                "date_created": timestamp,
                "formatted_date": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(timestamp)),
                "version_history": []  # Initialize empty version history
            }
            
            # Ensure the scopes directory exists
            os.makedirs("scopes", exist_ok=True)
            
            # Save the scope as a JSON file
            file_path = os.path.join("scopes", f"{scope_id}.json")
            with open(file_path, "w") as f:
                json.dump(scope_data, f, indent=4)
                
            return {"scope": formatted_scope, "id": scope_id}
            
        except Exception as e:
            print(f"Error generating scope: {str(e)}")
            return {"error": "Failed to generate scope document"}

    def get_ai_response(self, prompt, model):
        # Implement AI model interaction here
        pass

    def _clean_and_format_scope(self, scope):
        """Clean and format the scope document for better presentation"""
        # Remove any potential system messages or prefixes
        if "```markdown" in scope:
            scope = scope.split("```markdown")[1].split("```")[0]
        elif "```" in scope:
            scope = scope.split("```")[1].split("```")[0]
        
        # Ensure consistent heading formatting
        lines = scope.split('\n')
        formatted_lines = []
        in_requirements = False
        in_assumptions = False
        
        for line in lines:
            # Ensure proper spacing for headings
            if line.strip().startswith('#'):
                # Add extra line break before main sections
                if line.strip().startswith('## '):
                    formatted_lines.append('\n' + line.strip())
                    
                    # Track when we enter important sections
                    if 'Requirements' in line:
                        in_requirements = True
                        in_assumptions = False
                    elif 'Assumptions' in line:
                        in_requirements = False
                        in_assumptions = True
                    else:
                        in_requirements = False
                        in_assumptions = False
                else:
                    formatted_lines.append('\n' + line.strip())
            
            # Ensure proper formatting for numbered lists
            elif in_requirements and (line.strip().startswith('1.') or line.strip().startswith('2.') or 
                                     line.strip().startswith('3.') or line.strip().startswith('4.') or 
                                     line.strip().startswith('5.')):
                # Ensure proper spacing for requirement lists
                if formatted_lines and formatted_lines[-1].strip() != '':
                    formatted_lines.append('')  # Add blank line before list starts
                formatted_lines.append(line)
            
            # Ensure proper formatting for assumptions
            elif in_assumptions and (line.strip().startswith('1.') or line.strip().startswith('2.') or 
                                     line.strip().startswith('3.') or line.strip().startswith('4.') or 
                                     line.strip().startswith('5.')):
                # Ensure proper spacing for assumptions list
                if formatted_lines and formatted_lines[-1].strip() != '':
                    formatted_lines.append('')  # Add blank line before list starts
                formatted_lines.append(line)
            else:
                formatted_lines.append(line)
        
        # Add word count as a comment at the bottom
        total_words = len(' '.join(formatted_lines).split())
        formatted_lines.append(f"\n\n<!-- Total word count: {total_words} words -->")
        
        return '\n'.join(formatted_lines).strip()
        
    def list_saved_scopes(self) -> List[Dict]:
        """List all saved scopes with basic information."""
        scopes = []
        scopes_dir = Path("scopes")
        
        if not scopes_dir.exists():
            return []
            
        for file_path in scopes_dir.glob("*.json"):
            try:
                with open(file_path, 'r') as f:
                    data = json.load(f)
                    # Extract just the data we need for listing
                    scopes.append({
                        "id": data.get("id", "Unknown Scope"),
                        "project_name": data.get("project_name", "Unknown Project"),
                        "date_created": data.get("date_created", 0),
                        "formatted_date": data.get("formatted_date", "Unknown Date"),
                        "file_name": file_path.name
                    })
            except Exception as e:
                print(f"Error reading scope file {file_path}: {str(e)}")
                
        # Sort by date created (newest first)
        scopes.sort(key=lambda x: x["date_created"], reverse=True)
        return scopes
        
    def get_saved_scope(self, scope_id: str) -> Optional[Dict]:
        """Get a specific saved scope by ID."""
        file_path = Path(f"scopes/{scope_id}.json")
        
        if not file_path.exists():
            return None
            
        try:
            with open(file_path, 'r') as f:
                return json.load(f)
        except Exception as e:
            print(f"Error reading scope file {file_path}: {str(e)}")
            return None
            
    def update_saved_scope(self, scope_id: str, updated_data: Dict) -> bool:
        """Update a saved scope with edited data and maintain version history."""
        file_path = Path(f"scopes/{scope_id}.json")
        
        if not file_path.exists():
            return False
            
        try:
            # Read existing data first to preserve structure
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
                
            # Create version history array if it doesn't exist
            if "version_history" not in existing_data:
                existing_data["version_history"] = []
                
            # Add current version to history before updating
            current_timestamp = time.time()
            current_version = {
                "timestamp": current_timestamp,
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_timestamp)),
                "project_name": existing_data.get("project_name", ""),
                "scope": existing_data.get("scope", "")
            }
            
            # Only add to history if content actually changed
            latest_scope = existing_data.get("scope", "")
            new_scope = updated_data.get("scope", "")
            if latest_scope != new_scope or existing_data.get("project_name", "") != updated_data.get("project_name", ""):
                existing_data["version_history"].append(current_version)
            
            # Update with new data
            if "project_name" in updated_data:
                existing_data["project_name"] = updated_data["project_name"]
            if "project_info" in updated_data:
                existing_data["project_info"] = updated_data["project_info"]
            if "scope" in updated_data:
                existing_data["scope"] = updated_data["scope"]
                
            # Write the updated data back
            with open(file_path, 'w') as f:
                json.dump(existing_data, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error updating scope file {file_path}: {str(e)}")
            return False
            
    def get_scope_history(self, scope_id: str) -> List[Dict]:
        """Get the version history of a scope."""
        file_path = Path(f"scopes/{scope_id}.json")
        
        if not file_path.exists():
            return []
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            return data.get("version_history", [])
        except Exception as e:
            print(f"Error reading scope history {file_path}: {str(e)}")
            return []
            
    def restore_scope_version(self, scope_id: str, version_timestamp: float) -> bool:
        """Restore a scope to a previous version from history."""
        file_path = Path(f"scopes/{scope_id}.json")
        
        if not file_path.exists():
            return False
            
        try:
            with open(file_path, 'r') as f:
                data = json.load(f)
                
            history = data.get("version_history", [])
            
            # Find the version with the matching timestamp
            version_to_restore = None
            for version in history:
                if version.get("timestamp") == version_timestamp:
                    version_to_restore = version
                    break
                    
            if not version_to_restore:
                return False
                
            # Create a new history entry for the current version before restoring
            current_timestamp = time.time()
            current_version = {
                "timestamp": current_timestamp,
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(current_timestamp)),
                "project_name": data.get("project_name", ""),
                "scope": data.get("scope", ""),
                "is_restore_point": True,
                "restored_from": version_timestamp
            }
            
            # Add current version to history
            history.append(current_version)
            
            # Restore the old version data
            data["project_name"] = version_to_restore.get("project_name", data.get("project_name", ""))
            data["scope"] = version_to_restore.get("scope", data.get("scope", ""))
            
            # Add restoration note
            restore_note = {
                "timestamp": time.time(),
                "formatted_time": time.strftime("%Y-%m-%d %H:%M:%S"),
                "message": f"Restored to version from {version_to_restore.get('formatted_time')}"
            }
            
            if "restoration_notes" not in data:
                data["restoration_notes"] = []
                
            data["restoration_notes"].append(restore_note)
            
            # Write the updated data back
            with open(file_path, 'w') as f:
                json.dump(data, f, indent=4)
                
            return True
        except Exception as e:
            print(f"Error restoring scope version {file_path}: {str(e)}")
            return False
