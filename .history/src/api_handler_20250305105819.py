import sys
import os
import asyncio

# Add the project root directory to Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Update imports to use the new path
from src.blog_writer.services.content_generator import ContentGenerator
from src.blog_writer.services.media_service import PostWriterV2
from src.blog_writer.services.linking_service import LinkingAgent

class ContentAPIHandler:
    def __init__(self):
        self.blog_generator = ContentGenerator()
        self.internal_linker = LinkingAgent()

    async def generate_complete_post(self, keyword: str, base_url: str) -> dict:
        """
        Orchestrates the complete content creation process:
        1. Generates blog post
        2. Adds internal links
        3. Adds media content
        
        Args:
            keyword (str): The main keyword for content generation
            base_url (str): The base URL for media and internal links
            
        Returns:
            dict: Complete post with all components
        """
        try:
            # Initialize media handler with the base_url from the request
            self.media_handler = PostWriterV2(base_url=base_url)
            
            # Generate initial blog post (wrap in asyncio.to_thread if CPU intensive)
            print("Starting blog post generation...")
            blog_post = await asyncio.to_thread(self.blog_generator.generate_blog_post, keyword)
            print("✓ Blog post generated")
            
            if not blog_post or not isinstance(blog_post, dict) or "content" not in blog_post:
                raise ValueError(f"Invalid blog post format: {blog_post}")

            # Add internal links (handle both async and sync cases)
            print("Starting internal linking...")
            if asyncio.iscoroutinefunction(self.internal_linker.process_content_with_links):
                content_with_links = await self.internal_linker.process_content_with_links(blog_post["content"], base_url)
            else:
                content_with_links = await asyncio.to_thread(
                    self.internal_linker.process_content_with_links,
                    blog_post["content"],
                    base_url
                )
            print("✓ Internal links added")
            
            # Add media content (wrap in asyncio.to_thread)
            print("Starting media population...")
            final_post = await asyncio.to_thread(
                self.media_handler.populate_media_in_html,
                content_with_links,
                base_url
            )
            print("✓ Media populated")
            
            return {
                "status": "success",
                "data": final_post,
                "keyword": keyword
            }
            
        except Exception as e:
            print(f"Error in content generation: {str(e)}")
            return {
                "status": "error",
                "message": str(e),
                "keyword": keyword
            }

    async def get_generation_status(self, post_id: str) -> dict:
        """
        Checks the status of a post generation process
        
        Args:
            post_id (str): The ID of the post being generated
            
        Returns:
            dict: Current status of the post generation
        """
        # To be implemented based on how you want to track progress
        pass 

async def main():
    # Create an instance of ContentAPIHandler
    api = ContentAPIHandler()
    
    # Test keyword
    test_keyword = "How to start rucking"
    
    print(f"\nGenerating complete post for keyword: {test_keyword}")
    print("-" * 50)
    
    # Generate the post
    result = await api.generate_complete_post(test_keyword, "https://ruckquest.com")
    
    # Print the result
    if result["status"] == "success":
        print("\nSuccessfully generated post:")
        print(result["data"])
    else:
        print("\nError generating post:")
        print(result["message"])

if __name__ == "__main__":
    asyncio.run(main())