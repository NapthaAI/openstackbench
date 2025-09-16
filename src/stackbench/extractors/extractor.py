"""Main extraction logic with parallel processing and early stopping."""

import json
import os
import time
from concurrent.futures import ThreadPoolExecutor
from typing import List

import dspy
from dotenv import load_dotenv

from ..config import get_config
from ..core.run_context import RunContext
from .models import Document, UseCase, ExtractionResult
from .modules import DocumentProcessor
from .utils import find_markdown_files, load_documents


def setup_dspy():
    """Initialize DSPy with configuration."""
    # Load .env file to ensure API keys are available
    load_dotenv()
    
    # Check if required API key is available
    if not os.getenv("OPENAI_API_KEY"):
        raise ValueError(
            "OPENAI_API_KEY not found in environment variables. "
            "Please add it to your .env file or set it as an environment variable."
        )
    
    config = get_config()
    lm = dspy.LM(
        model=config.dspy_model,
        cache=config.dspy_cache,
        max_tokens=config.dspy_max_tokens
    )
    dspy.configure(lm=lm)


def process_single_document(document: Document, language: str = "python", max_per_doc: int = 1) -> List[UseCase]:
    """Process a single document and return validated use cases."""
    processor = DocumentProcessor()
    return processor.process_document(document, language=language, max_per_doc=max_per_doc)


def get_relative_path(file_path, repo_dir):
    """Get relative path from repo directory for cleaner logging."""
    try:
        return str(file_path.relative_to(repo_dir))
    except ValueError:
        # If file is not under repo_dir, just return the name
        return file_path.name


