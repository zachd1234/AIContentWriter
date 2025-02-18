import blog_generator
import media_populating_service as media_service
import linking_service
import media_handler

class ContentAPIHandler:
    def __init__(self):
        self.blog_generator = blog_generator.BlogGenerator()
        self.media_handler = media_handler.MediaHandler()
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
            blog_post = await self.blog_generator.generate_post(keyword)
            
            # Add media content
            post_with_media = await self.media_handler.populate_media(blog_post)
            
            # Add internal links
            final_post = await self.internal_linker.add_internal_links(post_with_media)
            
            return {
                "status": "success",
                "data": final_post,
                "keyword": keyword
            }
            
        except Exception as e:
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