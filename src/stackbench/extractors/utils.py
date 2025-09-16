"""Utility functions for use case extraction."""

import os
from pathlib import Path
from typing import List

import tiktoken

from .models import Document


def should_exclude_document(file_path: Path) -> bool:
    """Check if document should be excluded based on filename patterns."""
    excluded_names = {
        "changelog", "readme", "license", "contributing", 
        "code_of_conduct", "security", "authors", "credits",
    }
    file_stem = file_path.stem.lower()
    return file_stem in excluded_names


def find_markdown_files(repo_path: Path, include_folders: List[str] = None) -> List[Path]:
    """Find all markdown files in repository, optionally filtered by folders."""
    md_files = []
    
    for root, dirs, files in os.walk(repo_path):
        # Filter directories if include_folders specified
        if include_folders:
            root_relative = Path(root).relative_to(repo_path)
            if not any(folder in str(root_relative) for folder in include_folders):
                continue
        
        for file in files:
            if file.endswith(('.md', '.mdx')):
                file_path = Path(root) / file
                if not should_exclude_document(file_path):
                    md_files.append(file_path)
    
    return md_files


def count_tokens(content: str, model: str = "gpt-5") -> int:
    """Count tokens in content using tiktoken."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        return len(encoding.encode(content))
    except Exception:
        # Fallback: rough approximation (1 token ≈ 4 characters)
        return len(content) // 4


def truncate_content(content: str, max_tokens: int = 8000, model: str = "gpt-5") -> str:
    """Truncate content to maximum token count."""
    try:
        encoding = tiktoken.encoding_for_model(model)
        tokens = encoding.encode(content)
        
        if len(tokens) <= max_tokens:
            return content
        
        truncated_tokens = tokens[:max_tokens]
        return encoding.decode(truncated_tokens)
    except Exception:
        # Fallback: rough character-based truncation
        max_chars = max_tokens * 4
        return content[:max_chars] if len(content) > max_chars else content


def load_documents(markdown_files: List[Path], max_tokens: int = 10000, model: str = "gpt-5") -> List[Document]:
    """Load markdown files into Document objects with token counting."""
    documents = []
    
    for file_path in markdown_files:
        try:
            # Skip excluded documents as safety net
            if should_exclude_document(file_path):
                continue
                
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Skip empty files
            if not content.strip():
                continue
                
            num_tokens = count_tokens(
                content=content, 
                model=model,
            )
            truncated_content = truncate_content(
                content=content, 
                max_tokens=max_tokens, 
                model=model
            )
            
            document = Document(
                file_path=file_path,
                content=content,
                truncated_content=truncated_content,
                num_tokens=num_tokens
            )
            documents.append(document)
            
        except Exception as e:
            print(f"Error loading {file_path}: {e}")
            continue
    
    return documents