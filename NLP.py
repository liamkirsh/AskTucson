import re, nltk, calendar
import sys
import json
from datetime import datetime, date, time, timedelta

DEBUG = False 

# flags=re.IGNORECASE
remind_patterns = [r'\b(remind|tell|send)\s+me', # "Remind me"
					r'\blet\s+me\s+know\b'] # "Let me know"
sendlater_patterns = [r'\b(?:remind|tell|email|send)\s+([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})', # "Remind x@y.z"
						r'\b(?:email|send)\b(?:(?!to).)*to\s+\b([A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,})'] # "Send a message to x@y.z"
#default: today
day_patterns = [r'(\bnext\s)?((?:Sun|Mon|Tues|Wednes|Thurs|Fri|Satur)day)\b', # Sunday, next Sunday, on Friday
				r'\btomorrow\b',
				r'(?:in a |next )(week|month|year)']

date_patterns = [r'\b(?:(Jan)\.?(?:uary)?|(Feb)\.?(?:ruary)?|(Mar)\.?(?:ch)?|(Apr)\.?(?:il)?|(May)|(Jun)\.?(?:e)?|(Jul)\.?(?:y)?|(Aug)\.?(?:ust)?|(Sep)\.?t?\.?(?:ember)?|(Oct)\.?(?:ober)?|(Nov)\.?(?:ember)?|(Dec)\.?(?:ember)?) (\d+)(?:st|nd|rd|th)?(?:,? (\d+))?', # this has a ton of empty groups that need to be ignored.
				r'(\b\d+\/\d+(?:\/\d+)?)\b'] # 1/16/16 or 01/16/16, 01/16/2016, 2/24, etc.
				
# Note placement of 'midnight' before 'night' to avoid conflicts
gen_times = [('tonight', 21), ('morning', 9), ('noon', 12), ('afternoon', 15), ('evening', 18), ('midnight', 0), ('night', 21)]

spec_times = [r'\bat\s(half past\s|a quarter past\s)?(\d)+(?::(\d+))?\s?(am|pm)?']
			#r'\b(half past\s|a quarter past\s)?(\d)+(?::(\d+))?\s?(am|pm)?'] # try without the 'at' if it's not found initially

period = r'in (an?|\d+)? (minutes?|hours?)'
 
days = {'sunday':6, 'monday':0, 'tuesday':1, 'wednesday':2, 'thursday':3, 'friday':4, 'saturday':5}
months = {'jan':1, 'feb':2, 'mar':3, 'apr':4, 'may':5, 'jun':6, 'jul':7, 'aug':8, 'sep':9, 'oct':10, 'nov':11, 'dec':12}

message_pattern = r'"([^"]+)"'

# Solution by phihag <http://stackoverflow.com/users/35070/phihag>. Used under a CC-By-SA 3.0 license.
# http://stackoverflow.com/a/6558571
def next_weekday(d, weekday):
	days_ahead = weekday - d.weekday()
	if days_ahead <= 0: # Target day already happened this week
		days_ahead += 7
	return d + timedelta(days_ahead)

# Solution by Dave Webb <http://stackoverflow.com/users/3171/dave-webb>. Used under a CC-By-SA 3.0 license.
# http://stackoverflow.com/a/4131114
def add_months(sourcedate, months):
	month = sourcedate.month - 1 + months
	year = int(sourcedate.year + month / 12)
	month = month % 12 + 1
	day = min(sourcedate.day, calendar.monthrange(year, month)[1])
	return date(year, month, day)
	
# Solution by Gareth Rees <http://stackoverflow.com/users/68063/gareth-rees>. Used under a CC-By-SA 3.0 license.
# http://stackoverflow.com/a/15743908
def add_years(d, years):
    """Return a date that's `years` years after the date (or datetime)
    object `d`. Return the same calendar date (month and day) in the
    destination year, if it exists, otherwise use the following day
    (thus changing February 29 to March 1).

    """
    try:
        return d.replace(year = d.year + years)
    except ValueError:
        return d + (date(d.year + years, 1, 1) - date(d.year, 1, 1))