def extract_use_cases(context: RunContext) -> ExtractionResult:
    """
    Extract use cases from repository documentation with parallel processing and early stopping.
    
    Args:
        context: RunContext containing repository path and configuration
        
    Returns:
        ExtractionResult with extracted use cases and metadata
    """
    start_time = time.time()
    config = get_config()
    
    # Setup DSPy
    setup_dspy()
    
    # Find markdown files
    print(f"Finding markdown files in {context.repo_dir}...")
    md_files = find_markdown_files(
        repo_path=context.repo_dir,
        include_folders=context.config.include_folders
    )
    
    if not md_files:
        return ExtractionResult(
            total_documents_processed=0,
            documents_with_use_cases=0,
            total_use_cases_found=0,
            final_use_cases=[],
            processing_time_seconds=time.time() - start_time,
            errors=["No markdown files found"]
        )
    
    print(f"Found {len(md_files)} markdown files")
    
    # Load documents
    print("Loading documents...")
    documents = load_documents(
        markdown_files=md_files,
        max_tokens=config.MAX_DOC_TOKENS,
        model=config.dspy_model
    )
    
    if not documents:
        return ExtractionResult(
            total_documents_processed=0,
            documents_with_use_cases=0,
            total_use_cases_found=0,
            final_use_cases=[],
            processing_time_seconds=time.time() - start_time,
            errors=["No valid documents loaded"]
        )
    
    # Sort documents by token count (larger documents first - likely more comprehensive)
    documents.sort(key=lambda doc: doc.num_tokens, reverse=True)
    
    print(f"Loaded {len(documents)} documents, processing with target of {context.config.num_use_cases} use cases...")
    
    # Get language and max_use_case_per_doc from context config 
    language = context.config.language or "python"
    max_per_doc = context.config.max_use_case_per_doc
    
    # Process documents in parallel with early stopping
    all_use_cases = []
    documents_with_use_cases = 0
    processed_docs = 0
    errors = []
    
    max_workers = min(context.config.use_case_max_workers, len(documents))
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit initial batch to fill pipeline
        active_futures = {}
        doc_index = 0
        
        # Fill initial pipeline
        while len(active_futures) < max_workers and doc_index < len(documents):
            doc = documents[doc_index]
            future = executor.submit(process_single_document, doc, language, max_per_doc)
            active_futures[future] = doc
            doc_index += 1
        
        # Process results and keep pipeline full until target reached
        while active_futures and len(all_use_cases) < context.config.num_use_cases:
            # Wait for at least one to complete
            completed_futures = []
            for future in list(active_futures.keys()):
                if future.done():
                    completed_futures.append(future)
            
            # If no futures completed yet, wait a bit and continue
            if not completed_futures:
                time.sleep(0.1)
                continue
            
            # Process completed futures
            for future in completed_futures:
                document = active_futures.pop(future)
                processed_docs += 1
                
                try:
                    use_cases = future.result()
                    if use_cases:
                        all_use_cases.extend(use_cases)
                        documents_with_use_cases += 1
                        relative_path = get_relative_path(document.file_path, context.repo_dir)
                        print(f"Processed {relative_path}: {len(use_cases)} use cases "
                              f"(total: {len(all_use_cases)}/{context.config.num_use_cases})")
                    else:
                        relative_path = get_relative_path(document.file_path, context.repo_dir)
                        print(f"Processed {relative_path}: no use cases found")
                    
                except Exception as e:
                    relative_path = get_relative_path(document.file_path, context.repo_dir)
                    error_msg = f"Error processing {relative_path}: {e}"
                    errors.append(error_msg)
                    print(error_msg)
            
            # Early stopping check - exit if target reached
            if len(all_use_cases) >= context.config.num_use_cases:
                print(f"Reached target of {context.config.num_use_cases} use cases, stopping early")
                break
            
            # Fill pipeline with new documents while we have capacity and haven't reached target
            while (len(active_futures) < max_workers and 
                   doc_index < len(documents) and 
                   len(all_use_cases) < context.config.num_use_cases):
                doc = documents[doc_index]
                future = executor.submit(process_single_document, doc, language, max_per_doc)
                active_futures[future] = doc
                doc_index += 1
        
        # Cancel any remaining futures if target reached or no more docs
        for future in active_futures:
            if not future.done():
                future.cancel()
    
    # Trim to exact target count
    final_use_cases = all_use_cases[:context.config.num_use_cases]
    
    # Create result
    result = ExtractionResult(
        total_documents_processed=processed_docs,
        documents_with_use_cases=documents_with_use_cases,
        total_use_cases_found=len(all_use_cases),
        final_use_cases=final_use_cases,
        processing_time_seconds=time.time() - start_time,
        errors=errors
    )
    
    # Save use cases to run context
    save_use_cases(context, result)
    
    # Update run context status
    context.mark_extraction_completed(final_use_cases)
    
    print(f"Extraction completed: {len(final_use_cases)} use cases from {processed_docs} documents "
          f"in {result.processing_time_seconds:.1f}s")
    
    return result


def save_use_cases(context: RunContext, result: ExtractionResult) -> None:
    """Save extracted use cases to the run context data directory."""
    use_cases_file = context.get_use_cases_file()
    
    # Convert to serializable format
    use_cases_data = {
        "extraction_metadata": {
            "total_documents_processed": result.total_documents_processed,
            "documents_with_use_cases": result.documents_with_use_cases,
            "total_use_cases_found": result.total_use_cases_found,
            "processing_time_seconds": result.processing_time_seconds,
            "errors": result.errors,
            "extracted_at": time.time()
        },
        "use_cases": [use_case.model_dump() for use_case in result.final_use_cases]
    }
    
    with open(use_cases_file, 'w') as f:
        json.dump(use_cases_data, f, indent=2, default=str)
    
    print(f"Saved {len(result.final_use_cases)} use cases to {use_cases_file}")


def load_use_cases(context: RunContext) -> List[UseCase]:
    """Load use cases from the run context data directory."""
    use_cases_file = context.get_use_cases_file()
    
    if not use_cases_file.exists():
        return []
    
    try:
        with open(use_cases_file, 'r') as f:
            data = json.load(f)
        
        return [UseCase(**use_case_data) for use_case_data in data["use_cases"]]
    except Exception as e:
        print(f"Error loading use cases: {e}")
        return []