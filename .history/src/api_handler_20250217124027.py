import blog_generator
import media_populating_service
import linking_service

class ContentAPIHandler:
    def __init__(self):
        self.blog_generator = blog_generator.BlogGenerator()
        self.media_handler = media_populating_service.PostWriterV2()
        self.internal_linker = linking_service.LinkingAgent()

    async def generate_complete_post(self, keyword: str) -> dict:
        """
        Orchestrates the complete content creation process:
        1. Generates blog post
        2. Adds media content
        3. Adds internal links
        
        Args:
            keyword (str): The main keyword for content generation
            
        Returns:
            dict: Complete post with all components
        """
        try:
            # Generate initial blog post
            blog_post = self.blog_generator.generate_blog_post(keyword)
            
            # Debug print
            print("Blog post received:", blog_post)
            
            # Add media content
            if blog_post and isinstance(blog_post, dict) and "content" in blog_post:
                content = blog_post["content"]
                print("Content before media population:", content[:200])  # Print first 200 chars
                post_with_media = self.media_handler.populate_media_in_html(content)
                print("Content after media population:", post_with_media[:200])  # Print first 200 chars
            else:
                raise ValueError(f"Invalid blog post format: {blog_post}")
            
            # Add internal links
            final_post = await self.internal_linker.process_content_with_links(post_with_media)
            
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
    test_keyword = "What is a Phase I Environmental Site Assessment?"
    
    print(f"\nGenerating complete post for keyword: {test_keyword}")
    print("-" * 50)
    
    # Generate the post
    result = await api.generate_complete_post(test_keyword)
    
    # Print the result
    if result["status"] == "success":
        print("\nSuccessfully generated post:")
        print(result["data"])
    else:
        print("\nError generating post:")
        print(result["message"])

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())