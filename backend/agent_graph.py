import os
import json
import re
import urllib.parse
import datetime
from typing import TypedDict, List, Dict, Any
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from groq import Groq, AsyncGroq
from langgraph.graph import StateGraph, START, END

# Load environment variables
load_dotenv()

# Define the persistent agent state
class AgentState(TypedDict):
    query: str                                         # The initial user query
    sub_questions: List[Any]                           # Decomposed sub-questions (list of strings or list of dicts)
    scraped_results: Dict[str, List[Dict[str, str]]]   # sub_question -> list of {"title", "url", "snippet"}
    summaries: Dict[str, Dict[str, Any]]               # sub_question -> {"summary", "url"}
    contradictions: str                                # Critique / contradictions flagged
    source_urls: List[Dict[str, str]]                  # Extracted source URLs and titles for citations
    final_report: str                                  # The final aggregated coherent report

# Helper: web search with Tavily API (primary) and Mojeek scraping fallback
def search_web(query: str, max_results: int = 3) -> List[Dict[str, str]]:
    """
    Web search function.
    Primary: Queries Tavily search API (structured, AI-optimized).
    Fallback: Scrapes Mojeek Search (scraping-friendly web index).
    """
    tavily_key = os.getenv("TAVILY_API_KEY")

    # Engine 1: Tavily API Search (Primary)
    if tavily_key:
        try:
            print(f"[Search Tool] Querying Tavily API for: '{query}'")
            payload = {
                "api_key": tavily_key,
                "query": query,
                "search_depth": "basic",
                "max_results": max_results
            }
            response = requests.post("https://api.tavily.com/search", json=payload, timeout=8)
            if response.status_code == 200:
                data = response.json()
                results = []
                for item in data.get("results", []):
                    results.append({
                        "title": item.get("title", ""),
                        "url": item.get("url", ""),
                        "snippet": item.get("content", "")
                    })
                if results:
                    print(f"  -> Tavily API succeeded with {len(results)} results")
                    return results
            else:
                print(f"[Search Tool] Tavily API returned status code {response.status_code}: {response.text}")
        except Exception as e:
            print(f"[Search Tool] Tavily API failed: {e}")
    else:
        print("[Search Tool] TAVILY_API_KEY is not set in environment or .env file.")

    # Engine 2: Mojeek Search (Fallback)
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    }
    # Strip 4-digit years from Mojeek query to bypass the search engine's temporal WAF rules
    clean_query = re.sub(r'\b\d{4}\b', '', query).strip()
    clean_query = re.sub(r'\s+', ' ', clean_query)
    
    mojeek_url = f"https://www.mojeek.com/search?q={urllib.parse.quote(clean_query)}"
    try:
        if clean_query != query:
            print(f"[Search Tool] Falling back to Mojeek scraper for: '{clean_query}' (Original: '{query}')")
        else:
            print(f"[Search Tool] Falling back to Mojeek scraper for: '{clean_query}'")
            
        response = requests.get(mojeek_url, headers=headers, timeout=8)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")
            items = soup.find_all("a", class_="title")
            results = []
            for item in items:
                title = item.get_text(strip=True)
                href = item.get("href", "")
                sibling_snippet = item.find_next("p", class_="s")
                snippet = sibling_snippet.get_text(strip=True) if sibling_snippet else ""
                
                if title and href:
                    results.append({
                        "title": title,
                        "url": href,
                        "snippet": snippet
                    })
                    if len(results) >= max_results:
                        break
            if results:
                print(f"  -> Mojeek scraper fallback succeeded with {len(results)} results")
                return results
        else:
            print(f"[Search Tool] Mojeek returned status code {response.status_code}")
    except Exception as e:
        print(f"[Search Tool] Mojeek failed: {e}")

    return []


# Initialize Groq client
def get_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in environmental variables or .env file.")
    return Groq(api_key=api_key)

