"""Download the tls-client shared libraries for a release into tls_client/dependencies.

    python scripts/update_shared_libraries.py 1.16.0

Asset names are resolved from the GitHub release rather than built from a
template. They have changed shape before -- 1.15.1 published
`tls-client-linux-amd64-1.15.1.so`, 1.16.0 publishes
`tls-client-xgo-1.16.0-linux-amd64.so` -- and the previous version of this
script built the old shape and wrote whatever came back, so a rename turned
every binary into a 404 page with nothing said. Each download is checked for
status and size here, and one failure stops the run.

1.16.0 also dropped the separate alpine and ubuntu linux builds for a single
linux-amd64. Both glibc and musl slots are filled from it; if that binary turns
out not to run under musl, alpine deployments need a build from source.
"""
import json
import os
import sys
import urllib.request

RELEASES = "https://api.github.com/repos/bogdanfinn/tls-client/releases/tags/v%s"
DEPS = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "tls_client", "dependencies")
MIN_SIZE = 1_000_000

# Local file name -> the (os, arch) the release publishes it for. The local names
# are what tls_client/cffi.py picks between at import, so they are fixed; only the
# right-hand side follows upstream. Note cffi.py loads "-x86.so" on x86_64, since
# it tests `"x86" in machine()`, so that slot is the ordinary 64-bit linux build.
WANTED = {
    "tls-client-32.dll":     ("windows", "386"),
    "tls-client-64.dll":     ("windows", "amd64"),
    "tls-client-arm64.dylib": ("darwin", "arm64"),
    "tls-client-x86.dylib":  ("darwin", "amd64"),
    "tls-client-amd64.so":   ("linux", "amd64"),
    "tls-client-x86.so":     ("linux", "amd64"),
    "tls-client-arm64.so":   ("linux", "arm64"),
}


def release_assets(version):
    req = urllib.request.Request(RELEASES % version, headers={"User-Agent": "update-shared-libraries"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = json.load(r)
    if "assets" not in data:
        raise SystemExit("no release v%s: %s" % (version, data.get("message", "?")))
    return {a["name"]: a for a in data["assets"]}


def pick(assets, version, os_name, arch, ext):
    """Find the asset for one platform, accepting either naming scheme."""
    candidates = [n for n in assets
                  if n.endswith(ext) and os_name in n and ("-%s-" % arch in n or n.endswith("-%s%s" % (arch, ext)))]
    # An arch substring can match a longer one ("arm" in "arm64"), so require the
    # segment to stand alone between separators.
    exact = [n for n in candidates if ("-%s." % arch) in n or ("-%s-" % arch) in n]
    if len(exact) > 1:
        # Releases before 1.16.0 published the xgo build alongside the older
        # per-distro ones, so linux/amd64 matches three names there. The xgo build
        # is the one that survived, so prefer it and stay usable on old tags.
        exact = [n for n in exact if "-xgo-" in n] or exact
    if len(exact) == 1:
        return exact[0]
    raise SystemExit("cannot identify the %s/%s asset for v%s among: %s"
                     % (os_name, arch, version, ", ".join(sorted(candidates)) or "nothing"))


def main():
    if len(sys.argv) != 2:
        raise SystemExit(__doc__)
    version = sys.argv[1]
    assets = release_assets(version)
    print("v%s: %d assets" % (version, len(assets)))

    plan = []
    for local, (os_name, arch) in sorted(WANTED.items()):
        name = pick(assets, version, os_name, arch, os.path.splitext(local)[1])
        plan.append((local, assets[name]))
        print("  %-22s <- %s" % (local, name))

    for local, asset in plan:
        dest = os.path.join(DEPS, local)
        req = urllib.request.Request(asset["browser_download_url"],
                                     headers={"User-Agent": "update-shared-libraries"})
        with urllib.request.urlopen(req, timeout=600) as r:
            if r.status != 200:
                raise SystemExit("%s: HTTP %s" % (asset["name"], r.status))
            body = r.read()
        if len(body) < MIN_SIZE or len(body) != asset["size"]:
            raise SystemExit("%s: got %d bytes, release says %d" % (asset["name"], len(body), asset["size"]))
        with open(dest, "wb") as f:
            f.write(body)
        print("  wrote %-22s %10.1f MB" % (local, len(body) / 1048576.0))

    print("done")


if __name__ == "__main__":
    main()
