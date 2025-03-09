import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)

# Load .env file with explicit path
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.env')
print(f"Looking for .env file at: {dotenv_path}")
load_dotenv(dotenv_path)

# Debug: Print all environment variables to check if DATABASE_URL exists
print("Environment variables:")
print(f"DATABASE_URL exists: {'DATABASE_URL' in os.environ}")
if 'DATABASE_URL' in os.environ:
    # Print first few characters to avoid exposing full credentials
    db_url = os.environ.get('DATABASE_URL')
    print(f"DATABASE_URL value starts with: {db_url[:15]}...")

class DatabaseService:
    """Service for handling database operations related to outreach URLs."""
    
    def __init__(self, connection_string: Optional[str] = None):
        """
        Initialize the DatabaseService with a connection to the database.
        
        Args:
            connection_string: MySQL connection string. If None, will use environment variable.
        """
        try:
            import mysql.connector
            from mysql.connector import pooling
            self.mysql = mysql.connector
            self.pooling = pooling
        except ImportError:
            logger.error("mysql-connector-python is not installed. Please install it with: pip install mysql-connector-python")
            raise ImportError("mysql-connector-python is required. Install with: pip install mysql-connector-python")
            
        self.connection_string = connection_string or os.environ.get("DATABASE_URL")
        
        if not self.connection_string:
            raise ValueError("Database connection string not provided and DATABASE_URL environment variable not set")
        
        # Parse connection string to get connection parameters
        # Format expected: mysql://username:password@host:port/database
        try:
            # Remove mysql:// prefix if present
            if self.connection_string.startswith("mysql://"):
                conn_str = self.connection_string[8:]
            else:
                conn_str = self.connection_string
                
            # Parse the connection string
            auth, rest = conn_str.split('@')
            username, password = auth.split(':')
            host_port, database = rest.split('/')
            
            if ':' in host_port:
                host, port = host_port.split(':')
                port = int(port)
            else:
                host = host_port
                port = 3306  # Default MySQL port
                
            # Create connection pool
            self.connection_config = {
                'user': username,
                'password': password,
                'host': host,
                'port': port,
                'database': database,
                'pool_name': 'mypool',
                'pool_size': 10
            }
            
            self.connection_pool = self.pooling.MySQLConnectionPool(**self.connection_config)
            logger.info("MySQL database service initialized with connection pool")
            
        except Exception as e:
            logger.error(f"Error parsing connection string or creating pool: {str(e)}")
            raise
    
    def get_connection(self):
        """Get a connection from the pool."""
        return self.connection_pool.get_connection()
    
    def release_connection(self, conn):
        """Release a connection back to the pool."""
        conn.close()
    
    def save_urls(self, urls: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Save a list of URLs to the outreach_urls table.
        
        Args:
            urls: List of dictionaries containing url, site_id, and website_category
                 Example: [{"url": "https://example.com", "site_id": 1, "website_category": "Tech Blog"}]
        
        Returns:
            Dictionary with status and count of saved URLs
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Insert each URL into the database
            saved_count = 0
            skipped_count = 0
            
            for url_data in urls:
                url = url_data.get("url")
                site_id = url_data.get("site_id")
                website_category = url_data.get("website_category")
                
                # Skip if URL is missing
                if not url:
                    logger.warning("Skipping record with missing URL")
                    skipped_count += 1
                    continue
                
                # Check if URL already exists to avoid duplicates
                cursor.execute("SELECT id FROM outreach_urls WHERE url = %s", (url,))
                existing = cursor.fetchone()
                
                if existing:
                    logger.info(f"URL already exists in database: {url}")
                    skipped_count += 1
                    continue
                
                # Insert the new URL
                cursor.execute(
                    "INSERT INTO outreach_urls (url, site_id, website_category) VALUES (%s, %s, %s)",
                    (url, site_id, website_category)
                )
                
                # Get the last inserted ID
                cursor.execute("SELECT LAST_INSERT_ID()")
                new_id = cursor.fetchone()[0]
                logger.info(f"Saved URL with ID {new_id}: {url}")
                saved_count += 1
            
            # Commit the transaction
            conn.commit()
            
            return {
                "status": "success",
                "saved_count": saved_count,
                "skipped_count": skipped_count,
                "total_processed": saved_count + skipped_count
            }
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error saving URLs to database: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "saved_count": 0
            }
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_urls_by_category(self, category: str) -> List[Dict[str, Any]]:
        """
        Retrieve URLs filtered by website category.
        
        Args:
            category: The website category to filter by
            
        Returns:
            List of URL dictionaries
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
            
            cursor.execute(
                "SELECT id, url, site_id, website_category, created_at FROM outreach_urls WHERE website_category = %s",
                (category,)
            )
            
            results = cursor.fetchall()
            urls = []
            
            for row in results:
                # Convert datetime to string if needed
                if 'created_at' in row and row['created_at']:
                    row['created_at'] = row['created_at'].isoformat()
                urls.append(row)
            
            return urls
            
        except Exception as e:
            logger.error(f"Error retrieving URLs by category: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)
    
    def get_all_urls(self) -> List[Dict[str, Any]]:
        """
        Retrieve all URLs from the database.
        
        Returns:
            List of URL dictionaries
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
            
            cursor.execute(
                "SELECT id, url, site_id, website_category, created_at FROM outreach_urls ORDER BY created_at DESC"
            )
            
            results = cursor.fetchall()
            urls = []
            
            for row in results:
                # Convert datetime to string if needed
                if 'created_at' in row and row['created_at']:
                    row['created_at'] = row['created_at'].isoformat()
                urls.append(row)
            
            return urls
            
        except Exception as e:
            logger.error(f"Error retrieving all URLs: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)
    
    def close(self):
        """Close the connection pool when done."""
        logger.info("Database connections closed")

    def get_founder_name(self, site_id: int) -> str:
        """
        Get the founder name from the personas table for a given site ID.
        
        Args:
            site_id: The site ID to get the founder name for
            
        Returns:
            The founder name as a string
            
        Raises:
            ValueError: If no founder is found for the given site ID
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Query the personas table to get the name for the given site_id
            cursor.execute(
                "SELECT name FROM personas WHERE site_id = %s AND role = 'founder' LIMIT 1",
                (site_id,)
            )
            
            result = cursor.fetchone()
            
            if result and 'name' in result:
                logger.info(f"Found founder name for site ID {site_id}: {result['name']}")
                return result['name']
            else:
                # If no founder role is found, try to get any persona for the site
                cursor.execute(
                    "SELECT name FROM personas WHERE site_id = %s LIMIT 1",
                    (site_id,)
                )
                
                result = cursor.fetchone()
                
                if result and 'name' in result:
                    logger.info(f"No founder found, using persona name for site ID {site_id}: {result['name']}")
                    return result['name']
                else:
                    logger.error(f"No personas found for site ID {site_id}")
                    raise ValueError(f"No personas found for site ID {site_id}")
                
        except Exception as e:
            logger.error(f"Error retrieving founder name: {str(e)}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def get_blog_info(self, site_id: int) -> Dict[str, Any]:
        """
        Get blog information from the blog_info table for a given site ID.
        
        Args:
            site_id: The site ID to get blog information for
            
        Returns:
            Dictionary containing blog information (topic, description, url, blog_name)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Query the blog_info table to get information for the given site_id
            cursor.execute(
                "SELECT topic, description, url, blog_name FROM blog_info WHERE site_id = %s LIMIT 1",
                (site_id,)
            )
            
            result = cursor.fetchone()
            
            if result:
                logger.info(f"Found blog info for site ID {site_id}: {result['topic']}")
                return result
            else:
                logger.warning(f"No blog info found for site ID {site_id}")
                raise ValueError(f"No blog info found for site ID {site_id}")
                
        except Exception as e:
            logger.error(f"Error retrieving blog info: {str(e)}")
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def pop_next_urls(self, max_count: int, site_id: int) -> List[Dict[str, Any]]:
        """
        Retrieve the top URLs from the outreach list for a specific site,
        move them to the back of the list, and return them.
        
        Args:
            max_count: Maximum number of URLs to retrieve
            site_id: ID of the site to get URLs for
            
        Returns:
            List of URL dictionaries containing at least 'url' and 'email' keys
        """
        # Get connection to database
        conn = self.get_connection()
        cursor = conn.cursor()
        
        try:
            # Get the top URLs for the specified site based on ID (oldest first)
            cursor.execute(
                """
                SELECT id, url, site_id, created_at, website_category
                FROM outreach_urls
                WHERE site_id = ?
                ORDER BY id ASC
                LIMIT ?
                """,
                (site_id, max_count)
            )
            
            # Fetch results
            results = cursor.fetchall()
            
            if not results:
                return []
            
            # Convert to list of dictionaries
            url_ids = []
            prospects = []
            
            for row in results:
                url_id, url, site_id, created_at, website_category = row
                url_ids.append(url_id)
                
                prospect = {
                    "id": url_id,
                    "url": url,
                    "site_id": site_id,
                    "created_at": created_at,
                    "website_category": website_category
                }
                prospects.append(prospect)
            
            # For each URL we're returning, we need to:
            # 1. Create a copy at the end of the list
            # 2. Delete the original entry
            
            for url_id in url_ids:
                # Get the original record
                cursor.execute(
                    """
                    SELECT url, site_id, website_category
                    FROM outreach_urls
                    WHERE id = ?
                    """,
                    (url_id,)
                )
                original = cursor.fetchone()
                
                if original:
                    url, site_id, website_category = original
                    
                    # Insert a new copy at the end
                    cursor.execute(
                        """
                        INSERT INTO outreach_urls (url, site_id, website_category)
                        VALUES (?, ?, ?)
                        """,
                        (url, site_id, website_category)
                    )
                    
                    # Delete the original
                    cursor.execute(
                        """
                        DELETE FROM outreach_urls
                        WHERE id = ?
                        """,
                        (url_id,)
                    )
            
            conn.commit()
            return prospects
            
        except Exception as e:
            logger.error(f"Error retrieving URLs from database: {str(e)}")
            conn.rollback()
            return []
        finally:
            cursor.close()
            conn.close()

# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create database service using the environment variable
    db_service = DatabaseService()  # Will use os.environ.get("DATABASE_URL")
    
    # Test get_founder_name with site IDs 1, 2, and 3
    print("\nTesting get_founder_name:")
    try:
        for site_id in [1, 2, 3]:
            try:
                founder_name = db_service.get_founder_name(site_id)
                print(f"Site ID {site_id} founder: {founder_name}")
            except ValueError as e:
                print(f"Site ID {site_id}: {str(e)}")
    except Exception as e:
        print(f"Error testing get_founder_name: {str(e)}")
    
    # Close connections when done
    db_service.close() 