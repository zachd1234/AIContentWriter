from siteMapFetch import fetch_posts_from_sitemap
import re
from urllib.parse import urlparse

def suggest_internal_links(post_content):
    """
    Acts as an intelligent agent to suggest contextually relevant internal links
    by analyzing the content and finding semantic connections to existing posts.
    
    Args:
        post_content (str): The content of the current post
        
    Returns:
        list: A list of contextual link suggestions
    """
    try:
        # Fetch all posts from sitemap
        all_posts = fetch_posts_from_sitemap()
        
        # Split the content into paragraphs for context
        paragraphs = post_content.split('\n\n')
        
        suggestions = []
        
        print("\nAnalyzing content for potential internal links...")
        
        # Analyze each paragraph for potential linking opportunities
        for para_index, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) < 50:  # Skip very short paragraphs
                continue
                
            # For each existing post, check if its topic relates to this paragraph
            for target_post in all_posts:
                path = urlparse(target_post['loc']).path
                slug = path.rstrip('/').split('/')[-1]
                topic = slug.replace('-', ' ')
                
                # Look for semantic connections
                if is_semantically_related(paragraph, topic):
                    # Find the best anchor text within the paragraph
                    anchor_text = find_best_anchor_text(paragraph, topic)
                    
                    if anchor_text:
                        suggestion = {
                            'target_url': target_post['loc'],
                            'anchor_text': anchor_text,
                            'context': paragraph,
                            'paragraph_index': para_index,
                            'topic': topic
                        }
                        suggestions.append(suggestion)
        
        # Remove duplicate suggestions and keep the best ones
        unique_suggestions = filter_best_suggestions(suggestions)
        
        # Format the output in a more natural way
        print(f"\nFound {len(unique_suggestions)} meaningful internal linking opportunities:")
        for suggestion in unique_suggestions:
            print(f"\nSuggested Link:")
            print(f"→ Target: {suggestion['target_url']}")
            print(f"→ Anchor: \"{suggestion['anchor_text']}\"")
            print(f"→ Context: \"{suggestion['context'][:100]}...\"")
            print(f"→ Reasoning: This paragraph discusses {suggestion['topic']}")
            
        return unique_suggestions
        
    except Exception as e:
        print(f"Error suggesting internal links: {str(e)}")
        return []

def is_semantically_related(paragraph, topic):
    """
    Determines if a paragraph is semantically related to a topic.
    """
    # Convert topic words to a list of key terms
    topic_terms = set(topic.lower().split())
    
    # Remove common words from topic terms
    topic_terms = {term for term in topic_terms if len(term) > 3}
    
    # Look for topic terms in the paragraph
    paragraph_lower = paragraph.lower()
    
    # Count how many topic terms appear in the paragraph
    matches = sum(1 for term in topic_terms if term in paragraph_lower)
    
    # Consider it related if we find enough matching terms
    return matches >= len(topic_terms) / 2

def find_best_anchor_text(paragraph, topic):
    """
    Finds the most natural anchor text in a paragraph related to the topic.
    """
    # Try to find a natural phrase that encompasses the topic
    topic_words = topic.split()
    
    # Look for exact matches first
    pattern = re.compile(r'\b' + re.escape(topic) + r'\b', re.IGNORECASE)
    match = pattern.search(paragraph)
    if match:
        return match.group()
    
    # Look for partial matches with key terms
    for word in topic_words:
        if len(word) < 4:
            continue
        pattern = re.compile(r'\b\w*' + re.escape(word) + r'\w*\b', re.IGNORECASE)
        match = pattern.search(paragraph)
        if match:
            # Get some context around the match
            start = max(0, match.start() - 20)
            end = min(len(paragraph), match.end() + 20)
            context = paragraph[start:end]
            return match.group()
    
    return None

def filter_best_suggestions(suggestions):
    """
    Filters and ranks the suggestions to keep only the most relevant ones.
    """
    # Remove duplicate URLs, keeping the one with the best context
    seen_urls = {}
    for suggestion in suggestions:
        url = suggestion['target_url']
        if url not in seen_urls or len(suggestion['context']) > len(seen_urls[url]['context']):
            seen_urls[url] = suggestion
    
    return list(seen_urls.values())

def main():
    # Sample blog post content for testing
    test_content = """
    Rucking is a fantastic way to improve your fitness and mental toughness. 
    When you start training with a weighted backpack, you'll discover new challenges 
    and benefits. The key to successful rucking is proper form and gradually 
    increasing your weight and distance.

    Choosing the right backpack is crucial for your rucking journey. You want 
    something durable and comfortable that can handle the extra weight. Many 
    people start with basic hiking backpacks, but specialized rucking packs 
    offer better weight distribution and durability.

    Training for your first ruck march requires a systematic approach. Start 
    with shorter distances and lighter weights, then progressively increase 
    both as your strength and endurance improve. Remember to maintain good 
    posture and stay hydrated throughout your ruck.

    Mental toughness is just as important as physical preparation. During long 
    rucks, your mind will often want to quit before your body actually needs to. 
    Building mental resilience through consistent training will help you push 
    through these challenging moments.
    """
    
    print("Testing internal link suggestions with sample content...")
    print("-" * 50)
    suggestions = suggest_internal_links(test_content)

if __name__ == "__main__":
    main()
