"""Tests for extractor utility functions."""

import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, mock_open

import pytest

from stackbench.extractors.utils import (
    find_markdown_files,
    count_tokens,
    truncate_content,
    load_documents
)
from stackbench.extractors.models import Document


@pytest.fixture
def temp_repo():
    """Create a temporary repository structure for testing."""
    temp_dir = Path(tempfile.mkdtemp())
    
    # Create directory structure
    (temp_dir / "docs").mkdir()
    (temp_dir / "examples").mkdir()
    (temp_dir / "src").mkdir()
    (temp_dir / "nested" / "deep").mkdir(parents=True)
    
    # Create markdown files
    (temp_dir / "README.md").write_text("# Main README")
    (temp_dir / "docs" / "guide.md").write_text("# Documentation Guide")
    (temp_dir / "docs" / "api.mdx").write_text("# API Reference")
    (temp_dir / "examples" / "tutorial.md").write_text("# Tutorial")
    (temp_dir / "src" / "notes.md").write_text("# Development Notes")
    (temp_dir / "nested" / "deep" / "readme.md").write_text("# Deep README")
    
    # Create non-markdown files
    (temp_dir / "script.py").write_text("print('hello')")
    (temp_dir / "docs" / "image.png").write_text("fake image")
    
    yield temp_dir
    shutil.rmtree(temp_dir)


class TestFindMarkdownFiles:
    """Test markdown file discovery functionality."""
    
    def test_find_all_markdown_files(self, temp_repo):
        """Test finding all markdown files without filtering."""
        md_files = find_markdown_files(temp_repo)
        
        assert len(md_files) == 6
        
        # Check that all expected files are found
        file_names = [f.name for f in md_files]
        assert "README.md" in file_names
        assert "guide.md" in file_names
        assert "api.mdx" in file_names
        assert "tutorial.md" in file_names
        assert "notes.md" in file_names
        assert "readme.md" in file_names
    
    def test_find_markdown_files_with_include_folders(self, temp_repo):
        """Test finding markdown files with folder filtering."""
        md_files = find_markdown_files(temp_repo, include_folders=["docs"])
        
        assert len(md_files) == 2
        file_names = [f.name for f in md_files]
        assert "guide.md" in file_names
        assert "api.mdx" in file_names
    
    def test_find_markdown_files_multiple_include_folders(self, temp_repo):
        """Test finding markdown files with multiple include folders."""
        md_files = find_markdown_files(temp_repo, include_folders=["docs", "examples"])
        
        assert len(md_files) == 3
        file_names = [f.name for f in md_files]
        assert "guide.md" in file_names
        assert "api.mdx" in file_names
        assert "tutorial.md" in file_names
    
    def test_find_markdown_files_nonexistent_folder(self, temp_repo):
        """Test finding markdown files with nonexistent include folder."""
        md_files = find_markdown_files(temp_repo, include_folders=["nonexistent"])
        
        assert len(md_files) == 0
    
    def test_find_markdown_files_empty_directory(self):
        """Test finding markdown files in empty directory."""
        with tempfile.TemporaryDirectory() as temp_dir:
            md_files = find_markdown_files(Path(temp_dir))
            assert len(md_files) == 0
    
    def test_find_markdown_files_nested_folders(self, temp_repo):
        """Test finding markdown files in nested folder structure."""
        md_files = find_markdown_files(temp_repo, include_folders=["nested"])
        
        assert len(md_files) == 1
        assert md_files[0].name == "readme.md"


class TestTokenCounting:
    """Test token counting functionality."""
    
    def test_count_tokens_simple_text(self):
        """Test token counting with simple text."""
        content = "Hello world, this is a test."
        token_count = count_tokens(content)
        
        # Should return a reasonable token count
        assert isinstance(token_count, int)
        assert token_count > 0
        assert token_count < 20  # Simple text shouldn't have many tokens
    
    def test_count_tokens_empty_string(self):
        """Test token counting with empty string."""
        token_count = count_tokens("")
        assert token_count == 0
    
    def test_count_tokens_long_text(self):
        """Test token counting with longer text."""
        content = "This is a longer piece of text that should have more tokens. " * 50
        token_count = count_tokens(content)
        
        assert token_count > 100  # Should have many tokens
    
    @patch('tiktoken.encoding_for_model')
    def test_count_tokens_fallback(self, mock_encoding):
        """Test token counting fallback when tiktoken fails."""
        mock_encoding.side_effect = Exception("tiktoken failed")
        
        content = "This is test content"
        token_count = count_tokens(content)
        
        # Should fallback to character-based approximation
        expected_tokens = len(content) // 4
        assert token_count == expected_tokens
    
    def test_count_tokens_different_models(self):
        """Test token counting with different model specifications."""
        content = "Test content for different models"
        
        # These should not raise errors
        count1 = count_tokens(content, "gpt-4o-mini")
        count2 = count_tokens(content, "gpt-4")
        
        assert isinstance(count1, int)
        assert isinstance(count2, int)
        assert count1 > 0
        assert count2 > 0


