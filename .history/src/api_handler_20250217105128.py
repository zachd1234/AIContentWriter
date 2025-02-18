from .blog_generator import BlogGenerator
from .MediaPopulatingService import PostWriterV2
from .linkingService import LinkingAgent
from media_handler import MediaHandler
from internal_linker import InternalLinker

class ContentAPIHandler:
    def __init__(self):
        self.blog_generator = BlogGenerator()
        self.media_handler = MediaHandler()
        self.internal_linker = InternalLinker()

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