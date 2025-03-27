import json
from datetime import datetime
from typing import Optional, List, Dict, Any, Union

import requests
from fastapi import FastAPI, HTTPException, Query, UploadFile, File, Form, Body
from pydantic import BaseModel

app = FastAPI()

# Base URL for ragie.ai API endpoints (adjust if necessary)
BASE_URL = "https://api.ragie.ai"


# --------------------------
# Utility Function
# --------------------------
def get_api_response(url: str, params: Optional[dict] = None, method: str = "GET", payload: Optional[dict] = None, file: Optional[dict] = None) -> dict:
    """
    Helper function to perform API calls and return the JSON response.
    """
    # Base headers without Content-Type (will be set appropriately based on request type)
    headers = {
        "accept": "application/json",
        "authorization": f"Bearer tnt_IaYFVQkh7fq_ZiEfWDZE76FMAWw4AKooJ88kbjs9igKHlY1GiG63kUU"
    }
    
    # Start timing the request
    start_time = datetime.now()
    
    try:
        if method.upper() == "GET":
            # For GET requests, add Content-Type header
            get_headers = headers.copy()
            get_headers["Content-Type"] = "application/json"
            response = requests.get(url, headers=get_headers, params=params)
        elif method.upper() == "POST":
            if file:
                # For file uploads, don't set Content-Type - let requests handle it
                # Let requests handle multipart/form-data encoding
                response = requests.post(url, headers=headers, data=payload, files=file)
            else:
                # For regular JSON POST requests
                json_headers = headers.copy()
                json_headers["Content-Type"] = "application/json"
                response = requests.post(url, headers=json_headers, json=payload)
        elif method.upper() == "DELETE":
            # For DELETE requests
            delete_headers = headers.copy()
            delete_headers["Content-Type"] = "application/json"
            response = requests.delete(url, headers=delete_headers)
        else:
            raise ValueError(f"Unsupported HTTP method: {method}")
        
        # Calculate elapsed time
        elapsed_time = (datetime.now() - start_time).total_seconds()
        print(f"API Request to {url} ({method}) completed in {elapsed_time:.3f} seconds")
            
        response.raise_for_status()
        
        # Handle empty responses (like from DELETE operations)
        if response.text.strip():
            result = response.json()
            # Log response size for debugging
            print(f"Response size: {len(str(result))} characters")
            return result
        return {}
        
    except requests.exceptions.RequestException as e:
        # Calculate elapsed time on error too
        elapsed_time = (datetime.now() - start_time).total_seconds()
        print(f"API Request to {url} ({method}) FAILED after {elapsed_time:.3f} seconds")
        
        # Better error handling to see exactly what's going wrong
        error_detail = str(e)
        if hasattr(e, 'response') and e.response:
            try:
                error_detail = e.response.json()
            except:
                error_detail = e.response.text
        raise HTTPException(
            status_code=e.response.status_code if hasattr(e, 'response') else 500,
            detail=f"Error from Ragie API: {error_detail}"
        )


# --------------------------
# Pydantic Models for Request Bodies (for endpoints that use JSON)
# --------------------------
class QueryRequest(BaseModel):
    knowledgeBase_id: str
    query: str


# --------------------------
# FastAPI Endpoints
# --------------------------

@app.post("/ingest")
async def ingest_document_endpoint(
    organization_id: str = Form(...),
    knowledgeBase_id: str = Form(...),
    external_id: Optional[str] = Form(''),
    name: Optional[str] = Form(''),
    partition: Optional[str] = Form(''),
    file: UploadFile = File(...)
):
    """
    Ingest a document into ragie.ai using the 'Create Document' endpoint.
    The file is uploaded along with additional metadata.
    """
    url = f"{BASE_URL}/documents"

    # Create metadata dictionary with organization_id and knowledgeBase_id
    metadata_dict = {
        "organization_id": organization_id,
        "knowledgeBase_id": knowledgeBase_id
    }

    # Prepare form data
    data = {
        "mode": "fast",
        "metadata": json.dumps(metadata_dict)  # Convert metadata dict to JSON string
    }
    
    if external_id:
        data["external_id"] = external_id
    if name:
        data["name"] = name
    if partition:
        data["partition"] = partition

    # Prepare file data
    files = {"file": (file.filename, file.file, file.content_type)}

    # Use the get_api_response function to make the API call
    result = get_api_response(url, method="POST", payload=data, file=files)
    return result


@app.delete("/documents/{document_id}")
def delete_document_endpoint(document_id: str):
    """
    Delete a document from a specified knowledge base.
    """
    url = f"{BASE_URL}/documents/{document_id}"
    result = get_api_response(url, method="DELETE")
    return result


@app.post("/query")
def query_knowledge_base_endpoint(request: QueryRequest):
    """
    Query a specific knowledge base to retrieve relevant document chunks.
    """
    url = f"{BASE_URL}/retrievals"
    payload = {
        "filter": { "knowledgeBase_id": request.knowledgeBase_id },
        "query": request.query,
    }
    result = get_api_response(url, method="POST", payload=payload)
    return result


@app.get("/documents")
def list_documents_endpoint(
    organization_id: str = Query(..., description="Filter by organization_id"),
    knowledgeBase_id: Optional[str] = Query(None, description="Filter by knowledgeBase_id")
):
    """
    List documents. Optionally filter by organization_id and/or knowledgeBase_id.
    """
    url = f"{BASE_URL}/documents"
    
    # Extract string values from Query parameters
    org_id_str = str(organization_id)
    kb_id_str = str(knowledgeBase_id) if knowledgeBase_id is not None else None
    
    # Build the metadata filter
    if kb_id_str:
        # If both filters are present, use $and
        filter_query = {
            "$and": [
                {"organization_id": {"$eq": org_id_str}},
                {"knowledgeBase_id": {"$eq": kb_id_str}}
            ]
        }
    else:
        # If only organization_id is present, use simple filter
        filter_query = {"organization_id": {"$eq": org_id_str}}
    
    # Add the filter to params if we have any
    params = {"filter": json.dumps(filter_query)}
    
    # Make the API call
    response = get_api_response(url, params=params, method="GET")
    
    # Extract documents from response
    documents = response.get("documents", []) if response else []
    return documents


@app.get("/knowledge-bases", response_model=List[Dict[str, Any]])
def list_knowledge_bases_endpoint(organization_id: str = Query(..., description="Organization identifier")):
    """
    List knowledge bases for a given organization by grouping documents based on 'knowledgeBase_id'.
    Each knowledge base includes its title and creation time.
    """
    # Convert organization_id to string if it's not already
    org_id_str = str(organization_id)
    
    # Direct call to get_api_response instead of going through list_documents_endpoint
    url = f"{BASE_URL}/documents"
    
    # Build the metadata filter
    filter_query = {"organization_id": {"$eq": org_id_str}}
    
    # Add the filter to params
    params = {"filter": json.dumps(filter_query)}
    
    # Make the API call directly
    response = get_api_response(url, params=params, method="GET")
    
    # Extract documents from response
    documents = response.get("documents", []) if response else []
    
    kb_dict = {}
    
    for doc in documents:
        metadata = doc.get("metadata", {})
        kb_id = metadata.get("knowledgeBase_id")  # Get knowledgeBase_id from metadata
        if kb_id:
            if kb_id not in kb_dict:
                kb_dict[kb_id] = {
                    "knowledgeBase_id": kb_id,
                    "title": metadata.get("kb_title", "Unknown Title"),
                    "creation_time": metadata.get("kb_creation_time", "Unknown Time")
                }
    return list(kb_dict.values())


# --------------------------
# Run the Application with Uvicorn
# --------------------------
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)