import requests
import time
import concurrent.futures

# Set your base URL (adjust the port and domain as needed)
BASE_URL = "https://api.ragie.ai"
QUERY_ENDPOINT = f"{BASE_URL}/retrievals"

# Define a sample knowledge base ID for testing.
KNOWLEDGE_BASE_ID = "55"

# Updated list of 10 sample queries based on the lung cancer PDFs.
sample_queries = [
    "What is lung cancer and how does it develop?",
    "What are the main types of lung cancer, including NSCLC and SCLC?",
    "What are the risk factors associated with lung cancer?",
    "How is lung cancer diagnosed and staged?",
    "What are the recommended screening methods for lung cancer?",
    "What treatment options are available for non-small cell lung cancer?",
    "How is small cell lung cancer typically treated?",
    "What are the common side effects of lung cancer treatments?",
    "What lifestyle changes can help reduce the risk of lung cancer recurrence?",
    "How can survivors manage long-term health concerns after lung cancer treatment?"
]

def query_api(query: str):
    """
    Send a query to the /query endpoint and measure the latency.
    """
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer tnt_IaYFVQkh7fq_ZiEfWDZE76FMAWw4AKooJ88kbjs9igKHlY1GiG63kUU"
    }
    payload = {
        "filter": { "knowledgeBase_id": KNOWLEDGE_BASE_ID },
        "query": query,
    }
    start_time = time.time()
    response = requests.post(QUERY_ENDPOINT, json=payload, headers=headers)
    end_time = time.time()
    latency = end_time - start_time
    return {
        "query": query,
        "latency": latency,
        "status_code": response.status_code,
    }

def sequential_query_test():
    """
    Test the query endpoint sequentially and print the latency for each request.
    """
    print("Starting sequential query tests...")
    for query in sample_queries:
        result = query_api(query)
        print(f"Query: {result['query']}\n"
              f"Latency: {result['latency']:.3f} seconds, "
              f"Status: {result['status_code']}\n{'-'*40}")

def concurrent_query_test(concurrent_requests: int = 10):
    """
    Test the query endpoint with multiple concurrent requests using ThreadPoolExecutor.
    """
    print(f"Starting concurrent query tests with {concurrent_requests} requests...")
    
    # Create a list of queries by repeating sample queries if necessary.
    queries = (sample_queries * ((concurrent_requests // len(sample_queries)) + 1))[:concurrent_requests]
    
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrent_requests) as executor:
        futures = {executor.submit(query_api, query): query for query in queries}
        for future in concurrent.futures.as_completed(futures):
            try:
                result = future.result()
                print(f"Query: {result['query']}\n"
                      f"Latency: {result['latency']:.3f} seconds, "
                      f"Status: {result['status_code']}\n{'-'*40}")
            except Exception as exc:
                print(f"Query generated an exception: {exc}")

if __name__ == '__main__':
    # Run sequential tests to measure individual response times.
    # sequential_query_test()
    # Run concurrent tests to evaluate the system's behavior under load.
    concurrent_query_test(concurrent_requests=20)
