import os
import sys
import shutil
import json
import yaml
import git
from json.decoder import JSONDecodeError

def get_intent_list():
    with open('./intent.txt', 'r') as data_file:
        json_data = data_file.read()
    data = json.loads(json_data)
    return data

def get_version_from_branch(branch_name, spec_file_name):
    spec_content = {}
    with open(branch_name + '/' + spec_file_name, 'r') as spec_content:
        spec_content = yaml.safe_load(spec_content)
    return spec_content['info']['version']

def minor_bump(version):
    major, minor, patch = version.split('.')
    return major + '.' + str(int(minor) + 1) + '.' + patch
    
def major_bump(version):
    major, minor, patch = version.split('.')
    return str(int(major) + 1) + '.' + '0' + '.' + patch

def is_less_than(version1, version2):
    version1 = version1.replace('.', '')
    version2 = version2.replace('.', '')
    return version1 < version2

def compute_version(intent, latest_release_version, target_branch_version):
    next_version = None
    if intent == 'minor':
        next_version = minor_bump(latest_release_version) 
    else:
        next_version = major_bump(latest_release_version)
    if is_less_than(next_version, target_branch_version):
        next_version = target_branch_version
    return next_version

# Clone master and latest_release branch from remote
target_branch = str(sys.argv[1])

intent_list = get_intent_list()

internal_intent = None
external_intent = None

for intent in intent_list:
    if intent['file'] == 'internal.yml':
        if internal_intent == None:
            internal_intent = intent['intent']
        else:
            if intent['intent'] == 'major':
                internal_intent = intent['intent']
    else:
        if external_intent == None:
            external_intent = intent['intent']
        else:
            if intent['intent'] == 'major':
                external_intent = intent['intent']

release_path = './release'
target_path = './' + target_branch

if os.path.exists(release_path):
    shutil.rmtree(release_path)

if os.path.exists(target_path):
    shutil.rmtree(target_path)

os.mkdir(release_path)
os.mkdir(target_path)

clone_repo_target = None
clone_repo_release = None

clone_repo_target = git.Repo.clone_from('https://github.com/vivian-fan/version-bump-test.git', target_path, branch=target_branch)

release_branches = []

for branch in clone_repo_target.refs:
    if branch.__str__().startswith('origin/production_release'):
        release_branches.append(branch.__str__())
release_branches.sort()
latest_release_branch = release_branches[-1].replace('origin/', '')
clone_repo_release = git.Repo.clone_from('https://github.com/vivian-fan/version-bump-test.git', release_path, branch=latest_release_branch)

# Compute next version
next_version_external = None
next_version_internal = None

if external_intent != None:
    latest_release_version = get_version_from_branch('./release', 'external.yml')
    target_branch_version = get_version_from_branch('./' + target_branch, 'external.yml')
    next_version_external = compute_version(external_intent, latest_release_version, target_branch_version)
    print(latest_release_version, target_branch_version, external_intent, next_version_external)

if internal_intent != None:
    latest_release_version = get_version_from_branch('./release', 'internal.yml')
    target_branch_version = get_version_from_branch('./' + target_branch, 'internal.yml')
    next_version_internal = compute_version(internal_intent, latest_release_version, target_branch_version)
    print(latest_release_version, target_branch_version, internal_intent, next_version_internal)

# Accumulate intents
intents_obj = None

intents_file = open('./.github/intent.json', 'r+')

try:
    intents_obj = json.load(intents_file)
except JSONDecodeError:
        pass

if intents_obj == None:
    intents_obj = {
        "internal":[],
        "external":[]
    }
for intent in intent_list:
    if intent['file'] == 'internal.yml':
        intents_obj["internal"].append(intent)
    else:
        intents_obj["external"].append(intent)
intents_file.seek(0)
json.dump(intents_obj, intents_file)
intents_file.truncate()

shutil.rmtree(release_path)
shutil.rmtree(target_path)

print(next_version_internal, 'internal.yml', next_version_external, 'external.yml', internal_intent, external_intent)

try:
    repo = git.Repo('.')
    repo.git.add(update=True)
    repo.index.commit('accumulate intent')
    repo.git.push("origin", target_branch)
except Exception as e:
    print('Errors occured while pushing the code', e) 
