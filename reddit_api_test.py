import praw

# 1. Replace YOUR_CLIENT_ID_HERE with the real Client ID you copied
CLIENT_ID = "xuX1Bw7t4IBm0o2qupVL9Q"           

# 2. Use the secret you already have (and replaced the other secret with)
CLIENT_SECRET = "jvdPoiNmvFXk5rTFDNLwZI7uYmWbSA" 

# 3. Create a descriptive, unique name (this is the USER_AGENT)
USER_AGENT = "My_First_PRAW_Bot_v1.0 by u/YourRedditUsername" 

# 4. Your Reddit account credentials
USERNAME = "WilliamKaye"             
PASSWORD = "Redditpass-1!"             

try:
    # This is how PRAW uses all the credentials to log you in
    reddit = praw.Reddit(
        client_id=CLIENT_ID,
        client_secret=CLIENT_SECRET,
        user_agent=USER_AGENT,
        username=USERNAME,
        password=PASSWORD
    )

    # If this prints your username, you are successfully connected!
    print(f"PRAW successfully authenticated as: {reddit.user.me()}")

except Exception as e:
    print(f"Authentication failed. Please check your credentials. Error: {e}")