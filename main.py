"""
Main file for building the modpack + uploading
"""
import json
import re
import sh
import shutil
import sys
from cmd import cd, bake_nice_tty
from gradle import Gradle
from log import log
from pathlib import Path

git = bake_nice_tty(sh.git)
git_last_commit_message = git.log.bake('-1', '--pretty=%B')
git_last_commit_sha = git.log.bake('-1', '--pretty=%H')
java_jar = bake_nice_tty(sh.java.bake('-jar'))
lv_regex = re.compile(r'version = ["\'](\d+\.\d+\.\d+(?:-SNAPSHOT)?)["\']')


def fail(msg):
    exec = sys.exc_info()
    if exec[0]:
        if isinstance(exec[0], sh.ErrorReturnCode):
            print('Error code', exec[0].exit_code, file=sys.stderr)
        else:
            import traceback
            traceback.print_exc()
    print(msg, file=sys.stderr)
    sys.exit(1)


def require_folder_git(src, target, branch=None):
    if not target.exists():
        print('Cloning', src, target)
        clone = git.clone.bake(src, target)
        if branch:
            clone = clone.bake('--branch', branch, '--single-branch')
        if clone().exit_code:
            fail("Couldn't clone")
    else:
        try:
            with cd(target):
                git.pull()
                git.reset('--hard', 'HEAD')
        except sh.ErrorReturnCode:
            import traceback
            traceback.print_exc()
            shutil.rmtree(str(target))
            return require_folder_git(src, target, branch=branch)
    return target


@log
def clone_downloads():
    src = 'git@github.com:kenzierocks/Launcher.git'
    target = Path('downloads').absolute()
    return require_folder_git(src, target, branch='gh-pages')


@log
def dl_launcher():
    src = 'https://github.com/SKCraft/Launcher.git'
    target = Path('launcher').absolute()
    return require_folder_git(src, target, branch='master')


@log
def discover_patch_version():
    patches = Path('patches').absolute()
    with (patches / 'version.txt').open() as f:
        return f.read().strip()


@log
def apply_launcher_patches(launcher):
    patches = Path('patches').absolute()
    if not patches.exists():
        fail('No patches')
    apply = git.apply
    with cd(launcher):
        for p in patches.iterdir():
            print('Patching', p.absolute())
            if not p.is_file():
                fail('Patch {} is not a file. Please remove it.'.format(p.absolute()))
            if 'version.txt' == str(p.name):
                continue
            apply(str(p.absolute()))


def _find_all_jar(d: Path):
    return list(filter(lambda x: 'all' in str(x), d.iterdir()))[0]


@log
def build_launcher(launcher: Gradle):
    launcher.build()
    return (_find_all_jar(launcher.dir / 'launcher-bootstrap' / 'build' / 'libs'),
            _find_all_jar(launcher.dir / 'launcher-fancy' / 'build' / 'libs'),
            _find_all_jar(launcher.dir / 'launcher-builder' / 'build' / 'libs'))


@log
def build_modpack(cmd, package_version, file_src):
    inp = str(file_src.absolute())
    out_path = Path.cwd() / 'output-client'
    out = str(out_path.absolute())
    manifest_destiny = str((out_path / 'modpack.json').absolute())
    cmd('--version', package_version, '--input', inp, '--output', out, '--manifest-dest', manifest_destiny)
    return out


@log
def build_server(cmd, file_src):
    server = Path.cwd() / 'output-server'
    cmd('com.skcraft.launcher.builder.ServerCopyExport', '--source', file_src.absolute(),
        '--dest', server)
    return server


@log
def clear_and_copy(package_name, client, downloads):
    c_path = Path(client)
    d_path = Path(downloads)
    dl_client = d_path / 'data' / 'dist' / package_name
    if dl_client.exists():
        shutil.rmtree(str(dl_client))
    else:
        Path(dl_client.parent).mkdir(parents=True)
    c_path.rename(dl_client)


