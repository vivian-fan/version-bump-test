import os
import sys
import shutil
import json
import yaml
import git
from json.decoder import JSONDecodeError

def get_intent_object():
    f = open('./intent.json')
    intent_obj = json.load(f)
    return intent_obj

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

    resi/y

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
intent_obj = get_intent_object()

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

clone_repo_target = git.Repo.clone_from('https://github.com/vivian-fan/version-bump-poc.git', target_path, branch=target_branch)

release_branches = []

for branch in clone_repo_target.refs:
    if branch.__str__().startswith('origin/production_release'):
        release_branches.append(branch.__str__())
release_branches.sort()
latest_release_branch = release_branches[-1].replace('origin/', '')
clone_repo_release = git.Repo.clone_from('https://github.com/vivian-fan/version-bump-poc.git', release_path, branch=latest_release_branch)

# Compute next version
intent = intent_obj['intent']
latest_release_version = get_version_from_branch('./release', intent_obj['file'])
target_branch_version = get_version_from_branch('./' + target_branch, intent_obj['file'])
next_version = compute_version(intent, latest_release_version, target_branch_version)

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
if intent_obj['file'] == 'internal.yml':
    intents_obj["internal"].append(intent_obj)
else:
    intents_obj["external"].append(intent_obj)
intents_file.seek(0)
json.dump(intents_obj, intents_file)
intents_file.truncate()

shutil.rmtree(release_path)
shutil.rmtree(target_path)

print(next_version, intent_obj['file'])

try:
    repo = git.Repo('.')
    repo.git.add(update=True)
    repo.index.commit('accumulate intent')
    repo.git.push("origin", target_branch)
except Exception as e:
    print('Errors occured while pushing the code', e) 
