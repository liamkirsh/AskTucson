import re, nltk

# flags=re.IGNORECASE
remind_patterns = [r'\b(remind|tell|send)\s+me', # "Remind me"
					r'\blet\s+me\s+know\b'] # "Let me know"
sendlater_patterns = [r'\b(?:remind|tell|email|send)\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', # "Remind x@y.z"
						r'\b(?:email|send)\b(?:(?!to).)*to\s+\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})'] # "Send a message to x@y.z"

def parseQuery(q):
	#email = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', q)
	#q = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', 'Userxx', q) # Replace email address with 'User"
	#parsed = nltk.word_tokenize(q)
	#parts = nltk.pos_tag(parsed)

	# First check for reminder format
	qType = -1 # 0 for reminder, 1 for sendlater
	minNdx = float('inf')
	recipient = None
	for pat in remind_patterns:
		match = re.search(pat, q)
		if match and match.start() < minNdx:
			qType = 0
			minRemindNdx = match.start()			

	for pat in sendlater_patterns:
		match = re.search(pat, q)
		if match and match.start() < minNdx:
			qType = 1
			minRemindNdx = match.start()
			email = match.group(1)

	if qType == 0:
		print 'reminder'
	elif qType == 1 and email:
		print 'sendlater'
		print 'email: %s' % email
	else:
		print 'err'
	
	# First, determine whether it is a reminder or a sendlater
	#for pattern in remind_patterns:

while True:		
	query = raw_input()
	parseQuery(query)
