import os
import sys
import requests
import json

men = {}
women = {}

mp = {}
wp = {}

md = {}
wd = {}
step = 20

for i in range(80):
    mp[i+1] = [0, 0]
    wp[i+1] = [0, 0]

def do_read(fname, d, dp):
    with open(fname, 'r') as f:
        lines = f.readlines()
        for index, l in enumerate(lines):
            if '[' in l:
                parts = l.split()
                rank, name = parts[0], parts[1]
                if l[-2] == ']':
                    last_num = ' '.join([rank, name])
                    r = int(rank)
                    d[last_num] = [parts[-1], parts[1:-1], None]
                else:
                    d[last_num][2] = int(parts[-2])
                    for p in parts[:-3]:
                        if len(p) < 5:
                            continue
                        pp = p[:-1].split('[')
                        prob, points = int(pp[0]), int(pp[1])

                        ddd = md if fname == 'qm.txt' else wd
                        slot = r - (r - 1) % step

                        if slot not in ddd:
                            ddd[slot] = [0 for i in range(80)]

                        ddd[slot][prob-1] = ddd[slot][prob-1] + 1

                        if p[4] == '0':
                            dp[prob][1] = dp[prob][1] + 1
                        else:
                            dp[prob][0] = dp[prob][0] + 1
                            
                            
def rn(i):
    return i[3], i[4]


def rr(i):
    return i[5]


def print_ranking(d):
    all = []
    for k, v in d.items():
        all.append([k, v[0], v[1], v[2], v[3][0] * v[3][1] * v[3][2], v[3]])
    all.sort(key=rn)
    for i in all:
        print("%30s %s %s %s %8d" % (i[0], i[1], i[2], i[3], i[4]), i[5])
        

def read_ranking(category, d, c, gender):
    url = 'https://ifsc-egw.wavecdn.net/egw/ranking/json.php'
    params = {'type': 'ranking', 'cat': category}
    r = requests.get(url = url, params = params)

    if r.status_code == 200:
        results = r.json()
        for p in results['participants']:
            n = p['firstname'].lower() + '_' + p['lastname'].lower()
            print('name', n)
            if n not in d:
                d[n] = [p['nation'], p['birthyear'], gender, [999, 999, 999]]
            assert d[n][3][c] == 999
            d[n][3][c] = p['result_rank']


def match_name(comps, fn):
    highest = 2
    best = None
    for k in comps.keys():
        count = 0
        for letter in fn:
            if letter in k:
                count += 1
        if count > highest:
            best = k
            highest = count
    percentage = highest * 100 / len(fn)
                
    ignore = [
        ['lucie_d', 'lucia_d'],
        ['radin_f', 'reza_ali'],
        ['mauro_m', 'michael_p'],
        ['stefano_collin', 'stefano_ghis'],
        ['stefano_magnoni', 'stefano_ghis'],
        ['christoph_brockt', 'christoph_hanke'],
        ['andreas_brodmann', 'alexander_megos'],
    ]
    if percentage > 90 and fn[0] == best[0]:
        for i in ignore:
            if fn.startswith(i[0]) and best.startswith(i[1]):
                return [None, percentage]
        return [best, percentage]
    else:
        return [None, percentage]
        

def print_signups(fname, comps):
    slots = []

    with open(fname, 'r') as f:
        lines = f.readlines()
        gender = 'u'
        for line in lines:
            if 'WOMEN' == line.strip():
                gender = 'f'
            elif 'MEN' == line.strip():
                gender = 'm'
            parts = line.split()
            if not line[0].isdigit() or not (3 < len(parts) < 8):
                continue
            # assert 3 < len(parts) < 8, str(parts)
            fn = parts[1].lower() + '_' + parts[-3].lower()
            n, per = match_name(comps, fn)
            if n:
                if comps[n][0][:2] == parts[-1][:2]:
                    # print(comps[n][0] + '_' + parts[-1] + '_' + n + '_' + fn + '-' + str(per))
                # print(parts[-1][1])
                # else:
                    info = [parts[-2], parts[-1], gender, fn, n, min(comps[n][3])]
                    if info in slots:
                        pass
                        # print('Skipping duplicate ### ', info)
                    else:
                        slots.append(info)
    mc = 0
    wc = 0
    slots.sort(key=rr)
    for slot in slots:
        if slot[2] == 'm':
            mc += 1
        else:
            wc += 1
        print(slot)
    print('%d men %d women %d total' % (mc, wc, mc+wc))


do_read('qm.txt', men, mp)
do_read('qw.txt', women, wp)

rankings = {}

CACHE_FILENAME = 'cached_rankings.json'
try:
    with open(CACHE_FILENAME, 'r') as f:
        rankings = json.loads(f.read())
        new_dict = {}
        for k, v in rankings.items():
            new_dict[k.lower()] = v
        rankings = new_dict
except FileNotFoundError:
    read_ranking('ICC_MB', rankings, 0, 'M')
    read_ranking('ICC_FB', rankings, 0, 'F')
    read_ranking('ICC_M', rankings, 1, 'M')
    read_ranking('ICC_F', rankings, 1, 'F')
    read_ranking('ICC_MS', rankings, 2, 'M')
    read_ranking('ICC_FS', rankings, 2, 'F')
    with open(CACHE_FILENAME, 'w') as f:
        f.write(json.dumps(rankings))

# print_ranking(rankings)
print_signups('qm210.txt', rankings)

def do_print(desc, d):
    for k in sorted(d.keys()):
        print(desc + ', ' + str(k) + ', ' + str(d[k])[1:-1])

# do_print('men', men)
# do_print('women', women)
# do_print('mp', mp)
# do_print('wp', wp)

def print_comp(desc, d):
    for k, v in d.items():
        fn = v[1][0] + '_' + v[1][1]
        fn = fn.lower()
        n, per = match_name(rankings, fn)
        if n:
            c = rankings[n]
            # print('Not equal %s %s %s %s' % (str(v[0]), str(c), fn, n))
            if v[0][1:-1] == c[0]:
                print("%3s %30s %30s %5s %3d %4d %4d %4d" % (k.split()[0], n, fn, v[0], v[2], c[3][0], c[3][1], c[3][2]))
            # else:
            #     print(v[0][1:-1], c[0], fn, n)

print_comp('men', men)
print_comp('women', women)

# do_print('men', md)
# do_print('women', wd)

def print_country(desc, d):
    countries = {}
    for k, v in d.items():
        c = v[0][1:-1]
        if c not in countries:
            countries[c] = []
        countries[c].append([(k.split()[0]), v[2]])
    for k, v in countries.items():
        ranks = 0
        points = 0
        allpoints = []
        for item in v:
            ranks += int(item[0])
            points += item[1]
            allpoints.append(item[1])
        print(desc, k, 100 - int(100.0 * ranks / len(v) / len(d)), int(points / len(v)), '(' + str(len(v)) + ')')

# print_country('men', men)
# print_country('women', women)
