#!/usr/licensed/anaconda3/2023.3/bin/python -uB

import os
import subprocess
import pandas as pd
from base64 import b64decode
from dossier import get_position_from_lines
from dossier import clean_position

use_cache = False

if not os.path.exists(f"{os.getcwd()}/cache"):
    os.mkdir(f"{os.getcwd()}/cache")

depts = {"Lewis-Sigler Institute for Integrative Genomics":"LSI",
        "Chemical and Biological Engineering":"CBE",
        "Electrical and Computer Engineering":"ECE",
        "Molecular Biology":"MOLBIO"}

alphabet = "abcdefghijklmnopqrstuvwxyz"
assert len(alphabet) == 26
digits = "0123456789"
assert len(digits) == 10
uid_starts = [f"{alpha}{alphanum}" for alpha in alphabet for alphanum in alphabet + digits]

depts = {'Psychology':'PSYCH'}
depts = {'Princeton Neuroscience Institute':'PNI'}
depts = {"Electrical and Computer Engineering":"ECE"}
depts = {'Mechanical and Aerospace Engineering':'MAE'}
depts = {"Chemical and Biological Engineering":"CBE"}
depts = {'Civil and Environmental Engineering':'CEE'}
depts = {'Chemistry':'CHEM'}
depts = {'Computer Science':'CS'}

separator_count = 0
uid_count = 0
persons_in_dept = []
for dept in depts:

    for uid_start in uid_starts:

        outfile = f"cache/{depts[dept]}_{uid_start}.txt"
        if not use_cache:
            #cmd = f"ldapsearch -x '(&(uid={uid_start}*)(ou={dept}))'"
            cmd = f"ldapsearch -x '(&(uid={uid_start}*)(|(ou={dept})(puresidentdepartment={dept}))(|(puresource=authentication=enabled)(puresource=authentication=goingaway)))'"
            output = subprocess.run(cmd, stdout=subprocess.PIPE, shell=True, timeout=10, text=True, check=True)
            lines = output.stdout.split('\n')
            if lines != [] and lines[-1] == "": lines = lines[:-1]
            with open(outfile, "w") as f:
                for line in lines:
                    if "numResponses: 201" in line or "Size limit exceeded" in line:
                        print("WARNING:", dept, uid_start, line)
                    f.write(f"{line}\n")
        with open(outfile) as f:
            lines = f.readlines()

        person = {}
        lines_person = []
        for line in lines:
            if (", Princeton University, US".lower() in line.lower()) or ("numResponses: " in line):
                if ", Princeton University, US".lower() in line.lower():
                    separator_count += 1
                if person:
                    person["position"] = get_position_from_lines(lines_person)
                    person["dept"] = dept
                    persons_in_dept.append(person)
                person = {}
                person["name"] = "UNKNOWN"
                person["position"] = "UNKNOWN"
                person["account"] = "UNKNOWN"
                person["shell"] = "UNKNOWN"
                person["employee"] = "UNKNOWN"
                lines_person = []
            lines_person.append(line)
            if "puresource: authentication=" in line:
                person['account'] = line.split("=")[-1].strip()
            if "loginShell: " in line:
                person['shell'] = line.split(":")[-1].strip()
            if "pustatus: " in line:
                person['status'] = line.split(":")[-1].strip()
            if "displayName: " in line:
                person['name'] = line.split(":")[-1].strip()
            if "displayName:: " in line:
                person['name'] = b64decode(line.split("::")[-1].strip()).decode("utf-8")
            if "pupublishedemailaddress: " in line:
                person['email'] = line.split(":")[-1].strip()
            if "uid: " in line:
                person['uid'] = line.split(":")[-1].strip()
                uid_count += 1
            if "employeeNumber: " in line:
                person['employee'] = line.split(":")[-1].strip()

if (separator_count != uid_count):
    print(f"WARNING: separator count ({separator_count}) does not equal uid count ({uid_count}).")

# write out csv file for each department
lp = []
for person in persons_in_dept:
    lp.append([person["uid"], person["name"], person["position"], person["dept"], person["shell"], person["account"], person["employee"]])

df = pd.DataFrame(lp, columns=["uid", "name", "position", "dept", "shell", "account", "employee"])
df["lastname"] = df["name"].apply(lambda x: x.split()[-1])
df["cleanpos"] = df["position"].apply(lambda x: clean_position(x, level=3))
df = df.sort_values("lastname")
df.to_csv("persons.csv", index=False)
pd.set_option('display.max_rows', None)
print(df[df.position.str.contains("UNK")])
print("rows=", df.shape[0])

persons = df.copy()
persons = persons[persons.account == "enabled"].sort_values(by=["position", "lastname"])
print(persons)
print(persons.position.value_counts())

#persons = persons[(persons.account != "disabled") & persons.position.str.contains("G") & (persons.position != "G0")]
#persons = persons[(persons.account != "disabled") & (~persons.position.str.contains("G"))]
#persons = persons[(persons.account == "enabled") & persons.position.str.contains("G") & (persons.position != "G0") & (~persons.position.str.contains("XGraduate")) & (~persons.position.str.contains("Graduate"))]

# faculty
faculty = persons[persons.position.str.contains("Faculty") & (~persons.position.str.contains("visiting"))].reset_index(drop=True).copy()
faculty.index += 1
print(faculty)

# postdocs
postdocs = persons[(persons.position.str.contains("Postdoc")) & (~persons.position.str.contains("visiting"))].reset_index(drop=True).copy()
postdocs.position = "Postdoc"
postdocs = postdocs.sort_values("lastname")
postdocs.index += 1
print(postdocs)

# graduate students (excluding G0)
grad = persons[persons.position.str.match("G[1-9]")].reset_index(drop=True).copy()
grad.index += 1
print(grad)
print(grad.position.value_counts().sort_index())
