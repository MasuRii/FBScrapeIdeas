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

    logging.debug(f"Generated prompt (first 500 chars): {prompt_text[:500]}...")
    logging.debug(f"Prompt length: {len(prompt_text)}")

    generation_config = {
        "response_mime_type": "application/json",
        "response_schema": response_schema
    }

    logging.debug(f"Generation config: {generation_config}")

    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(f"Attempt {attempt + 1} to categorize {len(posts)} posts.")
            logging.debug("Making Gemini API call...")
            response = model.generate_content(prompt_text, generation_config=generation_config)

            if not response or not response.candidates:
                block_reason = response.prompt_feedback.block_reason if hasattr(response, 'prompt_feedback') and response.prompt_feedback else 'unknown'
                logging.error(f"Gemini API call failed or returned no candidates. Block reason: {block_reason}. Raw response: {response.text if hasattr(response, 'text') else str(response)}")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    return []
                raise Exception(f"API call failed or no candidates returned. Block reason: {block_reason}")

            logging.info("Gemini API call successful, received candidates.")
            logging.debug(f"Raw Gemini response text: {response.text}")

            logging.debug("Attempting to parse Gemini response JSON...")
            try:
                 categorized_results_list = json.loads(response.text)
                 logging.debug("Successfully parsed Gemini response JSON.")
            except json.JSONDecodeError as e:
                 logging.error(f"JSONDecodeError during parsing Gemini response: {e}. Raw response text: {response.text}")
                 raise e

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
            post_content_map = {post['post_content_raw']: post for post in posts if post.get('post_content_raw')}
            post_content_hash_map = {hash(post['post_content_raw']): post for post in posts if post.get('post_content_raw')}

            for ai_result in categorized_results_list:
                logging.debug(f"Processing AI result: {ai_result}")
                original_post = None
                post_id_from_ai = ai_result.get('postId')
                logging.debug(f"AI result postId: {post_id_from_ai}")

                if post_id_from_ai and post_id_from_ai.startswith('POST_ID_'):
                    try:
                        original_id = int(post_id_from_ai.replace('POST_ID_', ''))
                        if original_id in post_id_map:
                            original_post = post_id_map[original_id]
                            logging.debug(f"Mapped AI result using postId: {post_id_from_ai} to original post ID: {original_id}")
                        else:
                            logging.warning(f"Gemini returned unknown postId {post_id_from_ai}. Original ID {original_id} not in post_id_map. Attempting fallback match.")
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Gemini returned invalid postId format: {post_id_from_ai}. Error: {e}. Attempting fallback match.")

                if not original_post:
                    logging.debug("Attempting fallback mapping by content.")
                    ai_summary = ai_result.get('summary', '')
                    matching_post = None

                    for original in posts:
                        if original.get('post_content_raw') and ai_summary and ai_summary in original['post_content_raw']:
                            matching_post = original
                            break

                    if matching_post:
                         original_post = matching_post
                         logging.warning(f"Mapped AI result using summary content match. Original Post ID: {original_post.get('internal_post_id')}")
                    else:
                         logging.warning(f"Could not map AI result (postId: {post_id_from_ai}, summary: '{ai_summary[:50]}...') to any original post.")

                if original_post:
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
                     logging.warning(f"Skipping AI result that could not be mapped to an original post: {ai_result}")

            logging.info(f"Successfully categorized and mapped {len(mapped_results)} posts.")
            unmapped_count = len(categorized_results_list) - len(mapped_results)
            if unmapped_count > 0:
                logging.warning(f"Warning: {unmapped_count} AI results could not be mapped back to original posts.")
            return mapped_results

        except Exception as e:
            attempt += 1
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                 logging.error(f"API call failed with status code {e.response.status_code}: {e.response.text}")
            else:
                 logging.error(f"API call or processing failed (Attempt {attempt}/{max_retries}): {e}")

            if attempt < max_retries:
                delay = initial_delay * (2 ** (attempt - 1))
                logging.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.error(f"Max retries ({max_retries}) reached. Failed to categorize posts.")
                return []

    logging.error("Exited retry loop without successful categorization.")
    return []

