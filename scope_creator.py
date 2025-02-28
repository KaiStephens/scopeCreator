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

            # Phase 1: Initial Overview and Purpose
            initial_prompt = f"""You are a professional scope document creator. Create the initial sections of a comprehensive scope document focusing ONLY on project overview, history, and purpose. Use the following information:

PROJECT DETAILS:
Project Name: {project_name}

Meeting Transcription:
{transcription if transcription else "No transcription provided"}

Questions and Answers:
{json.dumps(cleaned_info, indent=2) if cleaned_info else "No additional information provided"}

CONTEXT AND EXAMPLES:
{context}

REQUIRED SECTIONS:
1. Project Name and Overview (500+ words)
   - Project Background
   - Detailed Context and History
   - In-depth Overview of Goals and Objectives

2. Project Purpose (750+ words)
   - Detailed Business Value and Justification
   - Comprehensive Explanation of Project Drivers
   - Detailed Success Criteria

CRITICAL GUIDELINES:
1. The meeting transcription and answered questions are your PRIMARY sources - use ALL details from them
2. Each section MUST meet the minimum word counts specified
3. Use specific measurements and technical details when available
4. Include direct quotes using > blockquotes
5. Never say "insufficient information" - use what's known or omit the section
6. Use professional, technical language throughout

FORMATTING:
1. Use ## for main section headers
2. Use ### for subsections
3. Use #### for sub-subsections
4. Use bullet points for lists
5. Use > for direct quotes
6. Use bold for emphasis on key points"""

            # Phase 2: Dynamic Middle Sections
            middle_prompt = f"""Based on the available information, generate appropriate technical and functional sections for this scope document. Focus on what is KNOWN and create detailed sections only for aspects that have clear information or requirements.

PROJECT DETAILS:
Project Name: {project_name}

Meeting Transcription:
{transcription if transcription else "No transcription provided"}

Questions and Answers:
{json.dumps(cleaned_info, indent=2) if cleaned_info else "No additional information provided"}

CONTEXT AND EXAMPLES:
{context}

POTENTIAL SECTIONS (Create ONLY those that have sufficient information):
- Technical Requirements and Architecture
- User Interface Requirements
- Security Requirements
- Performance Requirements
- User Management
- Data Management
- Integration Requirements
- Testing Requirements
- User Acceptance Criteria
- Expected Delivery Schedule
- Quality Assurance Plan
- Maintenance and Support
- Training Requirements
- Documentation Requirements

REQUIREMENTS FOR EACH SECTION:
1. Minimum 500 words per section
2. Must include specific technical details and measurements
3. Must break down into clear subsections
4. Must include examples and scenarios
5. Must specify acceptance criteria where applicable

CRITICAL GUIDELINES:
1. Only create sections where you have concrete information
2. Use specific technical details and measurements
3. Include direct quotes from the transcription
4. Break down requirements into clear, testable items
5. Specify exact parameters and configurations

FORMATTING:
Same as previous sections, maintain consistent formatting throughout."""

            # Phase 3: Critical Assumptions
            assumptions_prompt = f"""Create a comprehensive list of critical assumptions for this project. These assumptions should clearly state any potential points of misunderstanding or ambiguity that could affect project success.

PROJECT DETAILS:
Project Name: {project_name}

Meeting Transcription:
{transcription if transcription else "No transcription provided"}

Questions and Answers:
{json.dumps(cleaned_info, indent=2) if cleaned_info else "No additional information provided"}

CONTEXT AND EXAMPLES:
{context}

CRITICAL GUIDELINES:
1. Each assumption must be specific and testable
2. Focus on potential areas of misinterpretation
3. Include technical, business, and resource assumptions
4. Pay special attention to:
   - Technical constraints and compatibility
   - User expectations and requirements
   - Resource availability and limitations
   - Timeline and delivery expectations
   - Integration points and dependencies
   - Design and implementation flexibility
   - Client responsibilities and involvement
   - Testing and acceptance criteria
   - Maintenance and support expectations

FORMAT:
## Critical Assumptions and Clarifications

[List each assumption in clear, unambiguous language. Example format:]

1. [Technical Assumption]: Clear statement about technical constraints or requirements
2. [Business Assumption]: Clear statement about business processes or expectations
3. [Resource Assumption]: Clear statement about resource availability or limitations
4. [Implementation Assumption]: Clear statement about development approach or methodology

Each assumption should be:
- Specific and measurable where possible
- Related to potential points of confusion
- Important for project success
- Written in clear, non-technical language when possible

Minimum 500 words total for this section."""

            # Execute each phase
            messages_initial = [
                {"role": "system", "content": "You are a professional scope writer focusing on project overview and purpose."},
                {"role": "user", "content": initial_prompt}
            ]
            
            messages_middle = [
                {"role": "system", "content": "You are a professional scope writer focusing on technical and functional requirements."},
                {"role": "user", "content": middle_prompt}
            ]
            
            messages_assumptions = [
                {"role": "system", "content": "You are a professional scope writer focusing on critical project assumptions."},
                {"role": "user", "content": assumptions_prompt}
            ]
            
            # Get responses for each phase
            initial_response = self._make_api_call(messages_initial, model=model)
            middle_response = self._make_api_call(messages_middle, model=model)
            assumptions_response = self._make_api_call(messages_assumptions, model=model)
            
            # Combine and format all sections
            combined_scope = f"{initial_response}\n\n{middle_response}\n\n{assumptions_response}"
            formatted_scope = self._clean_and_format_scope(combined_scope)
            
            # Save scope to JSON
            scope_data = {
                "project_name": project_name,
                "project_info": project_info,
                "scope": formatted_scope
            }
            os.makedirs("scopes", exist_ok=True)
            with open(f"scopes/{project_name.replace(' ', '_')}.json", "w") as f:
                json.dump(scope_data, f, indent=4)

            return {"scope": formatted_scope}
            
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
        for line in lines:
            # Ensure proper spacing for headings
            if line.strip().startswith('#'):
                formatted_lines.append('\n' + line.strip())
            else:
                formatted_lines.append(line)
        
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
                        "id": file_path.stem,
                        "project_name": data.get("project_name", "Unknown Project"),
                        "date_created": file_path.stat().st_ctime,
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
        """Update a saved scope with edited data."""
        file_path = Path(f"scopes/{scope_id}.json")
        
        if not file_path.exists():
            return False
            
        try:
            # Read existing data first to preserve structure
            with open(file_path, 'r') as f:
                existing_data = json.load(f)
                
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