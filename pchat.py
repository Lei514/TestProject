from dateutil import parser
from datetime import datetime, timedelta
import sys

chats = []

last_person = None
last_time = None

ignore_words = ['will', 'so', 'more', 'one', 'the', 'a', 'as', 'but', 'have', 'with', 'is', 'of', 'am', 'for', 'in', 'to', 'that', 'it', 'at', 'this', 'on', 'and', 'or', 'was', 'be', 'are', 'from']
include_words = ['feel', 'love', 'like', 'need', 'work', 'hope', 'happy', 'glad']
WORD_CUTOFF = 70

EXCLUDE_HOURS = {
    'Lei': [5, 12],
    'San': [2, 9],
    'Default': [2, 12]
}

word_frequency = {}

FIRST_MSG_TIME_CUTOFF_HOUR = 3

GROUP_MINUTES = 15


def exclude_start(pname, hour):
    key = pname[:3]
    if key not in EXCLUDE_HOURS:
        key = 'Default'
    return EXCLUDE_HOURS[key][0] <= hour <= EXCLUDE_HOURS[key][1]


def add_words(words, person):
    for p in words:
        pl = p.lower()
        if pl not in word_frequency[person]:
            word_frequency[person][pl] = 0
        word_frequency[person][pl] += 1


def process_line(msg, has_attachment):
    assert len(msg) > 0
    parts = msg[0].split(': ')
    t, person = parts[0].split(' - ')
    if person not in word_frequency:
        word_frequency[person] = {}
    if has_attachment:
        count = 0
    else:
        pp = parts[1].split()
        count = len(pp)
        add_words(pp, person)
            
    for l in msg[1:]:
        pp = l.split()
        count += len(pp)
        add_words(pp, person)

    tt = parser.parse(t)
    global last_person
    global last_time
    filtered_gap = ''
    gap = ''
    if person != last_person:
        if last_person:
            gap = str(int((tt - last_time).seconds / 60))
            if not exclude_start(person, tt.hour):
                filtered_gap = gap
    last_person = person
    last_time = tt
    chats.append([tt, person, str(count), '1' if has_attachment else '0', gap, filtered_gap])


def daymin(t):
    return t.hour * 60 + t.minute

def round_date(d, round_type):
    day_num = (d.date().toordinal() - 730311) % 7
    if round_type == 'weekday':
        return WEEKDAYS[day_num]
    elif round_type == 'week':
        return d.date() - timedelta(days=day_num)
    elif round_type == 'month':
        return datetime(d.year, d.month, 1)
    elif round_type == 'year':
        return datetime(d.year, 1, 1)
    elif round_type == 'day':
        return d.date()
    else:
        assert Fail, 'Unsupported rounding: ' + str(round_type)

def initial_letters(all_persons):
    max_length = 0
    for person in all_persons:
        if len(person) > max_length:
            max_length = len(person)

    for i in range(max_length):
        new_dict = set()
        for person in all_persons:
            new_dict.add(person[:i+1])
        if len(all_persons) == len(new_dict):
            return i+1
    assert False, 'too many letters'


LIST_TYPES = ['weekday', 'month', 'week', 'day']
WEEKDAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday']


def rs(i):
    return i[2]