# Node 1: Orchestrator Node (Decomposition)
def orchestrator_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [ORCHESTRATOR NODE] Decomposing Query ---")
    query = state["query"]
    client = get_groq_client()
    
    current_year = datetime.datetime.now().year
    
    prompt = (
        "You are an expert search planner. Your task is to decompose a complex, broad search query into 2 to 3 distinct, specific sub-questions that can be researched independently to give a complete view of the topic.\n"
        f"The current year is {current_year}. If the research topic relates to current events, product releases, software, or upcoming trends, ensure that your optimized search queries target recent information by explicitly appending the year '{current_year}' or other recent years (e.g., 2025, 2026) to the search keywords to fetch the latest info instead of outdated historical info.\n"
        "For each sub-question, you must generate a short, clean, 3-4 keyword optimized search query to use in a search engine (avoiding conversational words, punctuation, or quotes).\n"
        "Output the result ONLY as a valid JSON list of dictionaries with keys 'question' and 'search_query', with no additional text, explanation, or markdown formatting.\n"
        f"Query: {query}\n"
        "Example output:\n"
        "[\n"
        f"  {{\"question\": \"What is the release date of the new iPhone?\", \"search_query\": \"iphone 17 release date {current_year}\"}}\n"
        "]"
    )
    
    completion = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": "You are a precise JSON generator. Output only raw JSON lists of dictionaries."},
            {"role": "user", "content": prompt}
        ],
        temperature=0.2,
    )
    
    response_text = completion.choices[0].message.content.strip()
    
    # Robustly parse JSON (clean potential markdown code blocks)
    try:
        # Clean markdown codeblocks if LLM included them
        clean_text = response_text
        if clean_text.startswith("```"):
            # strip backticks and json identifier
            clean_text = re.sub(r"^```(?:json)?\n", "", clean_text)
            clean_text = re.sub(r"\n```$", "", clean_text)
            clean_text = clean_text.strip()
            
        sub_questions = json.loads(clean_text)
        if not isinstance(sub_questions, list):
            raise ValueError("Parsed JSON is not a list")
    except Exception as e:
        print(f"[Orchestrator] JSON parsing failed: {e}. Raw response: {response_text}")
        # Graceful fallback: look for lines starting with bullet points or quotes
        sub_questions = []
        for line in response_text.splitlines():
            line = line.strip().strip("-*•").strip("\"'[]")
            if line and len(line) > 5:
                # Local clean function
                clean_q = line.lower().replace("?", "").replace("'", "").replace('"', "")
                clean_q = clean_q.replace("what are the ", "").replace("how does ", "").replace("are there any ", "")
                clean_q = clean_q.replace("effects of ", "").replace("impact of ", "").replace("influence of ", "")
                clean_q = clean_q.strip()
                sub_questions.append({
                    "question": line,
                    "search_query": clean_q
                })
        # Final safety check
        if not sub_questions:
            sub_questions = [{
                "question": f"General search on: {query}",
                "search_query": query.lower().replace("?", "").strip()
            }]
            
    print(f"[Orchestrator] Decomposed into sub-questions: {sub_questions}")
    return {"sub_questions": sub_questions}

# Node 2: Search Agent Node (Scrape Web Results)
def search_agent_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [SEARCH NODE] Scraping Web Results ---")
    sub_questions = state["sub_questions"]
    scraped_results = {}
    
    for sq_info in sub_questions:
        # Support both string list and dictionary formats gracefully
        if isinstance(sq_info, dict):
            sq = sq_info["question"]
            search_q = sq_info["search_query"]
        else:
            sq = sq_info
            # Fallback clean for string format
            search_q = sq.lower().replace("?", "").replace("'", "").replace('"', "")
            search_q = search_q.replace("what are the ", "").replace("how does ", "").replace("are there any ", "")
            search_q = search_q.replace("effects of ", "").replace("impact of ", "").replace("influence of ", "")
            search_q = search_q.strip()
            
        print(f"[Search Node] Scraping for sub-question: '{sq}' (Optimized query: '{search_q}')")
        results = search_web(search_q, max_results=3)
        scraped_results[sq] = results
        print(f"  -> Found {len(results)} results")
        
    source_urls = []
    seen_urls = set()
    for sq, results in scraped_results.items():
        for r in results:
            url = r.get("url")
            if url and url not in seen_urls:
                seen_urls.add(url)
                source_urls.append({
                    "title": r.get("title", "Untitled Source"),
                    "url": url
                })
        
    return {"scraped_results": scraped_results, "source_urls": source_urls}

