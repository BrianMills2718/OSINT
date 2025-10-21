import re

pattern = r'\$[\d,]+(?:\.\d+)?(?:\s*(?:million|billion|thousand|M|B|K))?|\b\d+(?:\.\d+)?\s*(?:million|billion|thousand)\s*(?:dollars|USD)?'
text = 'On January 15, 2024, the investigation revealed $2.5 million in transactions.'
matches = re.findall(pattern, text)
print('Money matches:', matches)