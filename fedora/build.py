import os
import sys
import shutil
import subprocess
import tarfile


def read_version_from_pubspec(pubspec_path: str) -> str:
    with open(pubspec_path, 'r', encoding='utf-8') as f:
        content = f.read()
    # Extract version before '+' if build metadata exists
    version_line = content.split('version: ')[1]
    version = version_line.split('\n')[0].strip()
    version = version.split('+')[0]
    return version


def rpm_arch_from_input(arch: str) -> str:
    if arch == 'x64':
        return 'x86_64'
    if arch == 'arm64':
        return 'aarch64'
    return arch


def bundle_arch_from_input(arch: str) -> str:
    if arch == 'x64':
        return 'x64'
    if arch == 'arm64':
        return 'arm64'
    return arch


def ensure_dirs(path: str):
    os.makedirs(path, exist_ok=True)


def main():
    if len(sys.argv) < 2:
        print('Usage: python3 fedora/build.py <arch>\n  arch: x64 | arm64')
        sys.exit(1)

    arch_in = sys.argv[1]
    rpm_arch = rpm_arch_from_input(arch_in)
    bundle_arch = bundle_arch_from_input(arch_in)

    root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    pubspec = os.path.join(root, 'pubspec.yaml')
    version = read_version_from_pubspec(pubspec)

    # Build Flutter linux bundle
    subprocess.check_call(["flutter", "pub", "get"], cwd=root)
    subprocess.check_call(["flutter", "build", "linux"], cwd=root)

    bundle_dir = os.path.join(root, 'build', 'linux', bundle_arch, 'release', 'bundle')
    if not os.path.isdir(bundle_dir):
        print(f'Bundle not found: {bundle_dir}')
        sys.exit(2)

    # Prepare staging directory for source tarball
    stage_dir = os.path.join(root, 'fedora', 'stage')
    if os.path.isdir(stage_dir):
        shutil.rmtree(stage_dir)
    ensure_dirs(stage_dir)

    # Copy bundle
    shutil.copytree(bundle_dir, os.path.join(stage_dir, 'bundle'))

    # Copy desktop file and icon
    shutil.copy(os.path.join(root, 'fedora', 'gui', 'venera.desktop'), os.path.join(stage_dir, 'venera.desktop'))
    shutil.copy(os.path.join(root, 'assets', 'app_icon.png'), os.path.join(stage_dir, 'venera.png'))

    # Copy wrapper
    shutil.copy(os.path.join(root, 'fedora', 'wrapper.sh'), os.path.join(stage_dir, 'venera.sh'))

    # Create SOURCES tarball
    rpmbuild_topdir = os.path.join(root, 'fedora', 'rpmbuild')
    sources_dir = os.path.join(rpmbuild_topdir, 'SOURCES')
    specs_dir = os.path.join(rpmbuild_topdir, 'SPECS')
    ensure_dirs(sources_dir)
    ensure_dirs(specs_dir)

    tarball_name = f'venera-{version}.tar.gz'
    tarball_path = os.path.join(sources_dir, tarball_name)
    with tarfile.open(tarball_path, 'w:gz') as tar:
        tar.add(stage_dir, arcname=f'venera-{version}')

    # Render spec from template
    with open(os.path.join(root, 'fedora', 'venera.spec.in'), 'r', encoding='utf-8') as f:
        spec_tpl = f.read()
    spec_content = spec_tpl.replace('{{Version}}', version).replace('{{RpmArch}}', rpm_arch)
    spec_path = os.path.join(specs_dir, 'venera.spec')
    with open(spec_path, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    # Build RPM
    cmd = [
        'rpmbuild', '-bb', spec_path,
        '--define', f'_topdir {rpmbuild_topdir}'
    ]
    subprocess.check_call(cmd, cwd=root)

    # Copy resulting RPM to artifact dir
    rpm_out_dir = os.path.join(root, 'build', 'linux', bundle_arch, 'release', 'rpm')
    ensure_dirs(rpm_out_dir)
    rpms_arch_dir = os.path.join(rpmbuild_topdir, 'RPMS', rpm_arch)
    for fname in os.listdir(rpms_arch_dir):
        if fname.endswith('.rpm'):
            shutil.copy(os.path.join(rpms_arch_dir, fname), os.path.join(rpm_out_dir, fname))
            print('RPM generated:', os.path.join(rpm_out_dir, fname))


if __name__ == '__main__':
    main()