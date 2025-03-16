import os
import logging
from typing import List, Dict, Any, Optional
from dotenv import load_dotenv
from datetime import datetime, timedelta

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
                
            # Create connection pool with smaller pool size and timeouts
            self.connection_config = {
                'user': username,
                'password': password,
                'host': host,
                'port': port,
                'database': database,
                'pool_name': 'mypool',
                'pool_size': 5,  # Reduced from 10 to 5
                'pool_reset_session': True,
                'connect_timeout': 10,  # Add connection timeout
                'autocommit': True
            }
            
            self.connection_pool = self.pooling.MySQLConnectionPool(**self.connection_config)
            logger.info("MySQL database service initialized with connection pool (size: 5)")
            
        except Exception as e:
            logger.error(f"Error parsing connection string or creating pool: {str(e)}")
            raise

    def get_connection(self):
        """Get a connection from the pool."""
        try:
            return self.connection_pool.get_connection()
        except Exception as e:
            logger.error(f"Error getting connection from pool: {str(e)}")
            raise
    
    def release_connection(self, conn):
        """Release a connection back to the pool."""
        try:
            if conn and hasattr(conn, 'is_connected') and conn.is_connected():
                conn.close()
                logger.debug("Connection released back to pool")
        except Exception as e:
            logger.error(f"Error releasing connection: {str(e)}")
    
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
                try:
                    conn.rollback()
                except:
                    pass
            logger.error(f"Error saving URLs to database: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "saved_count": 0
            }
        finally:
            if conn:
                self.release_connection(conn)

    def get_urls_by_category(self, category: str, site_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Retrieve a specific number of URLs filtered by website category and site ID.
        
        Args:
            category: The website category to filter by
            site_id: The site ID to filter by
            limit: Maximum number of URLs to return
            
        Returns:
            List of URL dictionaries
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
            
            cursor.execute(
                """
                SELECT id, url, site_id, website_category, created_at 
                FROM outreach_urls 
                WHERE website_category = %s AND site_id = %s
                ORDER BY id ASC
                LIMIT %s
                """,
                (category, site_id, limit)
            )
            
            results = cursor.fetchall()
            urls = []
            
            for row in results:
                # Convert datetime to string if needed
                if 'created_at' in row and row['created_at']:
                    row['created_at'] = row['created_at'].isoformat()
                urls.append(row)
            
            logger.info(f"Retrieved {len(urls)} URLs for category '{category}' and site ID {site_id}")
            return urls
            
        except Exception as e:
            logger.error(f"Error retrieving URLs by category and site: {str(e)}")
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

    def delete_urls_by_site_id(self, site_id: int) -> Dict[str, Any]:
        """
        Delete all prospect URLs associated with a specific site ID.
        
        Args:
            site_id: The ID of the site whose prospect URLs should be deleted
            
        Returns:
            Dictionary containing the result of the operation, including the count of deleted URLs
        """
        conn = None
        try:
            # Connect to the database
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Execute the DELETE query
            cursor.execute(
                "DELETE FROM outreach_urls WHERE site_id = %s",
                (site_id,)
            )
            
            # Get the number of rows deleted
            deleted_count = cursor.rowcount
            
            # Commit the transaction
            conn.commit()
            
            # Close the cursor (but not the connection yet)
            cursor.close()
            
            return {
                "success": True,
                "deleted_count": deleted_count,
                "message": f"Successfully deleted {deleted_count} prospect URLs for site ID {site_id}"
            }
            
        except Exception as e:
            # Log the error
            logger.error(f"Error deleting prospect URLs for site ID {site_id}: {str(e)}")
            
            # Try to rollback if possible
            if conn:
                try:
                    conn.rollback()
                except:
                    pass
            
            return {
                "success": False,
                "deleted_count": 0,
                "message": f"Failed to delete prospect URLs: {str(e)}"
            }
        finally:
            # Always release the connection back to the pool
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
            List of URL dictionaries containing id, url, site_id, created_at, and website_category
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Get the top URLs for the specified site based on ID (oldest first)
            cursor.execute(
                """
                SELECT id, url, site_id, created_at, website_category
                FROM outreach_urls
                WHERE site_id = %s
                ORDER BY id ASC
                LIMIT %s
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
                url_ids.append(row['id'])
                
                # Convert datetime to string if needed
                if 'created_at' in row and row['created_at']:
                    row['created_at'] = row['created_at'].isoformat()
                
                prospects.append(row)
            
            # For each URL we're returning, we need to:
            # 1. Create a copy at the end of the list
            # 2. Delete the original entry
            
            for url_id in url_ids:
                # Get the original record
                cursor.execute(
                    """
                    SELECT url, site_id, website_category
                    FROM outreach_urls
                    WHERE id = %s
                    """,
                    (url_id,)
                )
                original = cursor.fetchone()
                
                if original:
                    # Insert a new copy at the end
                    cursor.execute(
                        """
                        INSERT INTO outreach_urls (url, site_id, website_category)
                        VALUES (%s, %s, %s)
                        """,
                        (original['url'], original['site_id'], original['website_category'])
                    )
                    
                    # Delete the original
                    cursor.execute(
                        """
                        DELETE FROM outreach_urls
                        WHERE id = %s
                        """,
                        (url_id,)
                    )
            
            conn.commit()
            return prospects
            
        except Exception as e:
            if conn:
                conn.rollback()
            logger.error(f"Error retrieving URLs from database: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)

    def has_outreach_prospects(self, site_id):
        """
        Check if there are any outreach prospects for the given site_id
        
        Args:
            site_id (int): The site ID to check
            
        Returns:
            bool: True if there are prospects, False otherwise
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            query = "SELECT COUNT(*) FROM outreach_urls WHERE site_id = %s"
            cursor.execute(query, (site_id,))
            
            count = cursor.fetchone()[0]
            
            return count > 0
        except Exception as e:
            logger.error(f"Error checking outreach prospects: {str(e)}")
            return False
        finally:
            if conn:
                self.release_connection(conn)

    def add_email_tracking(self, 
                          email_id: str, 
                          recipient: str, 
                          subject: str, 
                          status: str = "pending",
                          site_id: Optional[int] = None):
        """
        Add a new email to the tracking database.
        
        Args:
            email_id: Unique identifier for the email
            recipient: Recipient email address
            subject: Email subject
            status: Initial status (default: pending)
            site_id: Optional site ID for tracking purposes
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            cursor.execute(
                "INSERT INTO email_tracking (email_id, recipient, subject, sent_at, status, updated_at, site_id) VALUES (%s, %s, %s, %s, %s, %s, %s)",
                (email_id, recipient, subject, now, status, now, site_id)
            )
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error adding email tracking record: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def update_email_status(self, 
                           email_id: str, 
                           status: str, 
                           bounce_reason: Optional[str] = None):
        """
        Update the status of an email in the tracking database.
        
        Args:
            email_id: Unique identifier for the email
            status: New status (e.g., delivered, bounced, replied)
            bounce_reason: Reason for bounce (if applicable)
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            
            # If status is 'replied', also update reply_received_at
            if status == 'replied':
                cursor.execute(
                    "UPDATE email_tracking SET status = %s, updated_at = %s, reply_received_at = %s, bounce_reason = %s WHERE email_id = %s",
                    (status, now, now, bounce_reason, email_id)
                )
            else:
                cursor.execute(
                    "UPDATE email_tracking SET status = %s, updated_at = %s, bounce_reason = %s WHERE email_id = %s",
                    (status, now, bounce_reason, email_id)
                )
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error updating email status: {str(e)}")
            if conn:
                conn.rollback()
            raise
        finally:
            if conn:
                self.release_connection(conn)

    def get_recent_emails(self, site_id: Optional[int] = None, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get the most recent emails from the tracking database.
        
        Args:
            site_id: Optional site ID to filter by
            limit: Maximum number of emails to return
            
        Returns:
            List of dictionaries containing email tracking data
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
            
            if site_id is not None:
                # Filter by site_id
                cursor.execute(
                    "SELECT email_id, recipient, subject, sent_at, status, updated_at, reply_received_at, bounce_reason, site_id FROM email_tracking WHERE site_id = %s ORDER BY sent_at DESC LIMIT %s",
                    (site_id, limit)
                )
            else:
                # Get all emails
                cursor.execute(
                    "SELECT email_id, recipient, subject, sent_at, status, updated_at, reply_received_at, bounce_reason, site_id FROM email_tracking ORDER BY sent_at DESC LIMIT %s",
                    (limit,)
                )
            
            results = cursor.fetchall()
            emails = []
            
            for row in results:
                # Convert datetime objects to strings if needed
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                emails.append(row)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error retrieving recent emails: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)

    def get_email_stats(self, site_id: Optional[int] = None, days: int = 7) -> Dict[str, Any]:
        """
        Get email statistics for the specified number of days.
        
        Args:
            site_id: Optional site ID to filter by
            days: Number of days to include in the statistics
            
        Returns:
            Dictionary containing email statistics
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Calculate the date range
            end_date = datetime.now()
            start_date = end_date - timedelta(days=days)
            
            # Prepare the site_id filter condition
            site_filter = "AND site_id = %s" if site_id is not None else ""
            site_params = (site_id,) if site_id is not None else ()
            
            # Get daily stats for each day in the range
            daily_stats = []
            
            for i in range(days):
                day_date = end_date - timedelta(days=i)
                day_start = day_date.replace(hour=0, minute=0, second=0).strftime('%Y-%m-%d %H:%M:%S')
                day_end = day_date.replace(hour=23, minute=59, second=59).strftime('%Y-%m-%d %H:%M:%S')
                
                # Count sent emails for this day
                if site_id is not None:
                    cursor.execute(
                        f"SELECT COUNT(*) as sent FROM email_tracking WHERE sent_at BETWEEN %s AND %s {site_filter}",
                        (day_start, day_end) + site_params
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) as sent FROM email_tracking WHERE sent_at BETWEEN %s AND %s",
                        (day_start, day_end)
                    )
                sent_result = cursor.fetchone()
                sent = sent_result['sent'] if sent_result else 0
                
                # Count delivered emails for this day
                if site_id is not None:
                    cursor.execute(
                        f"SELECT COUNT(*) as delivered FROM email_tracking WHERE status = 'delivered' AND sent_at BETWEEN %s AND %s {site_filter}",
                        (day_start, day_end) + site_params
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) as delivered FROM email_tracking WHERE status = 'delivered' AND sent_at BETWEEN %s AND %s",
                        (day_start, day_end)
                    )
                delivered_result = cursor.fetchone()
                delivered = delivered_result['delivered'] if delivered_result else 0
                
                # Count replied emails for this day
                if site_id is not None:
                    cursor.execute(
                        f"SELECT COUNT(*) as replied FROM email_tracking WHERE status = 'replied' AND sent_at BETWEEN %s AND %s {site_filter}",
                        (day_start, day_end) + site_params
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) as replied FROM email_tracking WHERE status = 'replied' AND sent_at BETWEEN %s AND %s",
                        (day_start, day_end)
                    )
                replied_result = cursor.fetchone()
                replied = replied_result['replied'] if replied_result else 0
                
                # Count bounced emails for this day
                if site_id is not None:
                    cursor.execute(
                        f"SELECT COUNT(*) as bounced FROM email_tracking WHERE status = 'bounced' AND sent_at BETWEEN %s AND %s {site_filter}",
                        (day_start, day_end) + site_params
                    )
                else:
                    cursor.execute(
                        "SELECT COUNT(*) as bounced FROM email_tracking WHERE status = 'bounced' AND sent_at BETWEEN %s AND %s",
                        (day_start, day_end)
                    )
                bounced_result = cursor.fetchone()
                bounced = bounced_result['bounced'] if bounced_result else 0
                
                # Calculate rates
                daily_reply_rate = (replied / delivered * 100) if delivered > 0 else 0
                daily_bounce_rate = (bounced / sent * 100) if sent > 0 else 0
                
                daily_stats.append({
                    'date': day_date.strftime('%Y-%m-%d'),
                    'sent': sent,
                    'delivered': delivered,
                    'replied': replied,
                    'bounced': bounced,
                    'reply_rate': daily_reply_rate,
                    'bounce_rate': daily_bounce_rate
                })
            
            # Reverse the list so it's in chronological order
            daily_stats.reverse()
            
            # Get overall totals
            if site_id is not None:
                cursor.execute(f"SELECT COUNT(*) as total FROM email_tracking WHERE site_id = %s", (site_id,))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM email_tracking")
            total_sent_result = cursor.fetchone()
            total_sent = total_sent_result['total'] if total_sent_result else 0
            
            if site_id is not None:
                cursor.execute(f"SELECT COUNT(*) as total FROM email_tracking WHERE status = 'delivered' AND site_id = %s", (site_id,))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM email_tracking WHERE status = 'delivered'")
            total_delivered_result = cursor.fetchone()
            total_delivered = total_delivered_result['total'] if total_delivered_result else 0
            
            if site_id is not None:
                cursor.execute(f"SELECT COUNT(*) as total FROM email_tracking WHERE status = 'replied' AND site_id = %s", (site_id,))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM email_tracking WHERE status = 'replied'")
            total_replied_result = cursor.fetchone()
            total_replied = total_replied_result['total'] if total_replied_result else 0
            
            if site_id is not None:
                cursor.execute(f"SELECT COUNT(*) as total FROM email_tracking WHERE status = 'bounced' AND site_id = %s", (site_id,))
            else:
                cursor.execute("SELECT COUNT(*) as total FROM email_tracking WHERE status = 'bounced'")
            total_bounced_result = cursor.fetchone()
            total_bounced = total_bounced_result['total'] if total_bounced_result else 0
            
            # Calculate overall rates
            reply_rate = (total_replied / total_delivered * 100) if total_delivered > 0 else 0
            bounce_rate = (total_bounced / total_sent * 100) if total_sent > 0 else 0
            
            return {
                'daily_stats': daily_stats,
                'total_sent': total_sent,
                'total_delivered': total_delivered,
                'total_replied': total_replied,
                'total_bounced': total_bounced,
                'reply_rate': reply_rate,
                'bounce_rate': bounce_rate
            }
            
        except Exception as e:
            logger.error(f"Error retrieving email statistics: {str(e)}")
            return {
                'daily_stats': [],
                'total_sent': 0,
                'total_delivered': 0,
                'total_replied': 0,
                'total_bounced': 0,
                'reply_rate': 0,
                'bounce_rate': 0
            }
        finally:
            if conn:
                self.release_connection(conn)

    def get_all_email_tracking(self, site_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Get all records from the email_tracking table.
        
        Args:
            site_id: Optional site ID to filter by
            
        Returns:
            List of dictionaries containing all email tracking data
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)  # Return results as dictionaries
            
            if site_id is not None:
                # Filter by site_id
                cursor.execute(
                    """
                    SELECT email_id, recipient, subject, sent_at, status, updated_at, 
                           reply_received_at, bounce_reason, site_id 
                    FROM email_tracking 
                    WHERE site_id = %s 
                    ORDER BY sent_at DESC
                    """,
                    (site_id,)
                )
            else:
                # Get all emails
                cursor.execute(
                    """
                    SELECT email_id, recipient, subject, sent_at, status, updated_at, 
                           reply_received_at, bounce_reason, site_id 
                    FROM email_tracking 
                    ORDER BY sent_at DESC
                    """
                )
            
            results = cursor.fetchall()
            emails = []
            
            for row in results:
                # Convert datetime objects to strings if needed
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.strftime('%Y-%m-%d %H:%M:%S')
                emails.append(row)
            
            return emails
            
        except Exception as e:
            logger.error(f"Error retrieving all email tracking data: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)

    def find_recent_emails_by_recipient(self, recipient, site_id=None):
        """
        Find recent emails sent to a specific recipient, optionally filtered by site_id
        Returns emails ordered by most recent first
        
        Args:
            recipient: Email address of the recipient
            site_id: Optional site ID to filter by
            
        Returns:
            List of email records or empty list if none found
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor(dictionary=True)
            
            if site_id is not None:
                # Filter by both recipient and site_id
                query = """
                SELECT * FROM email_tracking 
                WHERE recipient = %s AND site_id = %s
                ORDER BY sent_at DESC
                LIMIT 5
                """
                cursor.execute(query, (recipient, site_id))
            else:
                # Filter by recipient only
                query = """
                SELECT * FROM email_tracking 
                WHERE recipient = %s
                ORDER BY sent_at DESC
                LIMIT 5
                """
                cursor.execute(query, (recipient,))
            
            results = cursor.fetchall()
            
            # Convert datetime objects to strings
            for row in results:
                for key, value in row.items():
                    if isinstance(value, datetime):
                        row[key] = value.strftime('%Y-%m-%d %H:%M:%S')
            
            logger.info(f"Found {len(results)} recent emails sent to {recipient}")
            return results
            
        except Exception as e:
            logger.error(f"Database error finding emails by recipient: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)

    def get_all_website_categories(self) -> List[str]:
        """
        Retrieve all unique website categories from the outreach_urls table.
        
        Returns:
            List of unique website category strings
        """
        conn = None
        try:
            conn = self.get_connection()
            cursor = conn.cursor()
            
            # Query to get distinct website categories, excluding NULL values
            cursor.execute(
                "SELECT DISTINCT website_category FROM outreach_urls WHERE website_category IS NOT NULL"
            )
            
            # Fetch all results and extract the category strings
            results = cursor.fetchall()
            categories = [row[0] for row in results]
            
            logger.info(f"Retrieved {len(categories)} unique website categories")
            return categories
            
        except Exception as e:
            logger.error(f"Error retrieving website categories: {str(e)}")
            return []
        finally:
            if conn:
                self.release_connection(conn)

# Example usage
if __name__ == "__main__":
    # Set up basic logging
    logging.basicConfig(level=logging.INFO, 
                        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    
    # Create database service using the environment variable
    db_service = DatabaseService()  # Will use os.environ.get("DATABASE_URL")
    
    import uuid
    from datetime import datetime, timedelta
    
    print("\n===== TESTING EMAIL TRACKING METHODS =====\n")
    
    # 1. Test adding an email to tracking
    print("1. ADDING TEST EMAIL TO TRACKING")
    print("-" * 50)
    
    email_id = str(uuid.uuid4())
    recipient = "test@example.com"
    subject = "Test Email " + datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    print(f"Adding email with ID: {email_id}")
    print(f"Recipient: {recipient}")
    print(f"Subject: {subject}")
    
    db_service.add_email_tracking(
        email_id=email_id,
        recipient=recipient,
        subject=subject,
        status="pending"
    )
    print("✓ Email added to tracking database")
    print()
    
    # 2. Test updating email status
    print("2. UPDATING EMAIL STATUS")
    print("-" * 50)
    
    # Update the email we just added
    new_status = "delivered"
    print(f"Updating email {email_id} to status: {new_status}")
    
    db_service.update_email_status(
        email_id=email_id,
        status=new_status
    )
    print("✓ Email status updated")
    
    # Update to replied status
    new_status = "replied"
    print(f"Updating email {email_id} to status: {new_status}")
    
    db_service.update_email_status(
        email_id=email_id,
        status=new_status
    )
    print("✓ Email status updated to replied")
    print()
    
    # 3. Test getting recent emails
    print("3. RETRIEVING RECENT EMAILS")
    print("-" * 50)
    
    emails = db_service.get_recent_emails(site_id=2, limit=5)
    
    print(f"Retrieved {len(emails)} recent emails:")
    print("-" * 80)
    print(f"{'Email ID':<36} | {'Recipient':<20} | {'Subject':<25} | {'Status':<10} | {'Sent At'}")
    print("-" * 80)
    
    for email in emails:
        email_id_display = email['email_id']
        recipient = email['recipient'][:17] + "..." if len(email['recipient']) > 20 else email['recipient']
        subject = email['subject'][:22] + "..." if len(email['subject']) > 25 else email['subject']
        status = email['status']
        sent_at = email['sent_at']
        
        print(f"{email_id_display} | {recipient:<20} | {subject:<25} | {status:<10} | {sent_at}")
    print()
    
    # 4. Test getting email statistics
    print("4. GENERATING EMAIL STATISTICS")
    print("-" * 50)
    
    # Get stats for the last 7 days
    stats = db_service.get_email_stats(site_id=2, days=7)
    
    print("Email Statistics Summary:")
    print(f"Total Sent: {stats['total_sent']}")
    print(f"Total Delivered: {stats['total_delivered']}")
    print(f"Total Replied: {stats['total_replied']}")
    print(f"Total Bounced: {stats['total_bounced']}")
    print(f"Cumulative Reply Rate: {stats['reply_rate']:.2f}%")
    print(f"Cumulative Bounce Rate: {stats['bounce_rate']:.2f}%")
    
    print("\nDaily Statistics:")
    print("-" * 60)
    print(f"{'Date':<12} | {'Sent':<6} | {'Delivered':<10} | {'Replied':<8} | {'Bounced':<8} | {'Reply Rate'} | {'Bounce Rate'}")
    print("-" * 60)
    
    for day in stats['daily_stats']:
        date = day['date']
        sent = day['sent']
        delivered = day['delivered']
        replied = day['replied']
        bounced = day['bounced']
        reply_rate = (replied / delivered * 100) if delivered > 0 else 0
        bounce_rate = (bounced / sent * 100) if sent > 0 else 0
        
        print(f"{date:<12} | {sent:<6} | {delivered:<10} | {replied:<8} | {bounced:<8} | {reply_rate:.2f}% | {bounce_rate:.2f}%")
    print()
    
    # 5. Test existing outreach prospects functionality
    print("5. CHECKING OUTREACH PROSPECTS")
    print("-" * 50)
    
    site_id = 2  # Using a default site ID
    has_prospects = db_service.has_outreach_prospects(site_id)
    print(f"Site ID {site_id} has outreach prospects: {has_prospects}")
    print()
    
    # Close connections when done
    db_service.close()
    print("✓ Database connections closed")
    print("\n===== ALL TESTS COMPLETED =====") 