def parseQuery(query):
	#email = re.findall(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', q)
	#q = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b', 'Userxx', q) # Replace email address with 'User"
	#parsed = nltk.word_tokenize(q)
	#parts = nltk.pos_tag(parsed)
	email = ""
	q = query.split("/\r?\n/")[0]
	# First check for reminder format
	qType = -1 # 0 for reminder, 1 for sendlater
	minNdx = float('inf')
	recipient = None
	for pat in remind_patterns:
		match = re.search(pat, q, re.IGNORECASE)
		if match and match.start() < minNdx:
			qType = 0
			minRemindNdx = match.start()			

	for pat in sendlater_patterns:
		match = re.search(pat, q, re.IGNORECASE)
		if match and match.start() < minNdx:
			qType = 1
			minRemindNdx = match.start()
			email = match.group(1)
			
	# Figure out the date and time
	# default: today at noon
	d = date.today()
	t = time(12, 00)
	#dt = datetime.combine(d, t)
	
	# Look for a day pattern
	match = re.search(day_patterns[0], q, re.IGNORECASE)
	if match:
		groups = [group for group in match.groups() if group]
		# For next, use the next xday after the Sunday following today
		if match.group(1): # next
			# Find the following Sunday after today
			sunday = next_weekday(date.today(), calendar.SUNDAY)
			d = next_weekday(sunday, days[groups[1].lower()])
		else: # this week
			# Find the following xday after today
			d = next_weekday(date.today(), days[groups[0].lower()])
	else:
		match = re.search(day_patterns[1], q, re.IGNORECASE)
		if match: # tomorrow
			d += timedelta(1) # add one day to today
		else:
			match = re.search(day_patterns[2], q, re.IGNORECASE)
			if match: # in a week/month/year, next week/month/year
				if match.group(1).lower() == "week":
					d += timedelta(7)
				elif match.group(1).lower() == "month":
					d = add_months(d, 1)
				elif match.group(1).lower() == "year":
					d = add_years(d, 1)
				else:
					print "ERR: invalid date entered"
					sys.exit(100)
			else:
				# day patterns did not work. Look for a specific date.
				d = parse_date(d, q)
	
	# Now, let's figure out the time
	tSet = False
	for tm in gen_times:
		if tm[0] in q.lower():
			t = time(tm[1], 00)
			tSet = True
			break
	
	if not tSet:
		for tm in spec_times:
			match = re.search(tm, q, re.IGNORECASE)
			if match:
				if match.group(0) == "half past":
					mins = 30
				elif match.group(0) == "a quarter past":
					mins = 15
				else:
					mins = int(match.group(3)) if match.group(3) else 00
				
				hrs = int(match.group(2))
				if match.group(4).lower() == "pm":
					hrs += 12
				t = time(hrs, mins)
				tSet = True
				break
	
	if not tSet: #still no? try checking for 'in a minute' or 'in an hour'
		match = re.search(period, q, re.IGNORECASE)
		if DEBUG:
			print 'checking for in a minute/hour'
		if match:
			if DEBUG:
				print 'matched!'
			now = datetime.now()
			if match.group(1) == "a" or match.group(1) == "an":
				quantity = 1
			else:
				quantity = int(match.group(1))
				print 'quantity:', quantity
			if match.group(2).startswith("minute"):
				t = (now + timedelta(minutes = quantity)).time()
			elif match.group(2).startswith("hour"):
				t = (now + timedelta(hours = quantity)).time()
				
			if t.hour == 0: # it's the dawn of a new day
				d += timedelta(1)
		
	
	#print "Date:", str(d)
	#print "Time:", str(t)
	message = re.search(message_pattern, q).group(1)
	
	if qType == 0:
		theType = 'reminder'
	elif qType == 1 and email:
		theType == 'sendlater'
		#print 'email: %s' % email
	else:
		print 'err'
	result = {"date": str(d), "time": str(t), "type": theType, "email": email, "message": message}
	print json.dumps(result)
	sys.stdout.flush
	sys.exit(0)
	
	# First, determine whether it is a reminder or a sendlater
	#for pattern in remind_patterns:

def parse_date(today, q):
	match = re.search(date_patterns[0], q)
	if match:
		# full date spelled out
		if DEBUG:
			print 'full date spelled out'
		groups = [group for group in match.groups() if group]
		month = months[groups[0].lower()]
		day = groups[1]
		year = groups[2] if len(groups) > 2 else datetime.now().year
		
		return datetime.strptime("%s-%s-%s" % (month, day, year), "%m-%d-%Y")
	else:
		match = re.search(date_patterns[1], q)
		if match:
			dat = match.group(1)
			spl = dat.split('/')
			# mm/dd or mm/dd/yy or mm/dd/yyyy format
			if len(spl) == 2:
				year = datetime.now().year
				return datetime.strptime("%s/%s" % (dat, year), "%m/%d/%Y")
			else: #len == 3
				yrLen = len(spl[2])
				if DEBUG:
					print spl
				if yrLen == 2: # extend year to 4-digit format
					dat = "%s/%s/20%s" % (spl[0], spl[1], spl[2])
				return datetime.strptime(dat, "%m/%d/%Y")
		else: return today
	
while True:		
	query = raw_input()
	parseQuery(query)