def print_history(chats):
    persons = set()
    for c in chats:
        persons.add(c[1])
    initials = initial_letters(persons)
    headers = ['word']
    total = {}
    highest = {}
    uniqs = {}
    for person in persons:
        headers.append(person[:initials])
        headers.append(person[:initials] + '_normalized')
        highest[person] = 0
        total[person] = 0
        uniqs[person] = set()
    int_words = []
    for person, counts in word_frequency.items():
        for k, v in counts.items():
            total[person] += v
            uniqs[person].add(k)
    for person, counts in word_frequency.items():
        items = []
        for k, v in counts.items():
            if (k not in ignore_words and v > WORD_CUTOFF) or (k in include_words):
                if v > highest[person]:
                    highest[person] = v
                items.append([person, k, v])
        items.sort(key=rs)
        items.reverse()
        for i in items:
            if i[1] not in int_words:
                int_words.append(i[1])
    info = ['num_words']
    for person in persons:
        info.append(str(total[person]))
    print(','.join(info))
    info = ['unique_words']
    for person in persons:
        info.append(str(len(uniqs[person])))
    print(','.join(info))
    print(','.join(headers))

    for word in int_words:
        info = [word]
        for person in persons:
            info.append(str(word_frequency[person][word]))
            info.append("%5.2f" % (100 * word_frequency[person][word]/highest[person]))
        print(','.join(info))
    print('\n\n\n\n')

    earliest = datetime(2099, 1, 1)
    latest = datetime(2000, 1, 1)
    for c in chats:
        if c[0] < earliest:
            earliest = c[0]
        if c[0] > latest:
            latest = c[0]

    lists = {}
    for list_type in LIST_TYPES:
        d = {}
        lists[list_type] = d
        if list_type == 'weekday':
            for weekday in WEEKDAYS:
                d[weekday] = []
            for c in chats:
                key = round_date(c[0], 'weekday')
                d[key].append(c)
        else:
            day = earliest
            while day <= latest:
                day_rounded = round_date(day, list_type)
                if day_rounded not in d:
                    d[day_rounded] = []
                day = day + timedelta(days=1)
            for c in chats:
                key = round_date(c[0], list_type)
                d[key].append(c)

    for list_type in LIST_TYPES:
        d = lists[list_type]

        headers = ['first', 'msgs', 'batches', 'words', 'attachments', 'delay',
                   'quick_10min', 'subhour', '3hours+']
        print_headers = ['start_date']
        for h in headers:
            for p in persons:
                print_headers.append(p[:initials] + '_' + h)
        print(','.join(print_headers))

        batch_dict = {}
        for person in persons:
            batch_dict[person] = {}
            for i in range(20):
                batch_dict[person][i] = 0

        for k, v in d.items():
            msgs = {}
            first_times = {}
            delays = {}
            last_min = {}
            for person in persons:
                msgs[person] = {
                    "first_time": '',
                    "msg_count": 0,
                    "batch_count": 0,
                    "word_count": 0,
                    "attach_count": 0,
                    "average_delay": '',
                    "quick_reply": 0,
                    "hour_reply": 0,
                    "hour3_reply": 0
                }
                first_times[person] = {}
                delays[person] = []
                last_min[person] = -1000

            for item in v:
                person = item[1]
                msgs[person]['msg_count'] += 1
                msgs[person]['word_count'] += int(item[2])
                if daymin(item[0]) - last_min[person] > GROUP_MINUTES:
                    msgs[person]['batch_count'] += 1
                last_min[person] = daymin(item[0])
                if item[3] == '1':
                    msgs[person]['attach_count'] += 1
                if item[4] and item[0].hour >= FIRST_MSG_TIME_CUTOFF_HOUR:
                    delays[person].append(int(item[4]))
                day_number = item[0].toordinal()
                if day_number not in first_times[person] and item[0].hour >= FIRST_MSG_TIME_CUTOFF_HOUR:
                    first_times[person][day_number] = item[0].hour * 60 + item[0].minute

            average_delay = {}
            quick = {}
            hour1 = {}
            hour3 = {}
            hour3plus = {}
            for person in persons:
                average_delay[person] = ''
                quick[person] = 0
                hour1[person] = 0
                hour3[person] = 0
                hour3plus[person] = 0
            for person in persons:
                dd = delays[person]
                if len(dd) > 0:
                    average_delay[person] = str(int(sum(dd) / len(dd)))
                    for delay in dd:
                        if delay <= 10:
                            quick[person] += 1
                        if delay <= 60:
                            hour1[person] += 1
                        if delay <= 180:
                            hour3[person] += 1
                        else:
                            hour3plus[person] += 1
                    quick[person] = str(int(100 * quick[person] / len(dd)))
                    hour1[person] = str(int(100 * hour1[person] / len(dd)))
                    hour3[person] = str(int(100 * hour3[person] / len(dd)))
                    hour3plus[person] = str(int(100 * hour3plus[person] / len(dd)))
            first_time = {}
            for person in persons:
                first_time[person] = ''
                ft = first_times[person]
                if len(ft) > 0:
                    minute = int(sum(ft.values()) / len(ft))
                    hour = int(minute / 60)
                    minute = minute % 60
                    minute_print = str(minute) if minute >= 10 else '0' + str(minute)
                    ampm = 'am' if hour < 12 else 'pm'
                    hour = hour if hour <= 12 else hour - 12
                    hour_print = str(hour) if hour >= 10 else '0' + str(hour)
                    first_time[person] = '%s:%s%s' % (hour_print, minute_print, ampm)

            if list_type == 'day':
                for person in persons:
                    assert 'batch_count' in msgs[person], msgs[person]
                    batch_dict[person][msgs[person]['batch_count']] += 1
            print_list = [k]
            for person in persons:
                print_list.append(first_time[person])
            for person in persons:
                print_list.append(msgs[person]['msg_count'])
            for person in persons:
                print_list.append(msgs[person]['batch_count'])
            for person in persons:
                print_list.append(msgs[person]['word_count'])
            for person in persons:
                print_list.append(msgs[person]['attach_count'])
            for person in persons:
                print_list.append(average_delay[person])
            for person in persons:
                print_list.append(quick[person])
            for person in persons:
                print_list.append(hour1[person])
            for person in persons:
                print_list.append(hour3plus[person])

            # print_list = [str(k), first_time, str(len(v)), str(batch_count), str(word_count),
            #               str(attach_count), average_delay, quick, hour1, hour3plus]
            output = ''
            for i in print_list:
                output += str(i) + ','
            print(output[:-1])
        if list_type == 'day':
            headers = ['batches']
            for person in persons:
                headers.append(person[:initials] + '_' + 'batch_count')
            print(','.join(headers))
            for k in range(20):
                info = [str(k)]
                for person in persons:
                    info.append(str(batch_dict[person][k]))
                print(','.join(info))
        print('\n\n\n\n\n')


if len(sys.argv) != 2:
    print('Usage:\n     python pchat.py messages.txt')
    # infile = '/Users/lei/sbm/wsml.txt'
    infile = '/Users/lei/sbm/sml211.txt'
else:
    infile = sys.argv[1]

with open(infile, 'r') as f:
    lines = f.readlines()
    msg = []
    has_attachment = False
    got_header = False
    for line in lines:
        line = line.strip()
        if not got_header and 'Messages to this chat and calls are now secured with end-to-end encryption' in line:
            got_header = True
            continue
        if 13 < line.find('M - ') < 18:
            if len(msg) > 0:
                process_line(msg, has_attachment)
            has_attachment = line.endswith('(file attached)') or line.endswith('<Media omitted>')
            msg = [line]
        else:
            assert line.find('/') == -1 or line.find(',') == -1 or line.find(' - ') == -1 or line.find(': ') == -1, \
                line + '_' + str(line.find('/')) + '_' + str(line.find(',')) + '_' + str(line.find(' - ')) + \
                '_' + str(line.find(': ')) + 'N' + str(line.find('M - '))
            msg.append(line)
    process_line(msg, has_attachment)

print_history(chats)
