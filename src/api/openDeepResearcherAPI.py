import os
import asyncio
import aiohttp
import nest_asyncio
from typing import List, Dict, Any, Optional, Tuple
import google.generativeai as genai
from dotenv import load_dotenv

# Apply nest_asyncio to allow nested event loops (needed for Jupyter/Colab environments)
nest_asyncio.apply()

# Load environment variables
load_dotenv()

class OpenDeepResearcherAPI:
    """
    Client for the OpenDeepResearcher service - an AI researcher that continuously 
    searches for information based on a user query until it has gathered all necessary details.
    """
    
    def __init__(self, model: str = "gemini-2.5-pro-exp-03-25"):
        """
        Initialize the OpenDeepResearcher API client
        
        Args:
            model (str): Gemini model to use (default: gemini-2.5-pro-exp-03-25)
        """
        # Get API keys from environment variables
        self.google_api_key = os.getenv("GOOGLE_API_KEY")
        self.serpapi_api_key = os.getenv("SERPAPI_API_KEY")
        self.jina_api_key = os.getenv("JINA_API_KEY")
        self.model = model
        
        # Validate API keys
        if not self.google_api_key:
            raise ValueError("Google API key is required. Set GOOGLE_API_KEY environment variable.")
        if not self.serpapi_api_key:
            raise ValueError("SERPAPI API key is required. Set SERPAPI_API_KEY environment variable.")
        if not self.jina_api_key:
            raise ValueError("Jina API key is required. Set JINA_API_KEY environment variable.")
        
        # Configure Gemini
        genai.configure(api_key=self.google_api_key)
        
        # Initialize Gemini model
        self.gemini_model = genai.GenerativeModel(self.model)
        
        # Base URLs for the different services
        self.serpapi_url = "https://serpapi.com/search"
        self.jina_base_url = "https://r.jina.ai/"  # Changed to match original implementation
    
    async def _call_llm(self, messages: List[Dict[str, str]]) -> str:
        """
        Call the LLM (Gemini)
        
        Args:
            messages (List[Dict[str, str]]): List of message objects for the LLM
            
        Returns:
            str: The LLM response content
        """
        # Convert messages format from OpenAI to Gemini format
        prompt = ""
        for message in messages:
            role = message["role"]
            content = message["content"]
            
            if role == "system":
                prompt += f"System: {content}\n\n"
            elif role == "user":
                prompt += f"User: {content}\n\n"
            elif role == "assistant":
                prompt += f"Assistant: {content}\n\n"
        
        # Call Gemini synchronously (we're already in an async function)
        loop = asyncio.get_event_loop()
        response = await loop.run_in_executor(
            None, 
            lambda: self.gemini_model.generate_content(prompt)
        )
        
        return response.text
    
    async def _search_serpapi(self, query: str) -> List[Dict[str, Any]]:
        """
        Perform a search using SERPAPI
        
        Args:
            query (str): Search query
            
        Returns:
            List[Dict[str, Any]]: List of search results
        """
        async with aiohttp.ClientSession() as session:
            params = {
                "q": query,
                "api_key": self.serpapi_api_key,
                "engine": "google"
            }
            
            async with session.get(self.serpapi_url, params=params) as response:
                if response.status != 200:
                    error_text = await response.text()
                    raise Exception(f"SERPAPI error: {response.status} - {error_text}")
                
                data = await response.json()
                # Return just the links like in the original implementation
                if "organic_results" in data:
                    return [item.get("link") for item in data["organic_results"] if "link" in item]
                return []
    
    async def _fetch_webpage(self, url: str) -> str:
        """
        Fetch webpage content using Jina
        
        Args:
            url (str): URL to fetch
            
        Returns:
            str: Webpage content
        """
        # Use the same URL format as the original implementation
        full_url = f"{self.jina_base_url}{url}"
        
        async with aiohttp.ClientSession() as session:
            headers = {
                "Authorization": f"Bearer {self.jina_api_key}"
            }
            
            try:
                async with session.get(full_url, headers=headers) as response:
                    if response.status == 200:
                        return await response.text()
                    else:
                        error_text = await response.text()
                        print(f"Jina API error for {url}: {response.status} - {error_text}")
                        return ""
            except Exception as e:
                print(f"Error fetching webpage with Jina: {str(e)}")
                return ""
    
    async def _generate_search_queries(self, research_query: str) -> List[str]:
        """
        Generate search queries based on the research topic
        
        Args:
            research_query (str): The main research query/topic
            
        Returns:
            List[str]: List of search queries
        """
        prompt = [
            {"role": "system", "content": "You are a helpful and precise research assistant."},
            {"role": "user", "content": f"User Query: {research_query}\n\nYou are an expert research assistant. Given the user's query, generate up to four distinct, precise search queries that would help gather comprehensive information on the topic. Return only a Python list of strings, for example: ['query1', 'query2', 'query3']. Do not include any markdown formatting, code blocks, or additional text."}
        ]
        
        response = await self._call_llm(prompt)
        
        # Clean up the response - remove any markdown code formatting
        cleaned_response = response.strip()
        if "```" in cleaned_response:
            # Extract content between triple backticks
            import re
            code_blocks = re.findall(r'```(?:python)?(.*?)```', cleaned_response, re.DOTALL)
            if code_blocks:
                cleaned_response = code_blocks[0].strip()
        
        try:
            # Try to evaluate the response as a Python list
            search_queries = eval(cleaned_response)
            if isinstance(search_queries, list):
                return search_queries
            else:
                print(f"LLM did not return a list. Response: {response}")
                # Fallback: try to extract a list-like structure
                if '[' in cleaned_response and ']' in cleaned_response:
                    list_content = cleaned_response[cleaned_response.find('[')+1:cleaned_response.rfind(']')]
                    items = [item.strip().strip("'\"") for item in list_content.split(',')]
                    return [item for item in items if item]
        except Exception as e:
            print(f"Error parsing search queries: {e} \nResponse: {response}")
            # Fallback: try to extract quoted strings
            import re
            quoted_strings = re.findall(r'[\'\"](.*?)[\'\"]', cleaned_response)
            if quoted_strings:
                return quoted_strings
            
            # Last resort: split by newlines and clean up
            lines = [line.strip() for line in cleaned_response.split('\n')]
            # Remove numbering (1., 2., etc.)
            cleaned_lines = []
            for line in lines:
                if line and (not line.startswith('```') and not line.endswith('```')):
                    # Remove numbering if present
                    if re.match(r'^\d+[\.\)]', line):
                        line = re.sub(r'^\d+[\.\)]\s*', '', line)
                    # Remove quotes if present
                    line = line.strip('"\'')
                    if line:
                        cleaned_lines.append(line)
            
            if cleaned_lines:
                return cleaned_lines[:4]  # Limit to 4 queries
        
        # If all else fails, generate some generic queries based on the research query
        return [
            f"{research_query} environmental impact",
            f"{research_query} benefits and drawbacks",
            f"{research_query} statistics and data",
            f"{research_query} future trends"
        ]
    
    async def _evaluate_page(self, url: str, content: str, query: str) -> Tuple[bool, str]:
        """
        Evaluate if a webpage is useful and extract relevant context
        
        Args:
            url (str): URL of the webpage
            content (str): Content of the webpage
            query (str): The research query/topic
            
        Returns:
            Tuple[bool, str]: (is_useful, extracted_context)
        """
        # First determine if the page is useful
        prompt = [
            {"role": "system", "content": "You are a strict and concise evaluator of research relevance."},
            {"role": "user", "content": f"User Query: {query}\n\nWebpage Content (first 20000 characters):\n{content[:20000]}\n\nYou are a critical research evaluator. Given the user's query and the content of a webpage, determine if the webpage contains information relevant and useful for addressing the query. Respond with exactly one word: 'Yes' if the page is useful, or 'No' if it is not. Do not include any extra text."}
        ]
        
        usefulness = await self._call_llm(prompt)
        usefulness = usefulness.strip()
        
        # Handle the response
        if usefulness == "Yes":
            # If useful, extract the relevant context
            extract_prompt = [
                {"role": "system", "content": "You are an expert in extracting and summarizing relevant information."},
                {"role": "user", "content": f"User Query: {query}\nWebpage URL: {url}\n\nWebpage Content (first 20000 characters):\n{content[:20000]}\n\nYou are an expert information extractor. Given the user's query and the webpage content, extract all pieces of information that are relevant for answering the user's query. Return only the relevant context as plain text without commentary."}
            ]
            
            context = await self._call_llm(extract_prompt)
            return True, context.strip()
        else:
            return False, ""
    
    async def _need_more_queries(self, current_context: str, research_query: str) -> Tuple[bool, List[str]]:
        """
        Determine if more search queries are needed and generate them
        
        Args:
            current_context (str): Current aggregated context
            research_query (str): The main research query/topic
            
        Returns:
            Tuple[bool, List[str]]: (need_more_queries, new_queries)
        """
        prompt = [
            {"role": "system", "content": "You are a systematic research planner."},
            {"role": "user", "content": f"User Query: {research_query}\n\nExtracted Relevant Contexts:\n{current_context}\n\nYou are an analytical research assistant. Based on the original query and the extracted contexts from webpages, determine if further research is needed. If further research is needed, provide up to four new search queries as a Python list (for example, ['new query1', 'new query2']). If you believe no further research is needed, respond with exactly <done>.\nOutput only a Python list or the token <done> without any additional text."}
        ]
        
        response = await self._call_llm(prompt)
        cleaned = response.strip()
        
        if cleaned == "<done>":
            return False, []
            
        try:
            new_queries = eval(cleaned)
            if isinstance(new_queries, list):
                return True, new_queries
            else:
                print("LLM did not return a list for new search queries. Response:", response)
                return False, []
        except Exception as e:
            print("Error parsing new search queries:", e, "\nResponse:", response)
            return False, []
    
    async def _generate_final_report(self, research_query: str, context: str) -> str:
        """
        Generate a final comprehensive report
        
        Args:
            research_query (str): The main research query/topic
            context (str): Aggregated research context
            
        Returns:
            str: Final report
        """
        prompt = [
            {"role": "system", "content": "You are a skilled report writer."},
            {"role": "user", "content": f"User Query: {research_query}\n\nGathered Relevant Contexts:\n{context}\n\nYou are an expert researcher and report writer. Based on the gathered contexts below and the original query, write a comprehensive, well-structured, and detailed report that addresses the query thoroughly. Include all relevant insights and conclusions without extraneous commentary."}
        ]
        
        return await self._call_llm(prompt)
    
    async def research(self, query: str, max_iterations: int = 10) -> str:
        """
        Perform comprehensive research on a query
        
        Args:
            query (str): The research query/topic
            max_iterations (int): Maximum number of research iterations
            
        Returns:
            str: Final research report
        """
        print(f"Starting research on: {query}")
        
        # Initialize research context
        aggregated_contexts = []
        all_search_queries = []
        iteration = 0
        
        # Generate initial search queries
        new_search_queries = await self._generate_search_queries(query)
        if not new_search_queries:
            print("No search queries were generated. Exiting.")
            return "No search queries were generated by the LLM. Please try again with a different query."
            
        all_search_queries.extend(new_search_queries)
        print(f"Initial search queries: {new_search_queries}")
        
        # Main research loop
        async with aiohttp.ClientSession() as session:
            while iteration < max_iterations:
                print(f"\n=== Iteration {iteration + 1}/{max_iterations} ===")
                iteration_contexts = []
                
                # For each search query, perform searches
                search_tasks = [self._search_serpapi(query) for query in new_search_queries]
                search_results = await asyncio.gather(*search_tasks)
                
                # Aggregate all unique links from all search queries
                unique_links = {}
                for idx, links in enumerate(search_results):
                    query_used = new_search_queries[idx]
                    for link in links:
                        if link and link not in unique_links:
                            unique_links[link] = query_used
                
                print(f"Found {len(unique_links)} unique links to process")
                
                # Process each link: fetch, evaluate, extract
                for link in unique_links:
                    try:
                        print(f"Processing: {link}")
                        content = await self._fetch_webpage(link)
                        if not content:
                            print(f"No content retrieved from {link}")
                            continue
                            
                        is_useful, extracted_context = await self._evaluate_page(link, content, query)
                        
                        if is_useful and extracted_context:
                            print(f"✓ Useful content found")
                            iteration_contexts.append(f"Source: {link}\n{extracted_context}")
                        else:
                            print(f"✗ Not useful")
                    except Exception as e:
                        print(f"Error processing {link}: {str(e)}")
                
                # Add iteration contexts to aggregated contexts
                if iteration_contexts:
                    aggregated_contexts.extend(iteration_contexts)
                    print(f"Added {len(iteration_contexts)} useful contexts in this iteration")
                else:
                    print("No useful contexts found in this iteration")
                
                # Determine if more queries are needed
                need_more, new_queries = await self._need_more_queries("\n".join(aggregated_contexts), query)
                
                if not need_more:
                    print("No more queries needed. Research complete.")
                    break
                
                if not new_queries:
                    print("No new search queries provided. Ending research.")
                    break
                    
                new_search_queries = new_queries
                all_search_queries.extend(new_search_queries)
                print(f"New search queries: {new_search_queries}")
                
                iteration += 1
        
        # Generate final report
        print("\nGenerating final report...")
        final_report = await self._generate_final_report(query, "\n".join(aggregated_contexts))
        
        return final_report
    
    def run_research(self, query: str, max_iterations: int = 10) -> str:
        """
        Synchronous wrapper for the research method
        
        Args:
            query (str): The research query/topic
            max_iterations (int): Maximum number of research iterations
            
        Returns:
            str: Final research report
        """
        return asyncio.run(self.research(query, max_iterations))