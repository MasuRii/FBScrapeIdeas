import google.generativeai as genai
import json
from typing import List, Dict
import logging
import time

from config import get_google_api_key

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def categorize_posts_batch(
    posts: List[Dict],
    max_retries: int = 3,
    initial_delay: int = 5
) -> List[Dict]:
    """
    Sends a batch of posts to Gemini 2.0 Flash for categorization and returns the results.
    Includes basic error handling and retry logic.

    Args:
        posts: A list of dictionaries, each containing 'internal_post_id' and 'post_content_raw'.

    Returns:
        A list of dictionaries with added AI categorization results, or an empty list if processing fails.
    """
    if not posts:
        return []

    api_key = get_google_api_key()
    if not api_key:
        logging.error("Google API key not found.")
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash')

    try:
        with open('ai/gemini_schema.json', 'r') as f:
            response_schema = json.load(f)
    except FileNotFoundError:
        logging.error("Error: ai/gemini_schema.json not found.")
        return []
    except json.JSONDecodeError:
        logging.error("Error decoding ai/gemini_schema.json.")
        return []

    prompt_parts = [
        "You are an expert post categorizer. Analyze the following Facebook posts. ",
        "For each post, identify its primary category, a sub-category if applicable, ",
        "3-5 relevant keywords, a 1-2 sentence summary, whether it suggests a potential project idea (true/false), ",
        "and provide a brief reasoning for your categorization. ",
        "Posts are provided with a temporary ID. Format your response as a JSON array of objects, ",
        "adhering to the provided schema. ",
        "Categories to use: Problem Statement, Project Idea, Question/Inquiry, General Discussion, Other.\n\n",
        "Posts:\n"
    ]

    post_id_map = {post['internal_post_id']: post for post in posts}
    for post in posts:
        prompt_parts.append(f"[POST_ID_{post['internal_post_id']}: {post['post_content_raw']}]\n")

    prompt_text = "".join(prompt_parts)

    generation_config = {
        "responseMimeType": "application/json",
        "responseSchema": response_schema
    }

    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(f"Attempt {attempt + 1} to categorize {len(posts)} posts.")
            response = model.generate_content(prompt_text, generation_config=generation_config)
            response.raise_for_status()

            categorized_results_list = json.loads(response.text)

            if not isinstance(categorized_results_list, list):
                 logging.error(f"Gemini response was not a list: {response.text}")
                 attempt += 1
                 if attempt < max_retries:
                    delay = initial_delay * (2 ** (attempt - 1))
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                 else:
                    logging.error(f"Max retries ({max_retries}) reached. Failed to parse Gemini response.")
                    return []
                 continue

            mapped_results = []
            for ai_result in categorized_results_list:
                post_id = ai_result.get('postId')
                if post_id and post_id.startswith('POST_ID_'):
                    original_id = int(post_id.replace('POST_ID_', ''))
                    if original_id in post_id_map:
                        original_post = post_id_map[original_id]
                        combined_data = original_post.copy()
                        combined_data.update({
                            'ai_category': ai_result.get('category'),
                            'ai_sub_category': ai_result.get('subCategory'),
                            'ai_keywords': json.dumps(ai_result.get('keywords', [])),
                            'ai_summary': ai_result.get('summary'),
                            'ai_is_potential_idea': int(ai_result.get('isPotentialIdea', False)),
                            'ai_reasoning': ai_result.get('reasoning'),
                            'ai_raw_response': json.dumps(ai_result),
                            'is_processed_by_ai': 1,
                            'last_ai_processing_at': int(time.time())
                        })
                        mapped_results.append(combined_data)
                    else:
                        logging.warning(f"Gemini returned unknown postId: {post_id}")
                else:
                    logging.warning(f"Gemini returned invalid postId format or missing: {ai_result.get('postId')}")

            logging.info("Successfully categorized and mapped posts.")
            return mapped_results

        except Exception as e:
            attempt += 1
            logging.error(f"API call or processing failed (Attempt {attempt}/{max_retries}): {e}")
            if attempt < max_retries:
                delay = initial_delay * (2 ** (attempt - 1))
                logging.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.error(f"Max retries ({max_retries}) reached. Failed to categorize posts.")
                return []

    return []

def create_post_batches(all_posts: List[Dict], batch_size_chars: int = 700000) -> List[List[Dict]]:
    """
    Groups a list of posts into batches based on character count.

    Args:
        all_posts: A list of post dictionaries.
        batch_size_chars: The maximum character count per batch.

    Returns:
        A list of lists, where each inner list is a batch of post dictionaries.
    """
    batches: List[List[Dict]] = []
    current_batch: List[Dict] = []
    current_batch_char_count = 0

    for post in all_posts:
        post_char_count = len(post.get('post_content_raw', ''))
        estimated_post_token_count = post_char_count + 100

        if current_batch_char_count + estimated_post_token_count > batch_size_chars:
            if current_batch:
                batches.append(current_batch)
            current_batch = [post]
            current_batch_char_count = estimated_post_token_count
        else:
            current_batch.append(post)
            current_batch_char_count += estimated_post_token_count

    if current_batch:
        batches.append(current_batch)

    logging.info(f"Created {len(batches)} batches from {len(all_posts)} posts.")
    return batches

if __name__ == '__main__':



    dummy_posts = []
    for i in range(20):
        dummy_posts.append({
            "internal_post_id": i + 1,
            "post_content_raw": "This is a test post content. " * 50
        })
    
    batches = create_post_batches(dummy_posts, batch_size_chars=10000)
    pass 