@log
def pack_real_launcher(downloads, version_full, launcher_jar):
    target = Path(downloads) / 'data' / 'launcher-{}.jar.pack'.format(version_full)
    if target.exists():
        target.unlink()
    bake_nice_tty(sh.pack200)('--no-gzip', str(target.absolute()), launcher_jar)


@log
def write_jsons(downloads, package_name, package_title, package_version, launcher_version_full):
    from collections import OrderedDict
    latest = OrderedDict()
    latest["version"] = launcher_version_full
    latest["url"] = \
        "http://kenzierocks.github.io/Launcher/data/launcher-{}.jar.pack".format(launcher_version_full)
    packages = OrderedDict()
    packages["minimumVersion"] = 1
    pkg = OrderedDict()
    pkg["name"] = package_name
    pkg["title"] = package_title
    pkg["version"] = package_version
    pkg["location"] = "../dist/" + package_name + "/modpack.json"
    packages["packages"] = [pkg]
    jsons = (Path(downloads) / 'data' / 'jsons').absolute()
    with (jsons / 'latest.json').open('w+') as f:
        json.dump(latest, f)
    with (jsons / 'packages.json').open('w+') as f:
        json.dump(packages, f)


@log
def upload_downloads(d, version, launcher_version):
    with cd(d):
        git.add('.')
        git.commit('-m', make_commit_message(launcher_version, version))
        git.push()


def make_commit_message(launcher_version, version):
    return 'Version {} (launcher: {}), autogenerated.'.format(version, launcher_version)


def input_path():
    path = input("Directory with files: ")
    if not path:
        sys.exit(1)
    return path


def discover_data(files):
    with (Path(files) / 'modpack.json').open() as f:
        data = json.load(f)
    data = dict(data)
    with (Path(files) / 'version.txt').open() as f:
        data['version'] = f.read().strip()
    return data


def discover_launcher_version(launcher):
    with cd(launcher):
        return git_last_commit_sha(_out=None).stdout.decode().strip()


@log
def fail_if_no_changes(downloads, version, launcher_version):
    msg = make_commit_message(launcher_version, version)
    with cd(downloads):
        last_msg = git_last_commit_message(_out=None).stdout.decode().strip()
    if msg == last_msg:
        fail("No changes, '{}' == '{}'".format(msg, last_msg))


def main(path=None):
    try:
        launcher = dl_launcher()
        ghpages = clone_downloads()
        path = path or input_path()
        file_dir = Path(path).absolute().resolve()
        if not file_dir.exists():
            fail("{} doesn't exist".format(file_dir))
        print('Loading from {}'.format(file_dir))
        package_data = discover_data(file_dir)
        patch_version = discover_patch_version()
        launcher_version = discover_launcher_version(launcher) + '-' + patch_version
        fail_if_no_changes(ghpages, package_data['version'], launcher_version)
        apply_launcher_patches(launcher)
        (launcher_bootstrap,
         launcher_fancy,
         launcher_builder) = build_launcher(Gradle(directory=launcher, wrapper=True))
        print('Found LBO ' + str(launcher_bootstrap))
        print('Found LFA ' + str(launcher_fancy))
        print('Found LBL ' + str(launcher_builder))
        print('Launcher version ' + launcher_version)
        client_dir = build_modpack(java_jar.bake(launcher_builder),
                                   package_data['version'], file_dir)
        server_dir = build_server(bake_nice_tty(sh.java.bake('-cp', launcher_builder)),
                                  file_dir / 'src')
        clear_and_copy(package_data['name'], client_dir, ghpages)
        pack_real_launcher(ghpages, launcher_version, launcher_fancy)
        write_jsons(ghpages, package_data['name'], package_data['title'],
                    package_data['version'], launcher_version)
        upload_downloads(ghpages, package_data['version'], launcher_version)
    except Exception as e:
        l = len(e.args)
        if l == 0:
            fail(str(type(e)))
        elif l == 1:
            fail(str(e.args[0]))
        else:
            fail(str(e.args))


if __name__ == "__main__":
    main()
