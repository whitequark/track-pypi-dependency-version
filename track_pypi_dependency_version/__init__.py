import sys
import urllib.request
import json
import argparse
from packaging.version import Version
from packaging.specifiers import Specifier, SpecifierSet
from packaging.requirements import Requirement


def main():
    parser = argparse.ArgumentParser(sys.argv[0], description="""
    Check the version of newest PyPI release and update requirements file.

    If STATUS-FILE is specified, then a line of the form `status=X` is appended
    to it, where X is one of `stale` (if the release of a new version caused
    DEPS-FILE to be updated), `up-to-date` (if nothing was done), or `failure`
    (if an error was encountered). If DEPS-FILE was updated, then `old-requirement=Y`
    and `new-requirement=Z` are also appended, where Y is the existing upper bound
    and Z is the updated upper bound.
    """)
    parser.add_argument("target", metavar="PACKAGE",
        help="package whose version needs to be updated")
    parser.add_argument("--requirements", "-r", metavar="DEPS-FILE", type=argparse.FileType("r+"),
        help="requirements.txt style file to update")
    parser.add_argument("--status", metavar="STATUS-FILE", type=argparse.FileType("a"),
        help="GitHub Actions style status file to update")
    args = parser.parse_args()


    print(f"Updating requirement for {args.target}...")

    with urllib.request.urlopen(f"https://pypi.org/pypi/{args.target}/json") as req:
        target_pypi_metadata = json.load(req)

    target_latest_ver = max(map(Version, target_pypi_metadata['releases']))
    print(f"  Latest PyPI version is {target_latest_ver}")

    package_reqs = [Requirement(req) for req in args.requirements.readlines() if req]

    target_req = None
    other_reqs = []
    for package_req in package_reqs:
        if package_req.name == args.target:
            target_req = package_req
        else:
            other_reqs.append(package_req)
    if target_req is None:
        print(f"Could not find requirement for {args.target}",
              file=sys.stderr)
        if args.status:
            args.status.write(f"status=failure\n")
        sys.exit(1)
    print(f"  Requirement is {target_req}")

    target_req_spec = None
    other_req_specs = []
    for req_spec in target_req.specifier:
        if req_spec.operator in ("<", "<="):
            target_req_spec = req_spec
        else:
            other_req_specs.append(req_spec)
    if target_req_spec is None:
        print(f"Could not find upper version bound for {args.target} in requirement",
              file=sys.stderr)
        if args.status:
            args.status.write(f"status=failure\n")
        sys.exit(1)
    print(f"  Upper version bound is {target_req_spec}")

    if target_req_spec.contains(target_latest_ver):
        print(f"Latest PyPI version is within upper bound, nothing to do")
        if args.status:
            args.status.write(f"status=up-to-date\n")
        sys.exit(0)

    new_target_req_spec = f"<{target_latest_ver.major + 1}"
    new_target_req_specs = ",".join([str(spec) for spec in other_req_specs] +
                                    [new_target_req_spec])

    if not SpecifierSet(new_target_req_spec).contains(target_latest_ver):
        print(f"New specifier set {new_target_req_specs} does not contain {target_latest_ver}!")
        if args.status:
            args.status.write(f"status=failure\n")
        sys.exit(1)

    new_target_req = Requirement("".join([package_req.name, new_target_req_specs]))
    print(f"  New requirement for {args.target} is {new_target_req}")

    args.requirements.seek(0)
    args.requirements.truncate(0)
    for new_package_req in other_reqs + [new_target_req]:
        args.requirements.write(f"{new_package_req}\n")
    args.requirements.close()
    print(f"Updated requirement to include latest PyPI version")
    if args.status:
        args.status.write(f"status=stale\n")
        args.status.write(f"old-requirement={target_req_spec}\n")
        args.status.write(f"new-requirement={new_target_req_spec}\n")
    sys.exit(0)
