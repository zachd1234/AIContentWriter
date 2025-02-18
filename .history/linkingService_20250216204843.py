from siteMapFetch import fetch_posts_from_sitemap
import re
from urllib.parse import urlparse

def suggest_internal_links(post_content):
    """
    Acts as an intelligent agent to suggest contextually relevant internal links
    following Google's guidelines for good anchor text and natural linking.
    """
    try:
        all_posts = fetch_posts_from_sitemap()
        paragraphs = post_content.split('\n\n')
        suggestions = []
        links_in_paragraph = {}  # Track number of links per paragraph
        
        print("\nAnalyzing content for contextual linking opportunities...")
        
        for para_index, paragraph in enumerate(paragraphs):
            if len(paragraph.strip()) < 50:  # Skip very short paragraphs
                continue
            
            links_in_paragraph[para_index] = 0  # Initialize link counter
            
            for target_post in all_posts:
                path = urlparse(target_post['loc']).path
                topic = path.rstrip('/').split('/')[-1].replace('-', ' ')
                
                # Skip if we already have 2 links in this paragraph
                if links_in_paragraph[para_index] >= 2:
                    continue
                
                if is_semantically_related(paragraph, topic):
                    anchor_text = find_natural_anchor_text(paragraph, topic, target_post['loc'])
                    
                    if anchor_text and len(anchor_text.split()) <= 8:  # Limit anchor length
                        suggestion = {
                            'target_url': target_post['loc'],
                            'anchor_text': anchor_text,
                            'context': paragraph,
                            'paragraph_index': para_index,
                            'topic': topic,
                            'relevance_score': calculate_relevance_score(paragraph, topic, anchor_text)
                        }
                        suggestions.append(suggestion)
                        links_in_paragraph[para_index] += 1
        
        # Filter and sort suggestions by relevance
        best_suggestions = filter_best_suggestions(suggestions)
        
        print(f"\nFound {len(best_suggestions)} high-quality linking opportunities:")
        for suggestion in best_suggestions:
            print(f"\nSuggested Link:")
            print(f"→ Target: {suggestion['target_url']}")
            print(f"→ Anchor: \"{suggestion['anchor_text']}\"")
            print(f"→ Context: \"{suggestion['context'][:100]}...\"")
            print(f"→ Relevance Score: {suggestion['relevance_score']:.2f}")
            
        return best_suggestions
        
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

def find_natural_anchor_text(paragraph, topic, target_url):
    """
    Finds natural, descriptive anchor text following Google's guidelines.
    Avoids generic terms like 'click here' and ensures context.
    """
    # Extract meaningful phrases from the target URL
    target_keywords = set(topic.split())
    
    # Find sentences that contain topic keywords
    sentences = re.split(r'[.!?]+', paragraph)
    for sentence in sentences:
        # Skip if sentence is too short
        if len(sentence.strip()) < 30:
            continue
            
        # Look for natural phrases that include key terms
        words = sentence.strip().split()
        for i in range(len(words)):
            for j in range(i + 2, min(i + 9, len(words) + 1)):  # 2-8 word phrases
                phrase = ' '.join(words[i:j])
                
                # Check if phrase is relevant to both source and target
                if is_relevant_anchor(phrase, topic, target_keywords):
                    return phrase
    
    return None

def is_relevant_anchor(phrase, topic, target_keywords):
    """
    Checks if a phrase makes good anchor text by ensuring it's:
    - Descriptive and specific
    - Related to both source and target content
    - Not too generic
    """
    words = set(phrase.lower().split())
    
    # Skip generic phrases
    generic_terms = {'click', 'here', 'read', 'more', 'link', 'website', 'article'}
    if words.intersection(generic_terms):
        return False
    
    # Ensure some topical relevance
    if not words.intersection(target_keywords):
        return False
    
    # Check phrase length and quality
    if len(words) < 2 or len(words) > 8:
        return False
        
    return True

def calculate_relevance_score(paragraph, topic, anchor_text):
    """
    Calculates a relevance score for the suggested link based on:
    - Contextual relevance
    - Anchor text quality
    - Natural placement
    """
    score = 0.0
    
    # Score based on anchor text length (prefer 2-5 words)
    words_count = len(anchor_text.split())
    if 2 <= words_count <= 5:
        score += 0.3
    
    # Score based on topic relevance
    topic_words = set(topic.split())
    context_words = set(paragraph.lower().split())
    relevance = len(topic_words.intersection(context_words)) / len(topic_words)
    score += relevance * 0.4
    
    # Score based on anchor text naturalness
    if not any(generic in anchor_text.lower() for generic in ['click', 'here', 'read', 'more']):
        score += 0.3
    
    return score

def filter_best_suggestions(suggestions):
    """
    Filters and ranks suggestions to ensure:
    - No more than 2 links per paragraph
    - High relevance scores
    - Natural distribution throughout the content
    """
    # Sort by relevance score
    sorted_suggestions = sorted(suggestions, key=lambda x: x['relevance_score'], reverse=True)
    
    # Keep only the best suggestions per paragraph
    seen_paragraphs = {}
    filtered_suggestions = []
    
    for suggestion in sorted_suggestions:
        para_idx = suggestion['paragraph_index']
        if para_idx not in seen_paragraphs:
            seen_paragraphs[para_idx] = 1
            filtered_suggestions.append(suggestion)
        elif seen_paragraphs[para_idx] < 2 and suggestion['relevance_score'] > 0.6:
            seen_paragraphs[para_idx] += 1
            filtered_suggestions.append(suggestion)
            
    return filtered_suggestions

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
