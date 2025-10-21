# api_client.py
import requests
import json
import time
from urllib.parse import urljoin
from twitterexplorer_sigint import twitter_config as config

# Helper function for safe nested access
def get_nested_value(data, path_string):
    """Safely gets a value from nested dict/list using dot notation string, including numeric list indices."""
    if not path_string: # Handle empty path edge case
        return data
    keys = path_string.split('.')
    current_val = data
    for key in keys:
        if not current_val: # Stop if we hit None or empty container along the path
            return None
        if key.isdigit(): # Check if key is numeric (an index)
            index = int(key)
            if isinstance(current_val, list) and 0 <= index < len(current_val):
                current_val = current_val[index]
            else:
                # Index out of bounds or trying to index something not a list
                # print(f"Warning: Index '{index}' invalid for path '{path_string}' on value: {current_val}") # Optional debug
                return None
        elif isinstance(current_val, dict):
            current_val = current_val.get(key) # Use .get for safety
            if current_val is None:
                # Key not found
                # print(f"Warning: Key '{key}' not found for path '{path_string}' in dict: {current_val}") # Optional debug
                return None
        else:
            # Trying to access a key/index on a non-dict/list type (e.g., a string, number)
            # print(f"Warning: Cannot apply key '{key}' for path '{path_string}' on value type: {type(current_val)}") # Optional debug
            return None
    return current_val


