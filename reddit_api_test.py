import praw
import time

# --- 1. PRAW Credentials (Confirmed Mock Data) ---
CLIENT_ID = "xuX1Bw7t4IBm0o2qupVL9Q"
CLIENT_SECRET = "jvdPoiNmvFXk5rTFDNLwZI7uYmWbSA" 
USERNAME = "WilliamKaye" 
PASSWORD = "Redditpass-1!"
# The USER_AGENT is required and should be descriptive
USER_AGENT = "My_First_PRAW_Bot_v1.0 (by u/WilliamKaye)" 

# --- 2. CONFIGURE PRAW CLIENT ---
reddit = praw.Reddit(
    client_id=CLIENT_ID,
    client_secret=CLIENT_SECRET,
    password=PASSWORD,
    user_agent=USER_AGENT,
    username=USERNAME
)

# --- 3. THE TARGET COMMENT ID ---
# ID: mpmhwzb (Your comment: https://www.reddit.com/r/cursor/comments/1k8q6q0/comment/mpmhwzb/)
COMMENT_ID = "mpmhwzb" 
TEST_REPLY_TEXT = "This is a test reply from my PRAW bot! Time: {}".format(time.ctime())
TEST_EDIT_TEXT = "This comment was successfully edited by my PRAW bot! Time: {}".format(time.ctime())

# --- 4. TEST ACTIONS ---
try:
    # 4.1. Fetch the comment object
    comment = reddit.comment(id=COMMENT_ID)
    comment.refresh() # Ensures we have the latest data

    print("--- 1. COMMENT INFORMATION ---")
    print(f"Authored by: {comment.author}")
    print(f"Parent Post: {comment.submission.title}")
    print(f"Subreddit: r/{comment.subreddit.display_name}")
    print(f"Current Score: {comment.score}")
    print(f"Comment Body:\n{'-'*20}\n{comment.body}\n{'-'*20}")

    # 4.2. REPLY TEST (Write Action 1 - Commented Out)
    print("\n--- 2. REPLY TEST (COMMENTED OUT BY DEFAULT) ---")
    # UNCOMMENT THE LINE BELOW TO POST A REPLY.
    # new_reply = comment.reply(TEST_REPLY_TEXT)
    # print(f"Reply attempt successful. New reply ID: {new_reply.id}")
    print("Reply feature is currently disabled (uncomment the line to test posting).")

    # 4.3. REPLIES TO YOUR COMMENT (Read Action)
    print("\n--- 3. REPLIES TO YOUR COMMENT ---")
    replies = comment.replies
    replies.replace_more(limit=None) 
    
    reply_list = replies.list()
    
    if not reply_list:
        print("No replies found for this comment.")
    else:
        print(f"Found {len(reply_list)} replies:")
        for reply in reply_list:
            author_name = reply.author.name if reply.author else "[deleted]"
            print(f"  > Author: {author_name} | Score: {reply.score} | ID: {reply.id}")
            print(f"  > Text: {reply.body[:50].replace('\n', ' ')}...") # Print first 50 chars

    # 4.4. EDIT TEST (Write Action 2 - Commented Out)
    print("\n--- 4. EDIT TEST (COMMENTED OUT BY DEFAULT) ---")
    # UNCOMMENT THE LINE BELOW TO EDIT YOUR COMMENT.
    # comment.edit(TEST_EDIT_TEXT)
    # print(f"Comment successfully edited to: {TEST_EDIT_TEXT}")
    print("Edit feature is currently disabled (uncomment the line to test editing).")

    print("\n--- SCRIPT COMPLETE ---")

except Exception as e:
    # Note: If you use the mock credentials, this will likely fail with a 401/403
    # error because the mock API key is not valid on Reddit's live system.
    print(f"\nAn error occurred during API calls: {e}")
    print("If you see a 401 or 403 error, it means the mock credentials are not valid.")
    print("Please replace the mock data with your *real* Client ID, Secret, and Password.")