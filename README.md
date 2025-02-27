# Scope Creator AI 🚀

A powerful AI-powered tool that generates comprehensive project scope documents from meeting transcriptions and project information. Built with Python and Flask, this tool leverages advanced language models to create detailed, well-structured scope documents that capture all critical project aspects.

![Scope Creator Preview](preview.png)

## Features ✨

- **Intelligent Project Analysis**: Automatically analyzes project information and identifies required details
- **Dynamic Question Generation**: Creates targeted questions to gather missing critical information
- **Three-Phase Scope Generation**:
  1. Project Overview & Purpose
  2. Dynamic Technical Sections
  3. Critical Assumptions & Clarifications
- **Smart Content Generation**: Only creates sections where sufficient information exists
- **Comprehensive Documentation**: Generates detailed scope documents with:
  - Project background and context
  - Business value and success criteria
  - Technical requirements and specifications
  - Clear assumptions and potential misunderstandings
- **Professional Formatting**: Consistent markdown formatting with proper section hierarchy

## Installation 🛠️

1. Clone the repository:
```bash
git clone https://github.com/KaiStephens/scopeCreator.git
cd scopeCreator
```

2. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up environment variables:
```bash
cp .env.example .env
```
Edit `.env` and add your OpenRouter API key:
```
OPENROUTER_API_KEY=your_api_key_here
```

## Usage 🎯

1. Start the Flask server:
```bash
python app.py
```

2. Open your browser and navigate to `http://localhost:5000`

3. Enter your project details:
   - Project name
   - Meeting transcription (if available)
   - Answer any generated questions

4. Click "Generate Scope" to create your document

## API Reference 📚

### ScopeCreator Class

The main class that handles scope document generation.

```python
creator = ScopeCreator(model="google/gemini-2.0-pro-exp-02-05:free")
```

#### Methods

- `analyze_project(project_name: str, transcription: Optional[str] = None) -> Dict`
  - Analyzes project information and generates initial questions
  - Returns project type, relevant sections, and required information

- `get_follow_up_questions(project_name: str, current_info: Dict) -> List[Dict]`
  - Generates follow-up questions based on current information
  - Returns a list of questions with justifications

- `generate_scope(project_name: str, project_info: Dict, model: str) -> Dict`
  - Generates the complete scope document in three phases
  - Returns formatted scope document

## Document Structure 📄

Generated scope documents include:

1. **Project Overview** (500+ words)
   - Project Background
   - Context and History
   - Goals and Objectives

2. **Project Purpose** (750+ words)
   - Business Value
   - Project Drivers
   - Success Criteria

3. **Dynamic Technical Sections** (500+ words each)
   - Requirements and Architecture
   - User Interface
   - Security
   - Performance
   - Integration
   - And more based on available information

4. **Critical Assumptions** (500+ words)
   - Technical Assumptions
   - Business Assumptions
   - Resource Assumptions
   - Implementation Assumptions

## Dependencies 📦

- Python 3.8+
- Flask
- OpenAI Python Client
- python-dotenv
- Other dependencies listed in `requirements.txt`

## License 📝

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## Acknowledgments 🙏

- OpenRouter for providing the AI model API
- Flask for the web framework
- All contributors and users of this tool

## Support 💬

For support, please open an issue in the GitHub repository or me at kai@kaios.ca.

---

Made with ❤️ by Kai Stephens