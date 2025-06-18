"""
LLM Processor module for processing documents using LLaMA2-7B with Ollama.
"""
import os
import sys
import logging
import json
import re
import requests
from typing import Dict, List, Any, Optional
from datetime import datetime

# Add parent directory to path to import config
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from llm_service.config import (
    OLLAMA_API_BASE, OLLAMA_MODEL, OLLAMA_TIMEOUT,
    MAX_TOKENS, TEMPERATURE, TOP_P, TOP_K, SYSTEM_PROMPT
)

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

class LLMProcessor:
    """Class for processing documents with LLaMA2-7B using Ollama."""

    def __init__(self):
        """Initialize LLM processor with Ollama."""
        logger.info("Initializing LLM Processor with Ollama (LLaMA2-7B)...")
        
        try:
            # Check if Ollama is running
            self._check_ollama_status()

            self.api_base = OLLAMA_API_BASE
            self.model = OLLAMA_MODEL
            self.max_tokens = MAX_TOKENS
            self.temperature = TEMPERATURE
            self.top_p = TOP_P
            self.top_k = TOP_K
            self.timeout = OLLAMA_TIMEOUT
            logger.info(f"LLM Processor initialized successfully with model: {self.model}")
        except Exception as e:
            logger.error(f"Error initializing LLM Processor: {str(e)}")
            raise

    def _check_ollama_status(self):
        """
        Check if Ollama is running.
        Raises:
            Exception: If Ollama is not running
        """
        try:
            response = requests.get(f"{OLLAMA_API_BASE}/api/tags", timeout=5)
            if response.status_code != 200:
                raise Exception(f"Ollama returned status code {response.status_code}")
            models = response.json().get("models", [])
            model_names = [model.get("name") for model in models]
            if OLLAMA_MODEL not in model_names:
                logger.warning(f"Model {OLLAMA_MODEL} not found in Ollama. Available models: {model_names}")
                logger.warning(f"You may need to pull the model using: ollama pull {OLLAMA_MODEL}")
            logger.info(f"Ollama is running. Available models: {model_names}")
        except requests.exceptions.RequestException as e:
            raise Exception(f"Could not connect to Ollama at {OLLAMA_API_BASE}: {str(e)}")

    def _format_prompt(self, instruction: str, input_text: Optional[str] = None) -> str:
        """Format prompt for LLaMA2-7B."""
        if input_text:
            prompt = f"<s>[INST] <<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n{instruction}\n\n{input_text} [/INST]"
        else:
            prompt = f"<s>[INST] <<SYS>>\n{SYSTEM_PROMPT}\n<</SYS>>\n\n{instruction} [/INST]"
        return prompt

    def _process_with_llm(self, prompt_instruction: str, max_tokens_override: Optional[int] = None) -> str:
        """Process text with LLaMA2-7B using Ollama."""
        try:
            final_formatted_prompt = self._format_prompt(instruction=prompt_instruction)
            max_new_tokens = max_tokens_override if max_tokens_override else self.max_tokens
            
            payload = {
                "model": self.model,
                "prompt": final_formatted_prompt,
                "stream": False,
                "options": {
                    "num_predict": max_new_tokens,
                    "temperature": self.temperature,
                    "top_p": self.top_p,
                    "top_k": self.top_k
                }
            }
            
            logger.info(f"Generating text with max_tokens={max_new_tokens}. Prompt (first 200 chars): {prompt_instruction[:200]}...")
            response = requests.post(
                f"{self.api_base}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            if response.status_code != 200:
                logger.error(f"Ollama API error: {response.status_code} - {response.text}")
                return json.dumps({"error": f"Ollama API returned status code {response.status_code}"})
            
            result = response.json()
            generated_text = result.get("response", "").strip()
            logger.debug(f"LLM Raw Output: {generated_text}")
            return generated_text
            
        except requests.exceptions.Timeout:
            logger.error(f"Timeout error when calling Ollama API (timeout={self.timeout}s)")
            return json.dumps({"error": "Request to Ollama API timed out"})
        except requests.exceptions.RequestException as e:
            logger.error(f"Request error when calling Ollama API: {str(e)}")
            return json.dumps({"error": f"Ollama API request error: {str(e)}"})
        except Exception as e:
            logger.error(f"Error processing with LLM: {str(e)}")
            return json.dumps({"error": f"LLM processing error: {str(e)}"})

    def _parse_llm_json_output(self, json_str: str, fields: List[str]) -> Dict[str, Any]:
        """Safely parse JSON string from LLM output and extract specified fields."""
        logger.debug(f"Attempting to parse LLM output (first 1000 chars): {json_str[:1000]}")

        match = re.search(r"\{([\"\w\s\S]*?)\}", json_str, re.DOTALL)
        if match:
            json_str_cleaned = match.group(0)
        else:
            temp_str = json_str.strip()
            if temp_str.startswith("```json"):
                temp_str = temp_str[7:]
            if temp_str.endswith("```"):
                temp_str = temp_str[:-3]
            json_str_cleaned = temp_str.strip()
            
            if not (json_str_cleaned.startswith("{") and json_str_cleaned.endswith("}")):
                logger.warning(f"LLM output does not appear to be a JSON object: {json_str_cleaned[:200]}")
                try:
                    error_data = json.loads(json_str_cleaned) 
                    if isinstance(error_data, dict) and "error" in error_data:
                        return {field: error_data.get(field) if field == "error" else None for field in fields}
                except json.JSONDecodeError:
                    pass 
                return {field: None for field in fields} 

        try:
            data = json.loads(json_str_cleaned)
            if not isinstance(data, dict):
                 logger.warning(f"Parsed JSON is not a dictionary: {data}")
                 return {field: None for field in fields}
            return {field: data.get(field) for field in fields}
        except json.JSONDecodeError as e1:
            logger.warning(f"Initial JSON parsing failed for: '{json_str_cleaned[:500]}...'. Error: {e1}")
            json_str_fixed_trailing_comma = re.sub(r",\s*([\}\]])", r"\1", json_str_cleaned)
            try:
                data = json.loads(json_str_fixed_trailing_comma)
                logger.info("Successfully parsed JSON after attempting to fix trailing commas.")
                if not isinstance(data, dict):
                    logger.warning(f"Parsed JSON (after fix) is not a dictionary: {data}")
                    return {field: None for field in fields}
                return {field: data.get(field) for field in fields}
            except json.JSONDecodeError as e2:
                logger.error(f"JSON parsing failed conclusively for: '{json_str_fixed_trailing_comma[:500]}...'. Error: {e2}. Returning None for fields.")
                try:
                    error_data = json.loads(json_str)
                    if isinstance(error_data, dict) and "error" in error_data:
                        return {field: error_data.get(field) if field == "error" else None for field in fields}
                except json.JSONDecodeError:
                    pass 
                return {field: None for field in fields}
        except Exception as e:
            logger.error(f"Unexpected error during JSON parsing: {e}. Output: {json_str_cleaned[:500]}...")
            return {field: None for field in fields}

    def process_application(self, application_id: int, categorized_docs: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Process application documents and extract information."""
        logger.info(f"Processing application {application_id}")
        result = {
            "student_info": {"name": "", "gender": "", "date_of_birth": "", "age": 0, "nationality": "", "previous_university": "", "gpa": 0.0, "russian_language_level": ""},
            "summaries": {"cv_summary": "", "motivation_letter_summary": "", "recommendation_letter_summary": "", "recommendation_author": "", "achievements_summary": "", "additional_documents_summary": ""},
            "evaluation": {"score": 0, "comments": ""}
        }
        json_instruction = "Format your response STRICTLY as a JSON object. Ensure all string values are properly escaped for JSON (e.g., use \\\" for quotes, \\n for newlines). Return ONLY the JSON object without any text before or after it."
        string_value_instruction = "The value for this field MUST be a single flat string, not a nested JSON object or dictionary."

        # Passport
        if "passport" in categorized_docs and categorized_docs["passport"]:
            passport_text = categorized_docs["passport"][0]["content"]
            if passport_text:
                prompt = f"""Extract information from the passport. {json_instruction}
                Fields: "name" (string), "gender" (string), "date_of_birth" (string, YYYY-MM-DD), "nationality" (string).
                Calculate age as current year minus birth year. If content is empty or data not found, use appropriate null/empty string values within the JSON.
                Example: {{"name": "John Doe", "gender": "Male", "date_of_birth": "1990-01-01", "nationality": "USA"}}
                Passport content: {passport_text}
                Return only the JSON object without any additional text or explanations.
                If any field is missing, still include it as null."""
                passport_info_json_str = self._process_with_llm(prompt)
                self._update_student_info(result, passport_info_json_str)
            else: logger.info("No passport data provided.")

        # CV
        if "cv" in categorized_docs and categorized_docs["cv"]:
            cv_text = categorized_docs["cv"][0]["content"]
            if cv_text:
                prompt = f"""Summarize the CV, focusing on software skills, programming languages, and projects. {json_instruction}
                Field: "cv_summary" (string, max 200 words). {string_value_instruction} If content empty, return {{"cv_summary": "No CV data provided"}}.
                Example: {{"cv_summary": "Proficient in Python and ROS. Developed a robotic arm controlled by a web application and a mobile app for remote control using ROS. Specializes in robotics and AI."}}
                CV content: {cv_text}"""
                cv_summary_json_str = self._process_with_llm(prompt)
                self._update_cv_info(result, cv_summary_json_str)
            else: logger.info("No CV data provided."); result["summaries"]["cv_summary"] = "No CV data provided"

        # Degree (GPA)
        if "degree" in categorized_docs and categorized_docs["degree"]:
            degree_text = categorized_docs["degree"][0]["content"]
            if degree_text:
                prompt = f"""Extract university name and calculate GPA from the degree certificate. {json_instruction}
                To calculate GPA: Count "Отлично" (5), "Хорошо" (4), "Удовлетворительно" (3). Ignore "зачтено".
                Formula: GPA = (3 * number of "Удовлетворительно" + 4 * number of "Xорошо" + 5 * number of "Отлично") / (number of "Удовлетворительно" + number of "Xорошо" + number of "Отлично"). 
                If no such grades, GPA is 0.0. Round GPA to 2 decimal places.
                Fields: "university_name" (string, or "Unknown"), "gpa" (float).
                Example: {{"university_name": "Moscow State University", "gpa": 4.53}}
                Degree content: {degree_text}
                Return only the JSON object without any additional text or explanations.
                If any field is missing, still include it as null."""
                degree_info_json_str = self._process_with_llm(prompt)
                self._update_education_info(result, degree_info_json_str)
            else: logger.info("No degree data provided.")

        # Motivation Letter
        if "motivation_letter" in categorized_docs and categorized_docs["motivation_letter"]:
            motivation_text = categorized_docs["motivation_letter"][0]["content"]
            if motivation_text:
                prompt = f"""Summarize the motivation letter: purpose for master's study, future plans. {json_instruction}
                Field: "motivation_letter_summary" (string, max 200 words). {string_value_instruction} If empty, return {{"motivation_letter_summary": "No motivation letter data provided"}}.
                Example: {{"motivation_letter_summary": "Aims to specialize in AI..."}}
                Motivation letter content: {motivation_text}"""
                motivation_summary_json_str = self._process_with_llm(prompt)
                self._update_motivation_info(result, motivation_summary_json_str)
            else: logger.info("No motivation letter."); result["summaries"]["motivation_letter_summary"] = "No motivation letter data provided"

        # Recommendation Letter
        if "recommendation_letter" in categorized_docs and categorized_docs["recommendation_letter"]:
            recommendation_text = categorized_docs["recommendation_letter"][0]["content"]
            if recommendation_text:
                prompt = f"""Summarize recommendation letter and identify author. {json_instruction}
                Fields: "recommendation_letter_summary" (string, max 200 words), "recommendation_author" (string).
                {string_value_instruction} for recommendation_letter_summary. If empty, return {{"recommendation_letter_summary": "No recommendation letter data provided", "recommendation_author": ""}}.
                Example: {{"recommendation_letter_summary": "Highly recommended...", "recommendation_author": "Prof. Smith"}}
                Recommendation letter content: {recommendation_text}"""
                recommendation_info_json_str = self._process_with_llm(prompt)
                self._update_recommendation_info(result, recommendation_info_json_str)
            else: logger.info("No recommendation letter."); result["summaries"]["recommendation_letter_summary"] = "No recommendation letter data provided"

        # Language Certificate
        if "language_certificate" in categorized_docs and categorized_docs["language_certificate"]:
            language_text = categorized_docs["language_certificate"][0]["content"]
            if language_text:
                prompt = f"""Extract Russian language proficiency level (e.g., A1-C2). {json_instruction}
                Field: "russian_language_level" (string). {string_value_instruction} If empty, return {{"russian_language_level": "No language certificate data provided"}}.
                Example: {{"russian_language_level": "B2"}}
                Certificate content: {language_text}"""
                language_info_json_str = self._process_with_llm(prompt)
                self._update_language_info(result, language_info_json_str)
            else: logger.info("No language certificate."); result["student_info"]["russian_language_level"] = "No language certificate data provided"

        # Achievements
        if "achievements" in categorized_docs and categorized_docs["achievements"]:
            achievements_text = categorized_docs["achievements"][0]["content"]
            if achievements_text:
                prompt = f"""List and summarize personal achievements and awards. {json_instruction}
                Field: "achievements_summary" (string). {string_value_instruction} If empty, return {{"achievements_summary": "No achievements data provided"}}.
                Example: {{"achievements_summary": "Won hackathon. Published paper."}}
                Achievements document content: {achievements_text}"""
                achievements_info_json_str = self._process_with_llm(prompt)
                self._update_achievements_info(result, achievements_info_json_str)
            else: logger.info("No achievements data."); result["summaries"]["achievements_summary"] = "No achievements data provided"

        # Additional Documents
        if "additional_documents" in categorized_docs and categorized_docs["additional_documents"]:
            additional_text = categorized_docs["additional_documents"][0]["content"]
            if additional_text:
                prompt = f"""Briefly summarize additional documents/certificates. {json_instruction}
                Field: "additional_documents_summary" (string). {string_value_instruction} If empty, return {{"additional_documents_summary": "No additional documents data provided"}}.
                Example: {{"additional_documents_summary": "IELTS score 7.0. Coursera certificate in ML."}}
                Additional documents content: {additional_text}"""
                additional_info_json_str = self._process_with_llm(prompt)
                self._update_additional_docs_info(result, additional_info_json_str)
            else: logger.info("No additional documents."); result["summaries"]["additional_documents_summary"] = "No additional documents data provided"

        # Evaluation
        evaluation_prompt_instruction = self._create_evaluation_prompt_instruction(result, json_instruction)
        evaluation_result_json_str = self._process_with_llm(evaluation_prompt_instruction)
        self._update_evaluation(result, evaluation_result_json_str)
        
        return result

    def _update_student_info(self, result: Dict[str, Any], passport_info_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(passport_info_json_str, ["name", "gender", "date_of_birth", "nationality"])
        if parsed_info.get("name"): result["student_info"]["name"] = parsed_info["name"]
        if parsed_info.get("gender"): result["student_info"]["gender"] = parsed_info["gender"]
        if parsed_info.get("date_of_birth"): 
            result["student_info"]["date_of_birth"] = parsed_info["date_of_birth"]
            try:
                birth_year = datetime.strptime(str(parsed_info["date_of_birth"]), "%Y-%m-%d").year
                current_year = datetime.now().year
                result["student_info"]["age"] = current_year - birth_year
            except (ValueError, TypeError):
                date_of_birth_val = parsed_info.get('date_of_birth', 'N/A')
                logger.warning(f"Could not parse date_of_birth: {date_of_birth_val}")
        if parsed_info.get("nationality"): result["student_info"]["nationality"] = parsed_info["nationality"]

    def _update_cv_info(self, result: Dict[str, Any], cv_summary_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(cv_summary_json_str, ["cv_summary"])
        summary_data = parsed_info.get("cv_summary")
        if summary_data:
            if isinstance(summary_data, dict):
                logger.warning(f"CV summary was a dict, converting to JSON string: {summary_data}")
                result["summaries"]["cv_summary"] = json.dumps(summary_data, ensure_ascii=False)
            elif isinstance(summary_data, str):
                result["summaries"]["cv_summary"] = summary_data
            else:
                result["summaries"]["cv_summary"] = str(summary_data)
        else:
            result["summaries"]["cv_summary"] = "" 

    def _update_education_info(self, result: Dict[str, Any], degree_info_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(degree_info_json_str, ["university_name", "gpa"])
        if parsed_info.get("university_name"): result["student_info"]["previous_university"] = parsed_info["university_name"]
        else: result["student_info"]["previous_university"] = "Unknown"
        if parsed_info.get("gpa") is not None:
            try:
                result["student_info"]["gpa"] = float(parsed_info["gpa"])
            except (ValueError, TypeError):
                gpa_val = parsed_info.get('gpa', 'N/A')
                logger.warning(f"Could not parse GPA: {gpa_val}. Setting to 0.0")
                result["student_info"]["gpa"] = 0.0
        else: result["student_info"]["gpa"] = 0.0

    def _update_motivation_info(self, result: Dict[str, Any], motivation_summary_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(motivation_summary_json_str, ["motivation_letter_summary"])
        summary_data = parsed_info.get("motivation_letter_summary")
        if summary_data:
            if isinstance(summary_data, dict):
                logger.warning(f"Motivation letter summary was a dict, converting to JSON string: {summary_data}")
                result["summaries"]["motivation_letter_summary"] = json.dumps(summary_data, ensure_ascii=False)
            elif isinstance(summary_data, str):
                result["summaries"]["motivation_letter_summary"] = summary_data
            else:
                result["summaries"]["motivation_letter_summary"] = str(summary_data)
        else:
            result["summaries"]["motivation_letter_summary"] = ""

    def _update_recommendation_info(self, result: Dict[str, Any], recommendation_info_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(recommendation_info_json_str, ["recommendation_letter_summary", "recommendation_author"])
        summary_data = parsed_info.get("recommendation_letter_summary")
        if summary_data:
            if isinstance(summary_data, dict):
                logger.warning(f"Recommendation letter summary was a dict, converting to JSON string: {summary_data}")
                result["summaries"]["recommendation_letter_summary"] = json.dumps(summary_data, ensure_ascii=False)
            elif isinstance(summary_data, str):
                result["summaries"]["recommendation_letter_summary"] = summary_data
            else:
                result["summaries"]["recommendation_letter_summary"] = str(summary_data)
        else:
            result["summaries"]["recommendation_letter_summary"] = ""
        if parsed_info.get("recommendation_author"): result["summaries"]["recommendation_author"] = parsed_info["recommendation_author"]

    def _update_language_info(self, result: Dict[str, Any], language_info_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(language_info_json_str, ["russian_language_level"])
        summary_data = parsed_info.get("russian_language_level")
        if summary_data:
            if isinstance(summary_data, dict):
                logger.warning(f"Russian language level was a dict, converting to JSON string: {summary_data}")
                result["student_info"]["russian_language_level"] = json.dumps(summary_data, ensure_ascii=False)
            elif isinstance(summary_data, str):
                result["student_info"]["russian_language_level"] = summary_data
            else:
                result["student_info"]["russian_language_level"] = str(summary_data)
        else:
            result["student_info"]["russian_language_level"] = ""

    def _update_achievements_info(self, result: Dict[str, Any], achievements_info_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(achievements_info_json_str, ["achievements_summary"])
        summary_data = parsed_info.get("achievements_summary")
        if summary_data:
            if isinstance(summary_data, dict):
                logger.warning(f"Achievements summary was a dict, converting to JSON string: {summary_data}")
                result["summaries"]["achievements_summary"] = json.dumps(summary_data, ensure_ascii=False)
            elif isinstance(summary_data, str):
                result["summaries"]["achievements_summary"] = summary_data
            else:
                result["summaries"]["achievements_summary"] = str(summary_data)
        else:
            result["summaries"]["achievements_summary"] = ""

    def _update_additional_docs_info(self, result: Dict[str, Any], additional_info_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(additional_info_json_str, ["additional_documents_summary"])
        summary_data = parsed_info.get("additional_documents_summary")
        if summary_data:
            if isinstance(summary_data, dict):
                logger.warning(f"Additional documents summary was a dict, converting to JSON string: {summary_data}")
                result["summaries"]["additional_documents_summary"] = json.dumps(summary_data, ensure_ascii=False)
            elif isinstance(summary_data, str):
                result["summaries"]["additional_documents_summary"] = summary_data
            else:
                result["summaries"]["additional_documents_summary"] = str(summary_data)
        else:
            result["summaries"]["additional_documents_summary"] = ""

    def _create_evaluation_prompt_instruction(self, current_result: Dict[str, Any], json_instruction: str) -> str:
        profile_summary = "Applicant Profile:\n"
        for key, value in current_result["student_info"].items(): 
            formatted_key = key.replace('_', ' ').title()
            val_str = str(value) if not isinstance(value, str) else value
            profile_summary += f"- {formatted_key}: {val_str if val_str else 'N/A'}\n"
        for key, value in current_result["summaries"].items(): 
            formatted_key = key.replace('_', ' ').title()
            val_str = str(value) if not isinstance(value, str) else value
            profile_summary += f"- {formatted_key}: {val_str if val_str else 'N/A'}\n"

        instruction = f"""Based on the applicant profile, provide an overall evaluation score (0-100) and brief comments in English.
        Consider all aspects: academics, skills, motivation, recommendations, language.
        {json_instruction}
        Fields: "evaluation_score" (integer, 0-100), "evaluation_comments" (string, English).
        Example: {{"evaluation_score": 85, "evaluation_comments": "Strong candidate with good GPA and relevant skills."}}
        Profile:
        {profile_summary}
        """
        return instruction

    def _update_evaluation(self, result: Dict[str, Any], evaluation_result_json_str: str) -> None:
        parsed_info = self._parse_llm_json_output(evaluation_result_json_str, ["evaluation_score", "evaluation_comments"])
        if parsed_info.get("evaluation_score") is not None:
            try:
                result["evaluation"]["score"] = int(parsed_info["evaluation_score"])
            except (ValueError, TypeError):
                score_val = parsed_info.get('evaluation_score', 'N/A')
                logger.warning(f"Could not parse evaluation score: {score_val}")
                result["evaluation"]["score"] = 0
        if parsed_info.get("evaluation_comments"): result["evaluation"]["comments"] = parsed_info["evaluation_comments"]

if __name__ == "__main__":
    try:
        processor = LLMProcessor()
        logger.info("LLM Processor initialized for testing.")
        mock_docs = {
            "passport": [{"content": "Name: John Doe\nDOB: 1990-01-01\nNationality: USA", "language": "en"}],
            "degree": [{"content": "University of Excellence\nGrades: Отлично - 5, Хорошо - 10, Удовлетворительно - 2", "language": "en"}],
            "cv": [{"content": "Skills: Python, Java. Projects: Web app. Some text with \"quotes\" and new\nlines.", "language": "en"}],
            "additional_documents": [{"content": "IELTS: 7.0. Special chars: *\n*", "language": "en"}]
        }
        application_data = processor.process_application(1, mock_docs)
        logger.info(f"Processed Application Data:\n{json.dumps(application_data, indent=2, ensure_ascii=False)}")

        # Test problematic JSON
        problem_json = "Here is the JSON: { \"cv_summary\": \"Skills: C++, Python. \\nProject: AI bot with some \\\"special characters\\\".\", } extra text after json"
        parsed_problem = processor._parse_llm_json_output(problem_json, ["cv_summary"])
        logger.info(f"Parsed problematic JSON: {parsed_problem}")

        problem_json_2 = "```json\n{\n  \"additional_documents_summary\": \"IELTS Test Report Form provided with the following details:\\n* Overall Band score: 7.0\\n* Listening score: 7.5\\n* Reading score: 7.9\\n* Writing score: 6.5\\n* Speaking score: 6.5\\n* Validation stamp and Administrator_s signature\"\n}\n```"
        parsed_problem_2 = processor._parse_llm_json_output(problem_json_2, ["additional_documents_summary"])
        logger.info(f"Parsed problematic JSON 2: {parsed_problem_2}")
        
        # Test dict in additional_documents_summary
        test_result_dict = {"summaries": {"additional_documents_summary": ""}}
        processor._update_additional_docs_info(test_result_dict, "{\"additional_documents_summary\": {\"IELTS score\": 7.0, \"Coursera certificate in ML\": null}}")
        logger.info(f"Processed additional_documents_summary (dict to json string): {test_result_dict['summaries']['additional_documents_summary']}")
        
        test_result_str = {"summaries": {"additional_documents_summary": ""}}
        processor._update_additional_docs_info(test_result_str, "{\"additional_documents_summary\": \"Simple string summary\"}")
        logger.info(f"Processed additional_documents_summary (string): {test_result_str['summaries']['additional_documents_summary']}")

    except Exception as e:
        logger.error(f"Error during LLMProcessor test: {e}", exc_info=True)

