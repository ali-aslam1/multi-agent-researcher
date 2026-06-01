import pprint
import sys
from agent_graph import research_graph

def run_test(query: str):
    print("=" * 80)
    print(f"STARTING RESEARCH GRAPH FOR QUERY: '{query}'")
    print("=" * 80)
    
    # Initialize the input state
    initial_state = {
        "query": query,
        "sub_questions": [],
        "scraped_results": {},
        "summaries": {},
        "contradictions": ""
    }
    
    # Run the graph step-by-step to see node outputs
    print("\n--- Starting Stream ---")
    
    current_state = initial_state
    try:
        # Using stream to show step-by-step transition of nodes
        for output in research_graph.stream(initial_state):
            for node_name, node_output in output.items():
                print(f"\n[STREAM CHECKPOINT] Node '{node_name}' finished executing.")
                print(f"Keys modified/added in state: {list(node_output.keys())}")
                
                # Print specific debug output depending on node
                if "sub_questions" in node_output:
                    print("Decomposed sub-questions:")
                    for idx, sq_info in enumerate(node_output["sub_questions"], 1):
                        if isinstance(sq_info, dict):
                            print(f"  {idx}. Question: '{sq_info['question']}'")
                            print(f"     Search Query: '{sq_info['search_query']}'")
                        else:
                            print(f"  {idx}. {sq_info}")
                
                if "scraped_results" in node_output:
                    print("Scrape count summary:")
                    for sq, results in node_output["scraped_results"].items():
                        print(f"  - '{sq}': {len(results)} search results extracted.")
                
                if "summaries" in node_output:
                    print("Summaries generated:")
                    for sq, info in node_output["summaries"].items():
                        print(f"  - Sub-Question: '{sq}'")
                        print(f"    Source URL: {info['url']}")
                        print(f"    Summary: {info['summary']}")
                
                if "contradictions" in node_output:
                    print("Critic evaluation result:")
                    print(node_output["contradictions"])
                    
                # Update current_state with cumulative changes
                current_state.update(node_output)
                
        print("\n" + "=" * 80)
        print("FINAL STRUCTURED OUTPUT CHECKPOINT (Graph Completed)")
        print("=" * 80)
        
        # Format the final dictionary nicely
        final_dict = {
            "query": current_state["query"],
            "sub_answers": [
                {
                    "sub_question": sq,
                    "summary": info["summary"],
                    "source_url": info["url"]
                }
                for sq, info in current_state["summaries"].items()
            ],
            "contradictions": current_state["contradictions"]
        }
        
        pprint.pprint(final_dict, width=100, compact=True)
        
    except Exception as e:
        print(f"\n[FATAL ERROR] Graph execution failed: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Test query: we choose a classic debate topic likely to have differing viewpoints / contradictions to test the critic node
    test_query = "Is caffeine intake good or bad for anxiety and sleep quality?"
    
    if len(sys.argv) > 1:
        test_query = " ".join(sys.argv[1:])
        
    run_test(test_query)
