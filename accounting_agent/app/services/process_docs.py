
from fastapi import HTTPException, UploadFile
import os
import mimetypes  # Import the mimetypes module
import traceback
import uuid
from typing import List, Optional
from langchain_text_splitters import RecursiveCharacterTextSplitter


from langchain_community.document_loaders import (
    # CSVLoader,
    EverNoteLoader,
    PyMuPDFLoader,
    TextLoader,
    UnstructuredEPubLoader,
    UnstructuredHTMLLoader,
    UnstructuredMarkdownLoader,
    UnstructuredODTLoader,
    UnstructuredPowerPointLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_core.documents import Document
from app.dependencies import vectorstore


LOADER_MAPPING = {
    # ".csv": (CSVLoader, {}),
    ".doc": (UnstructuredWordDocumentLoader, {}),
    ".docx": (UnstructuredWordDocumentLoader, {}),
    ".enex": (EverNoteLoader, {}),
    ".epub": (UnstructuredEPubLoader, {}),
    ".html": (UnstructuredHTMLLoader, {}),
    ".md": (UnstructuredMarkdownLoader, {}),
    ".odt": (UnstructuredODTLoader, {}),
    ".pdf": (PyMuPDFLoader, {}),
    ".ppt": (UnstructuredPowerPointLoader, {}),
    ".pptx": (UnstructuredPowerPointLoader, {}),
    ".txt": (TextLoader, {"encoding": "utf8"}),
}

SUPPORTED_MIME_TYPES = [
    # "text/csv",
    "application/msword",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/enex+xml",  # Assuming this is the correct MIME type for ENEX
    "application/epub+zip",
    "text/html",
    "text/markdown",
    "application/vnd.oasis.opendocument.text",
    "application/pdf",
    "application/vnd.ms-powerpoint",
    "application/vnd.openxmlformats-officedocument.presentationml.presentation",
    "text/plain",
]


def split_text(documents: list[Document]):
    """
    Split the text content of the given list of Document objects into smaller chunks.
    Args:
    documents (list[Document]): List of Document objects containing text content to split.
    Returns:
    list[Document]: List of Document objects representing the split text chunks.
    """
    # Initialize text splitter with specified parameters
    text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300, # Size of each chunk in characters
    chunk_overlap=100, # Overlap between consecutive chunks
    length_function=len, # Function to compute the length of the text
    add_start_index=True, # Flag to add start index to each chunk
    )

    # Split documents into smaller chunks using text splitter
    chunks = text_splitter.split_documents(documents)
    # print(f"Split {len(documents)} documents into {len(chunks)} chunks.")

    # Print example of page content and metadata for a chunk
    # document = chunks[0]
    # print(document.page_content)
    # print(document.metadata)

    return chunks # Return the list of split text chunks

async def process_documents(files: List[UploadFile], conversation_id: str):
    """Processes uploaded documents and adds them to the vectorstore."""

    messages = []
    try:
        for file in files:
            mime_type = mimetypes.guess_type(file.filename)[0]
            if mime_type not in SUPPORTED_MIME_TYPES:
                raise HTTPException(
                    status_code=400,
                    detail=f"Unsupported file type: {file.filename} (MIME type: {mime_type})",
                )

            file_extension = os.path.splitext(file.filename)[1]
            loader_class, loader_args = LOADER_MAPPING.get(file_extension, (None, None))
            if loader_class:
                # Save the file temporarily
                file_path = f"temp_files/{file.filename}"  # Create a temp_files directory
                os.makedirs("temp_files", exist_ok=True)  # Ensure the directory exists
                with open(file_path, "wb") as f:
                    f.write(await file.read())

                loader = loader_class(file_path, **loader_args)
                documents = loader.load()
                documents = split_text(documents)  # Split the text content of the documents

                # Add metadata and conversation_id
                for doc in documents:
                    doc.metadata["source"] = file.filename
                    doc.metadata["conversation_id"] = conversation_id

                # Generate UUIDs for the documents
                ids = [str(uuid.uuid4()) for _ in documents]

                vectorstore.add_documents(documents=documents, ids=ids)

                messages.append(f"System: User uploaded document '{file.filename}'. This document is now available for answering relevant questions. You may use the vectorstore_retrieval tool to access the document.")
                # Clean up the temporary file
                os.remove(file_path)
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported file type: {file_extension}")

        return messages

    except Exception as e:
        print(f"Error processing documents: {e}\n{traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=f"Document processing error: {e}")
