from siteMapFetch import fetch_posts_from_sitemap
import re
from urllib.parse import urlparse

def suggest_internal_links(post_content):
    """
    Suggests internal links for a given post by analyzing other posts from the sitemap
    
    Args:
        post_content (str): The content of the current post
        
    Returns:
        list: A list of link suggestions with URLs and anchor text
    """
    try:
        # Fetch all posts from sitemap
        all_posts = fetch_posts_from_sitemap()
        
        suggestions = []
        
        # Extract meaningful words from the post URLs (excluding common WordPress parts)
        for target_post in all_posts:
            # Parse the URL to get the slug
            path = urlparse(target_post['loc']).path
            # Remove trailing slash and get the last part of the path (the slug)
            slug = path.rstrip('/').split('/')[-1]
            
            # Convert slug to potential keywords (remove hyphens and split)
            keywords = slug.replace('-', ' ').split()
            
            # Look for these keywords in the content
            for keyword in keywords:
                if len(keyword) < 4:  # Skip very short words
                    continue
                    
                # Case insensitive search for the keyword
                pattern = re.compile(r'\b' + re.escape(keyword) + r'\b', re.IGNORECASE)
                matches = pattern.finditer(post_content)
                
                for match in matches:
                    # Get some context around the keyword
                    start = max(0, match.start() - 40)
                    end = min(len(post_content), match.end() + 40)
                    context = post_content[start:end]
                    
                    suggestion = {
                        'target_url': target_post['loc'],
                        'keyword': keyword,
                        'context': f"...{context}...",
                        'anchor_text': match.group(),
                        'position': match.start()
                    }
                    suggestions.append(suggestion)
        
        # Sort suggestions by position in the content
        suggestions.sort(key=lambda x: x['position'])
        
        # Remove duplicate suggestions for the same target URL
        seen_urls = set()
        unique_suggestions = []
        for suggestion in suggestions:
            if suggestion['target_url'] not in seen_urls:
                seen_urls.add(suggestion['target_url'])
                unique_suggestions.append(suggestion)
        
        # Format the output
        print(f"\nFound {len(unique_suggestions)} potential internal linking opportunities:")
        for suggestion in unique_suggestions:
            print(f"\nLink to: {suggestion['target_url']}")
            print(f"Anchor text: '{suggestion['anchor_text']}'")
            print(f"Context: {suggestion['context']}")
            
        return unique_suggestions
        
    except Exception as e:
        print(f"Error suggesting internal links: {str(e)}")
        return []