class TestContentTruncation:
    """Test content truncation functionality."""
    
    def test_truncate_content_under_limit(self):
        """Test truncation when content is under token limit."""
        content = "Short content"
        truncated = truncate_content(content, max_tokens=1000)
        
        assert truncated == content  # Should be unchanged
    
    def test_truncate_content_over_limit(self):
        """Test truncation when content exceeds token limit."""
        content = "This is a long piece of content. " * 100
        truncated = truncate_content(content, max_tokens=50)
        
        assert len(truncated) < len(content)
        # Content may be truncated at any point, not necessarily cleanly
        assert len(truncated) > 0
    
    def test_truncate_content_exact_limit(self):
        """Test truncation when content is exactly at limit."""
        content = "Exact limit content"
        # Get the actual token count first
        actual_tokens = count_tokens(content)
        truncated = truncate_content(content, max_tokens=actual_tokens)
        
        assert truncated == content
    
    @patch('tiktoken.encoding_for_model')
    def test_truncate_content_fallback(self, mock_encoding):
        """Test content truncation fallback when tiktoken fails."""
        mock_encoding.side_effect = Exception("tiktoken failed")
        
        content = "This is test content that is quite long" * 10
        truncated = truncate_content(content, max_tokens=50)
        
        # Should fallback to character-based truncation
        max_chars = 50 * 4  # max_tokens * 4
        expected_length = min(len(content), max_chars)
        assert len(truncated) == expected_length
    
    def test_truncate_content_empty_string(self):
        """Test truncation with empty string."""
        truncated = truncate_content("", max_tokens=100)
        assert truncated == ""


class TestLoadDocuments:
    """Test document loading functionality."""
    
    def test_load_documents_valid_files(self, temp_repo):
        """Test loading valid markdown files."""
        md_files = find_markdown_files(temp_repo)
        documents = load_documents(md_files)
        
        assert len(documents) == 6
        
        # Check document structure
        for doc in documents:
            assert isinstance(doc, Document)
            assert doc.file_path.exists()
            assert len(doc.content) > 0
            assert len(doc.truncated_content) > 0
            assert doc.num_tokens > 0
    
    def test_load_documents_empty_file_list(self):
        """Test loading with empty file list."""
        documents = load_documents([])
        assert len(documents) == 0
    
    def test_load_documents_nonexistent_files(self):
        """Test loading nonexistent files."""
        fake_files = [Path("/nonexistent/file.md")]
        documents = load_documents(fake_files)
        
        # Should handle gracefully and return empty list
        assert len(documents) == 0
    
    @patch("builtins.open", mock_open(read_data=""))
    def test_load_documents_empty_files(self, temp_repo):
        """Test loading files with empty content."""
        md_files = find_markdown_files(temp_repo)
        
        # Mock empty files
        with patch("builtins.open", mock_open(read_data="")):
            documents = load_documents(md_files)
        
        # Should skip empty files
        assert len(documents) == 0
    
    @patch("builtins.open")
    def test_load_documents_encoding_error(self, mock_open_func, temp_repo):
        """Test loading files with encoding errors."""
        mock_open_func.side_effect = UnicodeDecodeError('utf-8', b'', 0, 1, 'invalid')
        
        md_files = find_markdown_files(temp_repo)
        documents = load_documents(md_files)
        
        # Should handle errors gracefully
        assert len(documents) == 0
    
    def test_load_documents_content_processing(self, temp_repo):
        """Test that documents are processed correctly."""
        # Create a file with known content
        test_file = temp_repo / "test.md"
        test_content = "# Test Document\n\nThis is a test document with some content."
        test_file.write_text(test_content)
        
        documents = load_documents([test_file])
        
        assert len(documents) == 1
        doc = documents[0]
        
        assert doc.content == test_content
        assert doc.truncated_content == test_content  # Should be same for short content
        assert doc.num_tokens > 0
        assert doc.file_path == test_file


if __name__ == "__main__":
    pytest.main([__file__])