# Node 3: Summarizer Agent Node (Create clean summaries with citations)
def summarizer_agent_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [SUMMARIZER NODE] Synthesizing Sub-Answers ---")
    scraped_results = state["scraped_results"]
    client = get_groq_client()
    summaries = {}
    
    for sq, results in scraped_results.items():
        if not results:
            summaries[sq] = {
                "summary": "No search results could be retrieved for this topic.",
                "url": "N/A"
            }
            continue
            
        # Format the search snippets for Groq
        context = ""
        for idx, r in enumerate(results, 1):
            context += f"[{idx}] {r['title']}\nURL: {r['url']}\nSnippet: {r['snippet']}\n\n"
            
        prompt = (
            f"Sub-Question: {sq}\n\n"
            "Search Results:\n"
            f"{context}\n"
            "Based on the search results above, write a highly informative, direct, and factual 3-4 sentence summary answering the sub-question.\n"
            "Do not include any conversational preamble (e.g., 'Based on the snippets provided...'). Just output the answer directly.\n"
            "At the end of your response, specify the single primary source URL from the search results that you relied on most using this exact format: 'Source: <URL>'."
        )
        
        try:
            completion = client.chat.completions.create(
                model="llama-3.3-70b-versatile",
                messages=[
                    {"role": "system", "content": "You are a professional research analyst summarizing web search results factual and objectively."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                max_tokens=500
            )
            
            summary_text = completion.choices[0].message.content.strip()
            
            # Extract URL citation from the summary
            url_match = re.search(r"Source:\s*(https?://[^\s\)]+)", summary_text)
            source_url = url_match.group(1) if url_match else results[0]["url"]
            
            # Clean up the "Source: URL" text from the main summary body
            clean_summary = re.sub(r"\s*Source:\s*https?://[^\s\)]+", "", summary_text).strip()
            
            summaries[sq] = {
                "summary": clean_summary,
                "url": source_url
            }
            print(f"[Summarizer Node] Completed summary for: '{sq}' (Source: {source_url})")
            
        except Exception as e:
            print(f"[Summarizer Node] Error generating summary for '{sq}': {e}")
            summaries[sq] = {
                "summary": "Error generating summary due to API failure.",
                "url": results[0]["url"] if results else "N/A"
            }
            
    return {"summaries": summaries}

# Node 4: Critic Agent Node (Flag contradictions and conflicts)
def critic_agent_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [CRITIC NODE] Checking for Contradictions ---")
    summaries = state["summaries"]
    client = get_groq_client()
    
    # Format all summaries for the critic
    summaries_text = ""
    for sq, info in summaries.items():
        summaries_text += f"Sub-Question: {sq}\nAnswer: {info['summary']}\n\n"
        
    prompt = (
        "You are an elite scientific and research critic.\n"
        "Analyze the following research summaries for any direct contradictions, logical mismatches, or conflicting factual assertions. "
        "Pay special attention if different sources present opposing conclusions, different statistics, or conflicting perspectives.\n\n"
        "Summaries to analyze:\n"
        f"{summaries_text}\n"
        "Task:\n"
        "1. Identify any contradictions or conflicts if they exist, explain them clearly and point out which sub-answers conflict.\n"
        "2. If there are no contradictions or conflicts, reply with exactly: 'No contradictions found.'\n"
        "Do not write any introductory or outro messages. Answer directly."
    )
    
    try:
        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are an objective, precise research auditor checking information synthesis for logical consistency."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=800
        )
        
        contradictions = completion.choices[0].message.content.strip()
        print(f"[Critic Node] Analysis Completed. Result:\n{contradictions}")
        
    except Exception as e:
        print(f"[Critic Node] Error compiling critique: {e}")
        contradictions = "Error performing critique analysis."
        
    return {"contradictions": contradictions}

# Initialize Async Groq client
def get_async_groq_client():
    api_key = os.getenv("GROQ_API_KEY")
    if not api_key:
        raise ValueError("GROQ_API_KEY is not set in environmental variables or .env file.")
    return AsyncGroq(api_key=api_key)

# Node 5: Aggregator Node (Synthesizes all summaries and critiques into a final report)
async def aggregator_node(state: AgentState) -> Dict[str, Any]:
    print("\n--- [AGGREGATOR NODE] Generating Final Coherent Report ---")
    query = state["query"]
    summaries = state["summaries"]
    contradictions = state["contradictions"]
    source_urls = state.get("source_urls", [])
    
    # Format all summaries for the aggregator
    summaries_text = ""
    for sq, info in summaries.items():
        summaries_text += f"Sub-Question: {sq}\nAnswer: {info['summary']}\n\n"
        
    # Format sources for prompting
    sources_text = ""
    for idx, src in enumerate(source_urls, 1):
        sources_text += f"[{idx}] {src['title']} - {src['url']}\n"
        
    prompt = (
        "You are an elite scientific and research reporter.\n"
        "Your task is to synthesize the following sub-question summaries and the critic's contradiction analysis into a single, cohesive, comprehensive, and well-structured final research report.\n\n"
        f"Initial Query: {query}\n\n"
        "Research Summaries:\n"
        f"{summaries_text}\n"
        "Critic's Contradiction Audit / Feedback:\n"
        f"{contradictions}\n\n"
        "Available Sources:\n"
        f"{sources_text}\n"
        "Instructions:\n"
        "1. Write a detailed final report in markdown. Use clear headings (#, ##, ###), bold text, and lists where appropriate to make it professional.\n"
        "2. Directly address the user's initial query, integrating all the sub-answers into a single narrative.\n"
        "3. Address and resolve any contradictions or conflicts flagged by the critic's feedback. Explain why they exist or how different sources view them.\n"
        "4. Throughout the report, cite the relevant sources using bracket numbers (e.g., [1], [2]) matching the available sources list.\n"
        "5. Do NOT append the list of sources/URLs at the end of the text. The system will display them separately. Just write the report content.\n"
        "6. Do not include any meta-announcements or introductory filler (such as 'Here is the final report...'). Start directly with the title of the report."
    )
    try:
        client = get_async_groq_client()
        completion = await client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": "You are a professional research report writer. Output only structured markdown."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            max_tokens=3000
        )
        
        final_report = completion.choices[0].message.content or ""
        print(f"[Aggregator Node] Completed report generation. Length: {final_report[:50]}... ({len(final_report)} chars)")
        return {"final_report": final_report}
        
    except Exception as e:
        print(f"[Aggregator Node] Error generating report: {e}")
        error_msg = f"Error generating final report: {str(e)}"
        return {"final_report": error_msg}

# Build the LangGraph StateGraph
workflow = StateGraph(AgentState)

# Add the nodes to the graph
workflow.add_node("orchestrator", orchestrator_node)
workflow.add_node("search", search_agent_node)
workflow.add_node("summarizer", summarizer_agent_node)
workflow.add_node("critic", critic_agent_node)
workflow.add_node("aggregator", aggregator_node)

# Set the flow edges
workflow.add_edge(START, "orchestrator")
workflow.add_edge("orchestrator", "search")
workflow.add_edge("search", "summarizer")
workflow.add_edge("summarizer", "critic")
workflow.add_edge("critic", "aggregator")
workflow.add_edge("aggregator", END)

# Compile the workflow graph
research_graph = workflow.compile()
