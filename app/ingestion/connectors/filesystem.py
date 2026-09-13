"""Filesystem connector for document ingestion."""

import hashlib
import mimetypes
from pathlib import Path
from typing import Iterator, Optional, Set, List
from dataclasses import dataclass
from datetime import datetime

from app.domain.metadata.source import SourceMetadata, SourceType
from app.domain.models.document import Document, DocumentVersion, DocumentStatus


@dataclass
class FilesystemConnectorConfig:
    """Configuration for filesystem connector."""
    
    root_path: str
    allowed_extensions: Optional[Set[str]] = None
    max_file_size_mb: int = 25
    recursive: bool = True
    follow_symlinks: bool = False
    exclude_patterns: Optional[List[str]] = None
    
    def __post_init__(self):
        if self.allowed_extensions is None:
            self.allowed_extensions = {".pdf", ".docx", ".html", ".md", ".csv", ".txt"}
        if self.exclude_patterns is None:
            self.exclude_patterns = ["**/.*", "**/__pycache__/**", "**/*.tmp"]


class FilesystemConnector:
    """Connector that scans filesystem directories for documents to index."""
    
    def __init__(self, config: FilesystemConnectorConfig):
        self.config = config
        self._root_path = Path(config.root_path).resolve()
    
    def scan(self) -> Iterator[Document]:
        """Scan the configured directory and yield Documents for each valid file."""
        if not self._root_path.exists():
            raise ValueError(f"Root path does not exist: {self._root_path}")
        
        if not self._root_path.is_dir():
            raise ValueError(f"Root path is not a directory: {self._root_path}")
        
        for file_path in self._walk_files():
            if self._should_process(file_path):
                document = self._create_document(file_path)
                if document:
                    yield document
    
    def _walk_files(self) -> Iterator[Path]:
        """Walk the directory tree yielding file paths."""
        if self.config.recursive:
            pattern = "**/*"
        else:
            pattern = "*"
        
        for path in self._root_path.glob(pattern):
            if path.is_file():
                yield path
            elif path.is_dir() and not self.config.recursive:
                continue
            elif path.is_symlink() and not self.config.follow_symlinks:
                continue
    
    def _should_process(self, file_path: Path) -> bool:
        """Check if file should be processed based on configuration."""
        # Check extension
        if self.config.allowed_extensions:
            if file_path.suffix.lower() not in self.config.allowed_extensions:
                return False
        
        # Check file size
        try:
            size_mb = file_path.stat().st_size / (1024 * 1024)
            if size_mb > self.config.max_file_size_mb:
                return False
        except OSError:
            return False
        
        # Check exclude patterns
        if self.config.exclude_patterns:
            rel_path = file_path.relative_to(self._root_path)
            for pattern in self.config.exclude_patterns:
                if self._match_pattern(rel_path, pattern):
                    return False
        
        return True
    
    def _match_pattern(self, path: Path, pattern: str) -> bool:
        """Simple pattern matching for exclude patterns."""
        import fnmatch
        return fnmatch.fnmatch(str(path), pattern) or fnmatch.fnmatch(path.name, pattern)
    
    def _create_document(self, file_path: Path) -> Optional[Document]:
        """Create a Document entity from a file path."""
        try:
            stat = file_path.stat()
            
            # Calculate SHA256 checksum
            checksum = self._calculate_checksum(file_path)
            
            # Determine MIME type
            mime_type, _ = mimetypes.guess_type(str(file_path))
            
            # Create source metadata
            source_metadata = SourceMetadata(
                source_type=SourceType.FILESYSTEM,
                source_path=str(file_path.relative_to(self._root_path)),
                file_name=file_path.name,
                file_extension=file_path.suffix.lower(),
                file_size_bytes=stat.st_size,
                mime_type=mime_type,
                checksum_sha256=checksum,
                last_modified=datetime.fromtimestamp(stat.st_mtime),
            )
            
            # Create document version
            version = DocumentVersion(
                content_hash=checksum,
                source_metadata=source_metadata,
            )
            
            # Create document
            document = Document(
                title=file_path.stem,
                source_metadata=source_metadata,
                status=DocumentStatus.PENDING,
            )
            document.add_version(version)
            
            return document
            
        except Exception:
            return None
    
    def _calculate_checksum(self, file_path: Path) -> str:
        """Calculate SHA256 checksum of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(8192), b""):
                sha256.update(chunk)
        return sha256.hexdigest()
    
    def get_file_count(self) -> int:
        """Get total count of files that would be processed."""
        return sum(1 for _ in self.scan())