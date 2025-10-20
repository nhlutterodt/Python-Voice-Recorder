"""Batch file processing utilities.

Provides a generic batch processor for processing multiple files/items sequentially
with automatic progress tracking, stats aggregation, and error handling.

NO DUPLICATION of existing utilities:
- performance_monitor.py handles operation measurement
- error_boundaries.py handles error context
- This module complements those by providing generic batch orchestration
"""

from dataclasses import dataclass
from typing import Any, Callable, List, Optional

from voice_recorder.utilities.base import BaseWorkerThread

from voice_recorder.core.logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class BatchProcessResult:
    """Result of processing a single item in a batch.
    
    Attributes:
        item_id: Identifier for the item
        success: Whether processing succeeded
        result: The processing result (if successful)
        error: Error message (if failed)
    """
    
    item_id: str
    success: bool
    result: Any = None
    error: Optional[str] = None


class BatchProcessorThread(BaseWorkerThread):
    """Generic batch processor for processing multiple items sequentially.
    
    Automatically handles progress tracking, stats aggregation, and error handling.
    
    Example:
        class MyBatchProcessor(BatchProcessorThread):
            def __init__(self, files):
                super().__init__(
                    items=files,
                    processor_func=self._process_file,
                    operation_name="File Processing"
                )
            
            def _process_file(self, file_path: str):
                # Process single file
                # Return result or raise exception
                return processed_data
    """
    
    def __init__(
        self,
        items: List[str],
        processor_func: Callable[[str], Any],
        operation_name: str = "Batch Processing",
    ):
        """Initialize the batch processor.
        
        Args:
            items: List of items to process (typically file paths)
            processor_func: Callable that processes a single item
                Should take item as argument and return result or raise exception
            operation_name: Name of the operation for logging
        """
        super().__init__(operation_name)
        self.items = items
        self.processor_func = processor_func
    
    def safe_run(self) -> None:
        """Execute batch processing.
        
        Iterates through items, calls processor_func for each, tracks stats.
        Emits progress updates and final summary.
        """
        total_items = len(self.items)
        if total_items == 0:
            logger.warning("Batch processing called with no items")
            return
        
        successful_count = 0
        failed_count = 0
        results: List[BatchProcessResult] = []
        
        for idx, item in enumerate(self.items):
            try:
                # Process item
                result = self.processor_func(item)
                
                # Track success
                successful_count += 1
                results.append(BatchProcessResult(
                    item_id=str(item),
                    success=True,
                    result=result,
                    error=None
                ))
                
                logger.debug(f"Successfully processed item {idx + 1}/{total_items}")
            
            except Exception as e:
                # Track failure
                failed_count += 1
                error_msg = str(e)
                results.append(BatchProcessResult(
                    item_id=str(item),
                    success=False,
                    result=None,
                    error=error_msg
                ))
                
                logger.warning(f"Failed to process item {idx + 1}/{total_items}: {error_msg}")
            
            # Emit progress
            progress = int(((idx + 1) / total_items) * 100)
            self.emit_progress(
                progress,
                f"Processing {idx + 1} of {total_items}"
            )
        
        # Emit final summary
        logger.info(
            f"Batch processing complete: {successful_count} succeeded, {failed_count} failed"
        )
