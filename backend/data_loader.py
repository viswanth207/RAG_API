import pandas as pd
import json
import requests
from typing import List, Dict, Any
from langchain_core.documents import Document
import logging
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from pymongo import MongoClient
import os

logger = logging.getLogger(__name__)


class DataLoader:
    
    @staticmethod
    def load_from_mongodb(collection_name: str = None, db_name: str = "vtfinal", mongo_url: str = None) -> List[Document]:
        try:
            if not mongo_url:
                mongo_url = os.getenv("MONGODB_URL", "mongodb://localhost:27017")
            
            logger.info(f"Connecting to MongoDB at {mongo_url}, database: {db_name}")
            client = MongoClient(mongo_url, serverSelectionTimeoutMS=5000)
            # Test connection
            client.admin.command('ping')
            logger.info("Successfully pinged MongoDB")
            db = client[db_name]
            
            if collection_name:
                collections_to_load = [collection_name]
            else:
                collections_to_load = db.list_collection_names()
                logger.info(f"Found collections in {db_name}: {collections_to_load}")
            
            documents = []
            
            for coll_name in collections_to_load:
                collection = db[coll_name]
                cursor = collection.find({})
                
                for idx, item in enumerate(cursor):
                    if '_id' in item:
                        item['_id'] = str(item['_id'])
                    
                    content = DataLoader._dict_to_content(item)
                    
                    # Make sure all metadata values are strings or primitives supported by FAISS
                    metadata = {
                        "source": f"mongodb:/{db_name}/{coll_name}",
                        "item_number": idx,
                        **DataLoader._flatten_dict(item)
                    }
                    
                    doc = Document(
                        page_content=content,
                        metadata=metadata
                    )
                    documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} documents from MongoDB {db_name}")
            return documents
            
        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error loading MongoDB: {error_msg}")
            
            if "10061" in error_msg or "Connection refused" in error_msg:
                detailed_msg = f"Network Connection Refused at {mongo_url}. Remote database is either offline or blocking access. (Error 10061)"
            elif "timeout" in error_msg.lower():
                detailed_msg = f"Connection Timeout at {mongo_url}. Check if the target IP is reachable and firewall is open (Port 27017)."
            else:
                detailed_msg = f"Failed to load data from MongoDB: {error_msg}"
                
            raise ValueError(detailed_msg)

    @staticmethod
    def load_from_postgres(connection_string: str, table_names: List[str] = None) -> List[Document]:
        try:
            import psycopg2
            from psycopg2.extras import RealDictCursor
        except ImportError:
            raise ImportError("psycopg2 is not installed. Please install it using `pip install psycopg2-binary`")
            
        try:
            logger.info(f"Connecting to PostgreSQL Database...")
            conn = psycopg2.connect(connection_string)
            cursor = conn.cursor(cursor_factory=RealDictCursor)
            
            if not table_names:
                # Fetch all public tables if no specific tables are requested
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                """)
                table_names = [row['table_name'] for row in cursor.fetchall()]
                logger.info(f"Automatically discovered tables: {table_names}")
                
            documents = []
            
            for table_name in table_names:
                cursor.execute(f"SELECT * FROM {table_name}")
                rows = cursor.fetchall()
                
                for idx, row in enumerate(rows):
                    row_dict = dict(row)
                    # Convert dates or uuids to strings safely
                    for k, v in row_dict.items():
                        row_dict[k] = str(v)

                    content = DataLoader._dict_to_content(row_dict)
                    
                    metadata = {
                        "source": f"postgresql:/{table_name}",
                        "item_number": idx,
                        **DataLoader._flatten_dict(row_dict)
                    }
                    
                    doc = Document(
                        page_content=content,
                        metadata=metadata
                    )
                    documents.append(doc)
            
            cursor.close()
            conn.close()
            
            logger.info(f"Loaded {len(documents)} documents from PostgreSQL")
            return documents

        except Exception as e:
            error_msg = str(e)
            logger.error(f"Error loading from PostgreSQL: {error_msg}")
            
            if "10061" in error_msg or "Connection refused" in error_msg:
                detailed_msg = f"PostgreSQL Connection Refused at your target IP. Ensure the database is running and the IP address is allowed in pg_hba.conf."
            elif "authentication failed" in error_msg.lower():
                detailed_msg = "PostgreSQL Identity/Password Mismatch. Ensure the username and password in your database_url are correct."
            else:
                detailed_msg = f"PostgreSQL protocol error: {error_msg}"
                
            raise ValueError(detailed_msg)
    
    @staticmethod
    def load_from_csv(file_path: str) -> List[Document]:
        try:
            df = pd.read_csv(file_path)
            documents = []
            
            for idx, row in df.iterrows():
                content_parts = []
                metadata = {"source": file_path, "row_number": idx}
                
                for column, value in row.items():
                    if pd.notna(value):
                        content_parts.append(f"{column}: {value}")
                        metadata[column] = str(value)
                
                content = " | ".join(content_parts)
                
                doc = Document(
                    page_content=content,
                    metadata=metadata
                )
                documents.append(doc)
            
            logger.info(f"Loaded {len(documents)} documents from CSV")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading CSV: {str(e)}")
            raise ValueError(f"Failed to load CSV file: {str(e)}")
    
    @staticmethod
    def load_from_json(file_path: str) -> List[Document]:
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            documents = []
            
            if isinstance(data, list):
                for idx, item in enumerate(data):
                    content = DataLoader._dict_to_content(item)
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": file_path,
                            "item_number": idx,
                            **DataLoader._flatten_dict(item)
                        }
                    )
                    documents.append(doc)
            
            elif isinstance(data, dict):
                content = DataLoader._dict_to_content(data)
                doc = Document(
                    page_content=content,
                    metadata={
                        "source": file_path,
                        **DataLoader._flatten_dict(data)
                    }
                )
                documents.append(doc)
            
            else:
                raise ValueError("JSON must be either an array or object")
            
            logger.info(f"Loaded {len(documents)} documents from JSON")
            return documents
            
        except Exception as e:
            logger.error(f"Error loading JSON: {str(e)}")
            raise ValueError(f"Failed to load JSON file: {str(e)}")
    
    @staticmethod
    def load_from_url(url: str) -> List[Document]:
        try:
            response = requests.get(url, timeout=30, headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
            })
            response.raise_for_status()
            
            content_type = response.headers.get('content-type', '').lower()
            
            if 'json' in content_type or url.endswith('.json'):
                try:
                    data = response.json()
                    documents = []
                    
                    if isinstance(data, list):
                        for idx, item in enumerate(data):
                            content = DataLoader._dict_to_content(item)
                            doc = Document(
                                page_content=content,
                                metadata={
                                    "source": url,
                                    "item_number": idx,
                                    **DataLoader._flatten_dict(item)
                                }
                            )
                            documents.append(doc)
                    elif isinstance(data, dict):
                        content = DataLoader._dict_to_content(data)
                        doc = Document(
                            page_content=content,
                            metadata={"source": url, **DataLoader._flatten_dict(data)}
                        )
                        documents.append(doc)
                    
                    logger.info(f"Loaded {len(documents)} documents from URL (JSON)")
                    return documents
                except json.JSONDecodeError:
                    pass
            
            if 'csv' in content_type or url.endswith('.csv'):
                from io import StringIO
                df = pd.read_csv(StringIO(response.text))
                documents = []
                
                for idx, row in df.iterrows():
                    content_parts = []
                    metadata = {"source": url, "row_number": idx}
                    
                    for column, value in row.items():
                        if pd.notna(value):
                            content_parts.append(f"{column}: {value}")
                            metadata[column] = str(value)
                    
                    content = " | ".join(content_parts)
                    doc = Document(page_content=content, metadata=metadata)
                    documents.append(doc)
                
                logger.info(f"Loaded {len(documents)} documents from URL (CSV)")
                return documents
            
            logger.info(f"Processing URL as HTML website: {url}")
            soup = BeautifulSoup(response.content, 'html.parser')
            
            for element in soup(["script", "style", "noscript", "iframe"]):
                element.decompose()
            
            title = soup.title.string if soup.title else urlparse(url).path
            
            # Extract main content
            main_content = soup.find('main') or soup.find('article') or soup.find('div', class_='content') or soup.body
            
            if main_content:
                documents = []
                seen_texts = set()  # Avoid duplicates
                chunk_number = 0
                
                # Strategy 1: Extract sections with headings
                for heading in main_content.find_all(['h1', 'h2', 'h3', 'h4', 'h5', 'h6']):
                    heading_text = heading.get_text(strip=True)
                    
                    # Skip very short headings but keep most
                    if not heading_text or len(heading_text) < 3:
                        continue
                    
                    # Normalize text to check duplicates
                    normalized_heading = ' '.join(heading_text.split())
                    if normalized_heading in seen_texts:
                        continue
                    
                    section_content = [heading_text]
                    seen_texts.add(normalized_heading)
                    
                    # Collect content until next heading (within reasonable limit)
                    content_count = 0
                    for sibling in heading.find_next_siblings():
                        if content_count >= 10:  # Limit to avoid too much content per section
                            break
                        if sibling.name and sibling.name.startswith('h'):  # Any heading
                            break
                        
                        if sibling.name in ['p', 'div', 'li', 'ul', 'ol', 'span']:
                            text = sibling.get_text(separator=' ', strip=True)
                            normalized_text = ' '.join(text.split())
                            
                            # Reduced minimum length to capture short descriptions like "Founder & CEO"
                            if normalized_text and len(normalized_text) > 5 and normalized_text not in seen_texts:
                                section_content.append(text)
                                seen_texts.add(normalized_text)
                                content_count += 1
                    
                    # Create document if there's content beyond just the heading (relaxed threshold)
                    full_content = '\n\n'.join(section_content)
                    if len(section_content) > 1 or len(full_content) > 20:
                        doc = Document(
                            page_content=full_content,
                            metadata={
                                "source": url,
                                "title": title,
                                "chunk": chunk_number,
                                "type": "website_section",
                                "heading": heading_text[:100]  # Truncate long headings in metadata
                            }
                        )
                        documents.append(doc)
                        chunk_number += 1
                
                for p in main_content.find_all('p'):
                    text = p.get_text(strip=True)
                    normalized_text = ' '.join(text.split())
                    
                    if normalized_text and len(normalized_text) > 50 and normalized_text not in seen_texts:
                        doc = Document(
                            page_content=text,
                            metadata={
                                "source": url,
                                "title": title,
                                "chunk": chunk_number,
                                "type": "website_paragraph"
                            }
                        )
                        documents.append(doc)
                        seen_texts.add(normalized_text)
                        chunk_number += 1
                
                if documents:
                    logger.info(f"Loaded {len(documents)} documents from website: {url}")
                    return documents
                else:
                    domain = urlparse(url).netloc.lower()
                    
                    if any(site in domain for site in ['youtube.com', 'facebook.com', 'twitter.com', 'instagram.com', 'tiktok.com']):
                        raise ValueError(
                            f"Cannot scrape {domain} - this site loads content dynamically with JavaScript. "
                            f"Web scraping works best with:\n"
                            f"- Blog posts and articles\n"
                            f"- Documentation sites\n"
                            f"- Company websites\n"
                            f"- News sites\n\n"
                            f"For {domain}, consider using their official API or providing structured data (CSV/JSON) instead."
                        )
                    else:
                        raise ValueError(
                            "Could not extract meaningful content from the website. "
                            "This may be because:\n"
                            "- The page loads content with JavaScript (try a different page)\n"
                            "- The page has no readable text content\n"
                            "- The content is behind a login/paywall\n\n"
                            "Try using a blog post, article, or documentation page instead."
                        )
            else:
                raise ValueError("Could not find main content in the webpage")
            
        except requests.RequestException as e:
            logger.error(f"Error fetching URL: {str(e)}")
            raise ValueError(f"Failed to fetch data from URL: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing URL data: {str(e)}")
            raise ValueError(f"Failed to process URL data: {str(e)}")
    
    @staticmethod
    def _dict_to_content(data: Dict[str, Any], prefix: str = "") -> str:
        parts = []
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                parts.append(DataLoader._dict_to_content(value, full_key))
            elif isinstance(value, list):
                parts.append(f"{full_key}: {', '.join(map(str, value))}")
            else:
                parts.append(f"{full_key}: {value}")
        
        return " | ".join(parts)
    
    @staticmethod
    def _flatten_dict(data: Dict[str, Any], prefix: str = "") -> Dict[str, str]:
        result = {}
        for key, value in data.items():
            full_key = f"{prefix}.{key}" if prefix else key
            
            if isinstance(value, dict):
                result.update(DataLoader._flatten_dict(value, full_key))
            elif isinstance(value, (list, tuple)):
                result[full_key] = str(value)
            else:
                result[full_key] = str(value)
        
        return result
