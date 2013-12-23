
IN_LONG_VERSION_PY = True
# This file helps to compute a version number in source trees obtained from
# git-archive tarball (such as those provided by githubs download-from-tag
# feature). Distribution tarballs (build by setup.py sdist) and build
# directories (produced by setup.py build) will contain a much shorter file
# that just contains the computed version number.

# This file is released into the public domain. Generated by
# versioneer-0.7+ (https://github.com/warner/python-versioneer)

# these strings will be replaced by git during git-archive
git_refnames = "$Format:%d$"
git_full = "$Format:%H$"


import subprocess
import sys


def run_command(args, cwd=None, verbose=False):
    try:
        # remember shell=False, so use git.cmd on windows, not just git
        p = subprocess.Popen(args, stdout=subprocess.PIPE, cwd=cwd)
    except EnvironmentError:
        e = sys.exc_info()[1]
        if verbose:
            print("unable to run %s" % args[0])
            print(e)
        return None
    stdout = p.communicate()[0].strip()
    if sys.version >= '3':
        stdout = stdout.decode()
    if p.returncode != 0:
        if verbose:
            print("unable to run %s (error)" % args[0])
        return None
    return stdout

import re
import os.path


def get_expanded_variables(versionfile_source):
    # the code embedded in _version.py can just fetch the value of these
    # variables. When used from setup.py, we don't want to import
    # _version.py, so we do it with a regexp instead. This function is not
    # used from _version.py.
    variables = {}
    try:
        f = open(versionfile_source, "r")
        for line in f.readlines():
            if line.strip().startswith("git_refnames ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["refnames"] = mo.group(1)
            if line.strip().startswith("git_full ="):
                mo = re.search(r'=\s*"(.*)"', line)
                if mo:
                    variables["full"] = mo.group(1)
        f.close()
    except EnvironmentError:
        pass
    return variables


def versions_from_expanded_variables(variables, tag_prefix, verbose=False):
    refnames = variables["refnames"].strip()
    if refnames.startswith("$Format"):
        if verbose:
            print("variables are unexpanded, not using")
        return {}  # unexpanded, so not in an unpacked git-archive tarball
    refs = set([r.strip() for r in refnames.strip("()").split(",")])
    # starting in git-1.8.3, tags are listed as "tag: foo-1.0" instead of
    # just "foo-1.0". If we see a "tag: " prefix, prefer those.
    TAG = "tag: "
    tags = set([r[len(TAG):] for r in refs if r.startswith(TAG)])
    if not tags:
        # Either we're using git < 1.8.3, or there really are no tags. We use
        # a heuristic: assume all version tags have a digit. The old git %d
        # expansion behaves like git log --decorate=short and strips out the
        # refs/heads/ and refs/tags/ prefixes that would let us distinguish
        # between branches and tags. By ignoring refnames without digits, we
        # filter out many common branch names like "release" and
        # "stabilization", as well as "HEAD" and "master".
        tags = set([r for r in refs if re.search(r'\d', r)])
        if verbose:
            print("discarding '%s', no digits" % ",".join(refs-tags))
    if verbose:
        print("likely tags: %s" % ",".join(sorted(tags)))
    for ref in sorted(tags):
        # sorting will prefer e.g. "2.0" over "2.0rc1"
        if ref.startswith(tag_prefix):
            r = ref[len(tag_prefix):]
            if verbose:
                print("picking %s" % r)
            return {"version": r,
                    "full": variables["full"].strip()}
    # no suitable tags, so we use the full revision id
    if verbose:
        print("no suitable tags, using full revision id")
    return {"version": variables["full"].strip(),
            "full": variables["full"].strip()}


def versions_from_vcs(tag_prefix, versionfile_source, verbose=False):
    # this runs 'git' from the root of the source tree. That either means
    # someone ran a setup.py command (and this code is in versioneer.py, so
    # IN_LONG_VERSION_PY=False, thus the containing directory is the root of
    # the source tree), or someone ran a project-specific entry point (and
    # this code is in _version.py, so IN_LONG_VERSION_PY=True, thus the
    # containing directory is somewhere deeper in the source tree). This only
    # gets called if the git-archive 'subst' variables were *not* expanded,
    # and _version.py hasn't already been rewritten with a short version
    # string, meaning we're inside a checked out source tree.

    try:
        here = os.path.abspath(__file__)
    except NameError:
        # some py2exe/bbfreeze/non-CPython implementations don't do __file__
        return {}  # not always correct

    # versionfile_source is the relative path from the top of the source tree
    # (where the .git directory might live) to this file. Invert this to find
    # the root from __file__.
    root = here
    if IN_LONG_VERSION_PY:
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        root = os.path.dirname(
            os.path.join('..', here))

    ######################################################
    # XXX patch for our specific configuration with
    # the three projects leap.soledad.{common, client, server}
    # inside the same repo.
    ######################################################
    root = os.path.dirname(os.path.join('..', root))

    if not os.path.exists(os.path.join(root, ".git")):
        if verbose:
            print("no .git in %s" % root)
        return {}

    GIT = "git"
    if sys.platform == "win32":
        GIT = "git.cmd"
    stdout = run_command([GIT, "describe", "--tags", "--dirty", "--always"],
                         cwd=root)
    if stdout is None:
        return {}
    if not stdout.startswith(tag_prefix):
        if verbose:
            print("tag '%s' doesn't start with prefix '%s'" %
                  (stdout, tag_prefix))
        return {}
    tag = stdout[len(tag_prefix):]
    stdout = run_command([GIT, "rev-parse", "HEAD"], cwd=root)
    if stdout is None:
        return {}
    full = stdout.strip()
    if tag.endswith("-dirty"):
        full += "-dirty"
    return {"version": tag, "full": full}


def versions_from_parentdir(parentdir_prefix, versionfile_source,
                            verbose=False):
    if IN_LONG_VERSION_PY:
        # We're running from _version.py. If it's from a source tree
        # (execute-in-place), we can work upwards to find the root of the
        # tree, and then check the parent directory for a version string. If
        # it's in an installed application, there's no hope.
        try:
            here = os.path.abspath(__file__)
        except NameError:
            # py2exe/bbfreeze/non-CPython don't have __file__
            return {}  # without __file__, we have no hope
        # versionfile_source is the relative path from the top of the source
        # tree to _version.py. Invert this to find the root from __file__.
        root = here
        for i in range(len(versionfile_source.split("/"))):
            root = os.path.dirname(root)
    else:
        # we're running from versioneer.py, which means we're running from
        # the setup.py in a source tree. sys.argv[0] is setup.py in the root.
        here = os.path.abspath(sys.argv[0])
        root = os.path.dirname(here)

    # Source tarballs conventionally unpack into a directory that includes
    # both the project name and a version string.
    dirname = os.path.basename(root)
    if not dirname.startswith(parentdir_prefix):
        if verbose:
            print("guessing rootdir is '%s', but '%s' doesn't start "
                  "with prefix '%s'" %
                  (root, dirname, parentdir_prefix))
        return None
    return {"version": dirname[len(parentdir_prefix):], "full": ""}

tag_prefix = ""
parentdir_prefix = "leap.soledad.server-"
versionfile_source = "src/leap/soledad/server/_version.py"


def get_versions(default={"version": "unknown", "full": ""}, verbose=False):
    variables = {"refnames": git_refnames, "full": git_full}
    ver = versions_from_expanded_variables(variables, tag_prefix, verbose)
    if not ver:
        ver = versions_from_vcs(tag_prefix, versionfile_source, verbose)
    if not ver:
        ver = versions_from_parentdir(parentdir_prefix, versionfile_source,
                                      verbose)
    if not ver:
        ver = default
    return ver