def execute_api_step(step_plan, previous_results, rapidapi_key):
    """Executes a single API call step, handling pagination and basic errors."""
    endpoint_suffix = step_plan.get('endpoint')
    params = step_plan.get('params', {})
    max_pages = step_plan.get('max_pages', config.DEFAULT_MAX_PAGES_FALLBACK) # Default to 1 page if not specified by LLM
    reason = step_plan.get('reason', 'No reason provided') # For logging

    print(f"\nExecuting Step: Call {endpoint_suffix} (Reason: {reason})")

    if not endpoint_suffix:
        return {"error": "Missing endpoint in plan step.", "endpoint": endpoint_suffix}

    # --- Resolve Parameter Dependencies ---
    resolved_params = {}
    try:
        for key, value in params.items():
            param_error = None # Store potential errors for clarity
            resolved_value = None

            # --- NEW: Handle Dictionary-based List Dependency ---
            if isinstance(value, dict) and 'source_step' in value:
                print(f"  Resolving list dependency for param '{key}'...")
                source_step_idx = value.get('source_step') - 1
                source_list_path = value.get('source_list_path')
                extract_field = value.get('extract_field')
                join_with = value.get('join_with') # Optional

                if source_step_idx < 0 or source_step_idx >= len(previous_results):
                    param_error = f"Invalid source_step {value.get('source_step')}"
                elif not source_list_path or not extract_field:
                    param_error = "Missing source_list_path or extract_field"
                else:
                    source_data = previous_results[source_step_idx].get('data')
                    if not source_data:
                        param_error = f"No data found from step {value.get('source_step')}"
                    else:
                        # Get the source list
                        source_list = get_nested_value(source_data, source_list_path)
                        if not isinstance(source_list, list):
                             param_error = f"Source path '{source_list_path}' did not resolve to a list in step {value.get('source_step')}"
                        else:
                            # Extract values from each item
                            extracted_values = []
                            for item in source_list:
                                extracted = get_nested_value(item, extract_field)
                                if extracted is not None: # Only add if value was found
                                     extracted_values.append(str(extracted)) # Convert to string for joining
                                else:
                                     print(f"    Warning: Field '{extract_field}' not found in one item of list '{source_list_path}'.")

                            if not extracted_values:
                                 print(f"    Warning: No values extracted for field '{extract_field}' from list '{source_list_path}'.")
                                 # Decide how to handle: error, empty string, skip param? Let's use empty string for now.
                                 resolved_value = ""
                            elif join_with is not None:
                                resolved_value = join_with.join(extracted_values)
                            else:
                                resolved_value = extracted_values # Return as list if no join specified

            # --- Handle Simple String Dependency ---
            elif isinstance(value, str) and value.startswith("$step"):
                print(f"  Resolving simple dependency for param '{key}'...")
                parts = value[1:].split('.')
                step_index = int(parts[0].replace("step", "")) - 1 # 0-based index
                keys_to_access = '.'.join(parts[1:]) # Re-join keys for nested access helper

                if step_index < 0 or step_index >= len(previous_results):
                    param_error = f"Invalid step index {step_index+1} referenced in '{value}'"
                else:
                    target_data = previous_results[step_index].get('data')
                    if not target_data:
                        param_error = f"No data found from step {step_index+1} to resolve '{value}'"
                    else:
                        resolved_value = get_nested_value(target_data, keys_to_access)
                        if resolved_value is None:
                             param_error = f"Path '{keys_to_access}' not found in data from step {step_index+1} for '{value}'"

            # --- No Dependency ---
            else:
                resolved_value = value

            # --- Assign or Raise Error ---
            if param_error:
                print(f"    Error resolving parameter '{key}': {param_error}")
                raise ValueError(param_error) # Raise error to stop execution
            else:
                resolved_params[key] = resolved_value
                if value != resolved_value: # Only print if resolution happened
                     print(f"    Resolved param '{key}': '{value}' -> '{resolved_value}'")

    except ValueError as e: # Catch resolution errors
         print(f"  Error resolving parameters: {e}")
         return {"error": f"Failed to resolve parameter: {e}", "endpoint": endpoint_suffix, "params": params}
    # --- End Parameter Resolution ---


    headers = {
        "X-RapidAPI-Key": rapidapi_key,
        "X-RapidAPI-Host": config.RAPIDAPI_TWITTER_HOST
    }

    full_url = urljoin(config.RAPIDAPI_BASE_URL + "/", endpoint_suffix) # Ensure trailing slash logic is okay
    print(f"  Requesting URL: {full_url}")
    print(f"  With Params: {resolved_params}")

    # ... (Rest of the function remains the same: pagination, error handling, data extraction) ...
    all_results = []
    current_page = 0
    next_cursor = None
    retry_count = 0
    max_retries = 3 # For transient server errors and network timeouts
    page_data = None # Keep track of last page data for structure merging
    data_key_found = None # Keep track of key where list data was found

    while current_page < max_pages:
        current_params = resolved_params.copy()
        if next_cursor:
            current_params['cursor'] = next_cursor
            print(f"  Fetching page {current_page + 1} with cursor {str(next_cursor)[:10]}...")
        else:
             print(f"  Fetching page {current_page + 1}...")

        try:
            response = requests.get(full_url, headers=headers, params=current_params, timeout=config.API_TIMEOUT_SECONDS)
            response.raise_for_status() # Raise HTTPError for bad responses (4xx or 5xx)

            page_data = response.json() # Store last page data
            # --- Data Extraction Logic (Improved slightly) ---
            extracted_list_data = None
            data_key_found = None # Reset for each page? No, keep from first successful extraction

            if isinstance(page_data, list): # If the response *is* the list
                extracted_list_data = page_data
                print(f"  Response is a list.")
            elif isinstance(page_data, dict):
                if data_key_found and data_key_found in page_data and isinstance(page_data[data_key_found], list):
                     extracted_list_data = page_data[data_key_found] # Use previously found key if still valid
                else:
                    list_keys_to_try = ['timeline', 'followers', 'following', 'users', 'trends', 'retweets', 'affilates', 'members', 'sharings', 'results', 'data'] # Added common keys
                    for key in list_keys_to_try:
                        if key in page_data and isinstance(page_data[key], list):
                            extracted_list_data = page_data[key]
                            data_key_found = key # Store the key where list was found
                            print(f"  Extracted list data from key: '{data_key_found}'")
                            break

                # If no list found, but it's a dict, maybe the dict *is* the result (e.g., single tweet)
                # Only treat as single item if it's the first page and no list key was ever found
                if extracted_list_data is None and current_page == 0 and not data_key_found:
                    extracted_list_data = [page_data] # Wrap single item in list for consistency
                    print(f"  Treating full dictionary response as single item list.")
                elif extracted_list_data is None:
                     # If not first page, or a key was expected but missing, maybe just skip? Or log warning.
                     print(f"  Warning: Expected list data (key: {data_key_found}) not found on page {current_page+1}.")


            else: # Unexpected format
                 print(f"  Warning: Unexpected response root type: {type(page_data)}")
                 # Only treat as single item if first page
                 if current_page == 0:
                      extracted_list_data = [page_data]
                 else:
                      print(f"  Ignoring unexpected data format on page {current_page+1}.")


            if extracted_list_data: # Check if we got any data items
                all_results.extend(extracted_list_data)
            # --- End Data Extraction ---

            current_page += 1

            # --- Cursor Handling ---
            next_cursor = None
            if isinstance(page_data, dict):
                 # Prioritize 'next_cursor', common in pagination
                 if 'next_cursor' in page_data and page_data['next_cursor']:
                      next_cursor = page_data['next_cursor']
                 # Fallback to 'cursor' if 'next_cursor' isn't present or empty
                 elif 'cursor' in page_data and page_data['cursor'] and isinstance(page_data.get('cursor'), str):
                      next_cursor = page_data['cursor']

            if not next_cursor or current_page >= max_pages:
                print(f"  Finished fetching for {endpoint_suffix}. Total pages: {current_page}. Has next cursor: {bool(next_cursor)}")
                break # Exit pagination loop

            # Reset retry count on success
            retry_count = 0
            time.sleep(0.5) # Small delay between pages

        # ... (Keep the existing except blocks for HTTPError, RequestException, JSONDecodeError) ...
        except requests.exceptions.HTTPError as e:
            status_code = e.response.status_code
            print(f"  HTTP Error {status_code}: {e.response.text}")
            if status_code == 429: # Rate Limit
                wait_time = (2 ** retry_count) # Exponential backoff
                print(f"  Rate limit hit. Waiting {wait_time} seconds...")
                time.sleep(wait_time)
                retry_count += 1
                if retry_count > 4: # Give up after ~15s total wait
                     return {"error": f"Rate limit exceeded after multiple retries.", "endpoint": endpoint_suffix, "status_code": status_code}
                continue # Retry the current page request without incrementing page count
            elif status_code >= 500 and retry_count < max_retries: # Server error, retry
                 print(f"  Server error ({status_code}). Retrying ({retry_count+1}/{max_retries})...")
                 time.sleep(1 * (retry_count + 1))
                 retry_count += 1
                 continue # Retry current page
            else: # 4xx errors or persistent 5xx
                return {"error": f"HTTP Error {status_code}: {e.response.text}", "endpoint": endpoint_suffix, "status_code": status_code}

        except requests.exceptions.RequestException as e:
            print(f"  Request failed: {e}")
            # Retry transient network errors (timeout, connection errors)
            if retry_count < max_retries:
                wait_time = (2 ** retry_count) + 1  # Exponential backoff: 2s, 4s, 8s, 16s
                print(f"  Network error. Retrying in {wait_time}s ({retry_count+1}/{max_retries})...")
                time.sleep(wait_time)
                retry_count += 1
                continue  # Retry the current page request
            else:
                return {"error": f"Request failed after {max_retries} retries: {e}", "endpoint": endpoint_suffix}
        except json.JSONDecodeError as e:
             print(f"  Failed to decode JSON response: {e}")
             # Add response text to error if possible
             response_text_for_error = ""
             if 'response' in locals() and hasattr(response, 'text'):
                  response_text_for_error = response.text[:500] # Limit length
             return {"error": f"Invalid JSON response from API: {e}. Response text: {response_text_for_error}", "endpoint": endpoint_suffix}


    # --- Post-processing: Combine results intelligently ---
    # Try to reconstruct a meaningful structure, especially if pagination occurred.
    final_data_structure = {}
    if data_key_found:
        final_data_structure[data_key_found] = all_results
        # Add back other top-level keys from the *last* successful page data
        if isinstance(page_data, dict):
             for key, value in page_data.items():
                  if key != data_key_found and key != 'next_cursor' and key != 'cursor': # Avoid adding list/cursor again
                       final_data_structure[key] = value
    elif len(all_results) == 1 and isinstance(all_results[0], dict):
         # If only one item was retrieved (maybe non-list endpoint, or list with 1 item)
         final_data_structure = all_results[0]
    elif len(all_results) > 0:
         # If multiple items but no primary key found (e.g., API returned list directly)
         final_data_structure = {'results': all_results}
    else:
         final_data_structure = {} # No results


    print(f"  Successfully processed request for {endpoint_suffix}.")
    # Ensure data key exists even if empty, for consistency downstream
    if not final_data_structure and data_key_found:
         final_data_structure = {data_key_found: []}
    elif not final_data_structure and not data_key_found and len(all_results) == 0:
         final_data_structure = {} # Truly no data

    # --- MODIFICATION START ---
    # Prepare the final result dictionary
    step_result_data = {"data": final_data_structure} if "error" not in final_data_structure else final_data_structure

    # Include original plan info (like endpoint, step) and executed params
    step_info_to_return = {
        'endpoint': endpoint_suffix,
        'step_executed': step_plan.get('step', -1), # Carry over step number if present
        'executed_params': resolved_params, # Include the parameters used!
        'reason': step_plan.get('reason') # Carry over reason
    }
    step_info_to_return.update(step_result_data) # Add data or error

    return step_info_to_return
    # --- MODIFICATION END ---