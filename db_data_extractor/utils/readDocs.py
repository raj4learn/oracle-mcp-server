# Relative Path: db_data_extractor\utils\readDocs.py
# db_data_extractor\utils\readDocs.py

# This method will be reading the docuemntation from md files.
# will give clarity of all the components that are used in the application.

import logging
import os
from typing import Optional

# Configure logger for this module
logger = logging.getLogger('db_data_extractor.utils.ReadDocs')
logger.info('ReadDocs module loaded')

class ReadDocs:
    knowledge_base_dir_name = ".windsurf"

    def __init__(self, connection=None):
        """
        Initialize with an existing connection or create a new one.
        
        Args:
            connection (OracleConnection, optional): Existing connection to use
        """
        
        logger.info("ReadDocs initialized with connection")
    
    def read_knowledgebase_index_file(self):
        """
            Read the index file (.windsurf\\rules\\index.md) of the knowledge.
            This will help AI to get the overview of the knowledgebase.
            and with this info AI can pass the right component to get the details about that component
            BY calling read_docs(component) method with the component Name
        """
        logger.info("Reading knowledgebase index file")
        return self.read_docs("index.md")
    
    # Read md files and for the given component, if the component is missing read all the md files 
    # and share the details with Agent.
    def read_docs(self, component: Optional[str] = None):
        logger.info(f"Reading documentation for component: {component}")
        if component is None:
            return self.read_markdown_from_knowledgebase()
        else:
            return self.read_markdown_from_knowledgebase(component)

    
    def _discover_files_to_read(self, knowledge_base_path: str, component: Optional[str] = None) -> tuple[list[str], bool, Optional[str]]:
        """
        Discovers markdown files in the given path. Traverses the directory structure once.
        If a component is specified, tries to find it. Otherwise, lists all .md files.

        Args:
            knowledge_base_path: The root directory to search within.
            component: Optional specific filename to target.

        Returns:
            A tuple: (list_of_file_paths_to_read, specific_file_was_targeted, actual_specific_path_if_found).
        """
        all_md_files_in_dir = []
        specific_component_path_found = None
        target_filename_lower = None

        if component:
            target_filename_lower = component.lower()
            if not target_filename_lower.endswith(".md"):
                target_filename_lower += ".md"

        for root, _, files in os.walk(knowledge_base_path):
            for filename_in_dir in files:
                current_file_full_path = os.path.join(root, filename_in_dir)
                filename_lower = filename_in_dir.lower()

                if target_filename_lower and not specific_component_path_found:
                    if filename_lower == target_filename_lower:
                        specific_component_path_found = current_file_full_path
                
                if filename_lower.endswith(".md"):
                    all_md_files_in_dir.append(current_file_full_path)
        
        if component:
            if specific_component_path_found:
                return [specific_component_path_found], True, specific_component_path_found
            else:
                # Component specified but not found, return all files
                return all_md_files_in_dir, False, None 
        else:
            # No component specified, return all files
            return all_md_files_in_dir, False, None

    def _read_files_content(self, file_paths: list[str]) -> tuple[str, int]:
        """
        Reads content from a list of file paths and concatenates them.

        Args:
            file_paths: A list of absolute paths to markdown files.

        Returns:
            A tuple: (combined_content_string, number_of_files_successfully_read).
        """
        all_markdown_content = ""
        files_successfully_read = 0
        for file_path_to_read in file_paths:
            try:
                with open(file_path_to_read, 'r', encoding='utf-8') as f:
                    all_markdown_content += f.read() + "\n\n"
                    files_successfully_read += 1
            except Exception as e:
                logger.error(f"Error reading file {file_path_to_read}: {e}")
        return all_markdown_content.strip(), files_successfully_read

    def read_markdown_from_knowledgebase(self, component: Optional[str] = None) -> str:
        """
        Reads markdown (.md) files from the '.windsurf' directory (expected to be located at ../.windsurf/ 
        relative to this script's utils directory). Uses helper methods for discovery and reading.

        If a 'component' (filename) is provided, it attempts to read that specific file case-insensitively.
        If the specified file is not found, or if no component is provided, it reads all .md files 
        from the '.windsurf' directory and its subfolders.

        Args:
            component: Optional. The name of the specific markdown file to read (e.g., 'myDoc.md').

        Returns:
            A string containing the content of the specified file, or the combined content of all 
            markdown files if the specific file isn't found or no component is specified.
            Returns an empty string if the base '.windsurf' directory doesn't exist or no files are read.
        """
        current_script_dir = os.path.dirname(os.path.abspath(__file__))
        knowledge_base_path = os.path.abspath(os.path.join(current_script_dir, '..', self.knowledge_base_dir_name))

        if not os.path.isdir(knowledge_base_path):
            logger.error(f"Base knowledge directory '{self.knowledge_base_dir_name}' not found at {knowledge_base_path}")
            return ""

        files_to_process, specific_file_targeted, specific_path_found = self._discover_files_to_read(knowledge_base_path, component)

        if component:
            if specific_file_targeted and specific_path_found:
                logger.info(f"Specific component file '{component}' found. Reading: {specific_path_found}")
            else:
                logger.info(f"Component file '{component}' not found in '{knowledge_base_path}'. Reading all {len(files_to_process)} markdown files instead.")
        
        if not files_to_process:
            if component and not specific_file_targeted:
                logger.info(f"Component file '{component}' was not found, and no other markdown files were found in '{knowledge_base_path}'.")
            elif not component:
                logger.info(f"No markdown files found in '{knowledge_base_path}'.")
            return ""

        all_markdown_content, files_processed_count = self._read_files_content(files_to_process)
        
        if files_processed_count == 0:
            # This case might be redundant if files_to_process was empty and handled above, 
            # but kept for safety if _read_files_content somehow processes 0 files from a non-empty list.
            if component and not specific_file_targeted:
                logger.info(f"Component file '{component}' was not found, and no markdown files could be read from '{knowledge_base_path}'.")
            elif not component:
                logger.info(f"No markdown files could be read from '{knowledge_base_path}'.")
        elif specific_file_targeted:
            if files_processed_count == 1: # Successfully read the one specific file
                logger.info(f"Successfully read specific component file: {files_to_process[0]}")
            else: # Error reading the specific file (already logged in _read_files_content)
                return "" # Return empty as per original logic for specific file read error
        else: # Reading all files (either by default or fallback)
            logger.info(f"Read {files_processed_count} markdown files from '{knowledge_base_path}'.")

        return all_markdown_content
