import json
import os
from zipfile import ZipFile
import subprocess

BRANCH = os.environ['GITHUB_REF'].split('refs/heads/')[-1]
DOWNLOAD_URL = 'https://github.com/ToxicMushroom/Athavar.FFXIV.DalaRepo/raw/{branch}/plugins/{plugin_name}/latest.zip'

DEFAULTS = {
    'IsHide': False,
    'IsTestingExclusive': False,
    'ApplicableVersion': 'any',
}

DUPLICATES = {
    'DownloadLinkInstall': ['DownloadLinkTesting', 'DownloadLinkUpdate'],
}

TRIMMED_KEYS = [
    'Author',
    'Name',
    'Punchline',
    'Description',
    'Changelog',
    'InternalName',
    'AssemblyVersion',
    'RepoUrl',
    'ApplicableVersion',
    'Tags',
    'DalamudApiLevel',
    'IconUrl',
    'ImageUrls',
    'IsThirdParty',
    'LoadSync',
    'AcceptsFeedback',
    'LoadPriority',
    'CanUnloadAsync',
    'DownloadLinkInstall',
]


def main():
    # extract the manifests from inside the zip files
    master = extract_manifests()

    # trim the manifests
    master = [trim_manifest(manifest) for manifest in master]

    # convert the list of manifests into a master list
    add_extra_fields(master)

    # write the master
    write_master(master)

    # update the LastUpdated field in master
    last_updated()


def extract_manifests():
    manifests = []

    for dirpath, dirnames, filenames in os.walk('./plugins'):
        if len(filenames) == 0:
            continue

        plugin_name = dirpath.split('/')[-1]
        if plugin_name + '.json' in filenames:
            latest_manifest = f'{dirpath}/{plugin_name}.json'
            with open(latest_manifest) as f:
                manifest = json.loads(f.read())
                print(manifest)
                manifests.append(manifest)
            continue

        if 'latest.zip' in filenames:
            latest_zip = f'{dirpath}/latest.zip'
            with ZipFile(latest_zip) as z:
                manifest = json.loads(z.read(f'{plugin_name}.json').decode('utf-8'))
                manifests.append(manifest)
            continue

    return manifests


def add_extra_fields(manifests):
    for manifest in manifests:
        # generate the download link from the internal assembly name

        if not manifest.get('DownloadLinkInstall'):
            manifest['DownloadLinkInstall'] = DOWNLOAD_URL.format(branch=BRANCH, plugin_name=manifest["InternalName"])

        # add default values if missing
        for k, v in DEFAULTS.items():
            if k not in manifest:
                manifest[k] = v
        # duplicate keys as specified in DUPLICATES
        for source, keys in DUPLICATES.items():
            for k in keys:
                if k not in manifest:
                    manifest[k] = manifest[source]
        manifest['DownloadCount'] = 0


def write_master(master):
    # write as pretty json
    with open('pluginmaster.json', 'w') as f:
        json.dump(master, f, indent=4)


def trim_manifest(plugin):
    return {k: plugin[k] for k in TRIMMED_KEYS if k in plugin}


def git(*args):
    return subprocess.check_output(['git'] + list(args), universal_newlines=True)


def last_updated():
    with open('pluginmaster.json') as f:
        master = json.load(f)

    for plugin in master:
        latest_zip = f'plugins/{plugin["InternalName"]}/latest.zip'
        modified_zip = int(git('log', '-1', '--format=%at', latest_zip).strip('\n')) if os.path.exists(latest_zip) else 0
        latest_manifest = f'plugins/{plugin["InternalName"]}/{plugin["InternalName"]}.json'
        modified_manifest = int(git('log', '-1', '--format=%at', latest_manifest).strip('\n')) if os.path.exists(latest_manifest) else 0
        modified = modified_manifest if modified_manifest > modified_zip else modified_zip
 
        if 'LastUpdated' not in plugin or modified != int(plugin['LastUpdated']):
            plugin['LastUpdated'] = str(modified)

    with open('pluginmaster.json', 'w') as f:
        json.dump(master, f, indent=4)


if __name__ == '__main__':
    main()