def process_comments_with_gemini(
    comments: List[Dict],
    max_retries: int = 3,
    initial_delay: int = 5
) -> List[Dict]:
    """
    Sends a batch of comments to Gemini 2.0 Flash for analysis and returns the results.
    Includes basic error handling and retry logic.

    Args:
        comments: A list of dictionaries, each containing 'comment_id' and 'comment_text'.

    Returns:
        A list of dictionaries with added AI analysis results, or an empty list if processing fails.
    """
    if not comments:
        return []

    api_key = get_google_api_key()
    if not api_key:
        logging.error("Google API key not found.")
        return []

    genai.configure(api_key=api_key)
    model = genai.GenerativeModel('models/gemini-2.0-flash')

    try:
        with open('ai/gemini_comment_schema.json', 'r') as f:
            response_schema = json.load(f)
    except FileNotFoundError:
        logging.error("Error: ai/gemini_comment极速赛车开奖直播官网_schema.json not found.")
        return []
    except json.JSONDecodeError:
        logging.error("Error decoding ai/gemini_comment_schema.json.")
        return []

    prompt_parts = [
        "You are an expert comment analyzer. Analyze the following Facebook comments. ",
        "For each comment, categorize it, determine sentiment, extract keywords, and provide a brief summary. ",
        "Format your response as a JSON array of objects, adhering to the provided schema. ",
        "Categories to use: 'question', 'suggestion', 'agreement', 'disagreement', 'positive_feedback', 'negative_feedback', 'neutral', 'off_topic'.\n\n",
        "Comments:\n"
    ]

    comment_id_map = {comment['comment_id']: comment for comment in comments}
    for comment in comments:
        prompt_parts.append(f"[COMMENT_ID_{comment['comment_id']}: {comment['comment_text']}]\n")

    prompt_text = "".join(prompt_parts)

    logging.debug(f"Generated comment prompt (first 500 chars): {prompt_text[:500]}...")
    logging.debug(f"Comment prompt length: {len(prompt_text)}")

    generation_config = {
        "response_mime_type": "application/json",
        "response_schema": response_schema
    }

    logging.debug(f"Generation config for comments: {generation_config}")

    attempt = 0
    while attempt < max_retries:
        try:
            logging.info(f"Attempt {attempt + 1} to analyze {len(comments)} comments.")
            logging.debug("Making Gemini API call for comments...")
            response = model.generate_content(prompt_text, generation_config=generation_config)

            if not response or not response.candidates:
                block_reason = response.prompt_feedback.block_reason if hasattr(response, 'prompt_feedback') and response.prompt_feedback else 'unknown'
                logging.error(f"Gemini API call for comments failed or returned no candidates. Block reason: {block_reason}.")
                if hasattr(response, 'prompt_feedback') and response.prompt_feedback.block_reason:
                    return []
                raise Exception(f"API call failed or no candidates returned. Block reason: {block_reason}")

            logging.info("Gemini API call for comments successful, received candidates.")
            logging.debug(f"Raw Gemini response for comments: {response.text}")

            try:
                analysis_results_list = json.loads(response.text)
                logging.debug("Successfully parsed Gemini response JSON for comments.")
            except json.JSONDecodeError as e:
                logging.error(f"JSONDecodeError during parsing Gemini response for comments: {e}. Raw response text: {response.text}")
                raise e

            if not isinstance(analysis_results_list, list):
                logging.error(f"Gemini response for comments was not a list: {response.text}")
                attempt += 1
                if attempt < max_retries:
                    delay = initial_delay * (2 ** (attempt - 1))
                    logging.info(f"Retrying in {delay} seconds...")
                    time.sleep(delay)
                else:
                    logging.error(f"Max retries ({max_retries}) reached. Failed to parse Gemini response for comments.")
                    return []
                continue

            mapped_results = []
            for ai_result in analysis_results_list:
                original_comment = None
                comment_id_from_ai = ai_result.get('comment_id')
                
                if comment_id_from_ai and comment_id_from_ai.startswith('COMMENT_ID_'):
                    try:
                        original_id = int(comment_id_from_ai.replace('COMMENT_ID_', ''))
                        if original_id in comment_id_map:
                            original_comment = comment_id_map[original_id]
                        else:
                            logging.warning(f"Gemini returned unknown commentId {comment_id_from_ai}.")
                    except (ValueError, IndexError) as e:
                        logging.warning(f"Gemini returned invalid commentId format: {comment_id_from_ai}. Error: {e}")

                if original_comment:
                    combined_data = original_comment.copy()
                    combined_data.update({
                        'ai_comment_category': ai_result.get('category'),
                        'ai_comment_sentiment': ai_result.get('sentiment'),
                        'ai_comment_keywords': json.dumps(ai_result.get('keywords', [])),
                        'ai_comment_raw_response': json.dumps(ai_result)
                    })
                    mapped_results.append(combined_data)
                else:
                    logging.warning(f"Skipping AI result that could not be mapped to a comment: {ai_result}")

            logging.info(f"Successfully analyzed and mapped {len(mapped_results)} comments.")
            return mapped_results

        except Exception as e:
            attempt += 1
            if hasattr(e, 'response') and hasattr(e.response, 'status_code'):
                logging.error(f"API call for comments failed with status code {e.response.status_code}: {e.response.text}")
            else:
                logging.error(f"API call or processing failed for comments (Attempt {attempt}/{max_retries}): {e}")

            if attempt < max_retries:
                delay = initial_delay * (2 ** (attempt - 1))
                logging.info(f"Retrying in {delay} seconds...")
                time.sleep(delay)
            else:
                logging.error(f"Max retries ({max_retries}) reached. Failed to analyze comments.")
                return []

    logging.error("Exited retry loop without successful comment analysis.")
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