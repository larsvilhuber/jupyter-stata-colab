#!/usr/bin/env python3
"""Install Stata on Google Colab (or any Linux machine) and configure PyStata.

Stata is copied out of one of the AEA Data Editor Docker images
(https://hub.docker.com/u/dataeditors) using only the Python standard
library, so neither Docker nor root-level tooling beyond write access to the
target directory is needed. The images do NOT contain a license: you must
supply your own ``stata.lic``, as a base64-encoded string.

Typical use from a notebook::

    import setup_stata
    setup_stata.install_stata()
    setup_stata.write_license(getpass("Base64-encoded stata.lic: "))
    setup_stata.configure_pystata()

Or from the command line::

    python setup_stata.py              # install, then prompt for the license
"""

import argparse
import base64
import binascii
import getpass
import json
import os
import posixpath
import shutil
import subprocess
import sys
import tarfile
import urllib.request

DEFAULT_IMAGE = "dataeditors/stata19_5-se:2026-08-12"
DEFAULT_STATA_DIR = "/usr/local/stata"
DEFAULT_EDITION = "se"

REGISTRY = "https://registry-1.docker.io"
AUTH_URL = "https://auth.docker.io/token?service=registry.docker.io&scope=repository:{repo}:pull"
MANIFEST_TYPES = ", ".join(
    [
        "application/vnd.docker.distribution.manifest.v2+json",
        "application/vnd.docker.distribution.manifest.list.v2+json",
        "application/vnd.oci.image.manifest.v1+json",
        "application/vnd.oci.image.index.v1+json",
    ]
)
WHITEOUT_PREFIX = ".wh."
OPAQUE_WHITEOUT = ".wh..wh..opq"


def _parse_image(image):
    """Split ``repo[:tag]`` into (repo, tag), defaulting to Docker Hub's library namespace."""
    repo, _, tag = image.partition(":")
    if "/" not in repo:
        repo = "library/" + repo
    return repo, tag or "latest"


def _request(url, token, accept=None):
    req = urllib.request.Request(url)
    # Unredirected so the token is not forwarded to the blob storage CDN.
    req.add_unredirected_header("Authorization", "Bearer " + token)
    if accept:
        req.add_header("Accept", accept)
    return urllib.request.urlopen(req)


def _get_token(repo):
    with urllib.request.urlopen(AUTH_URL.format(repo=repo)) as resp:
        return json.load(resp)["token"]


def _get_layers(repo, tag, token):
    """Return the list of layer digests of the linux/amd64 image."""
    url = "{}/v2/{}/manifests/{}".format(REGISTRY, repo, tag)
    with _request(url, token, MANIFEST_TYPES) as resp:
        manifest = json.load(resp)
    if "manifests" in manifest:  # multi-platform index
        for entry in manifest["manifests"]:
            platform = entry.get("platform", {})
            if platform.get("os") == "linux" and platform.get("architecture") == "amd64":
                return _get_layers(repo, entry["digest"], token)
        raise RuntimeError("No linux/amd64 image found for {}:{}".format(repo, tag))
    return [layer["digest"] for layer in manifest["layers"]]


def _within(path, prefix):
    return path == prefix or path.startswith(prefix + "/")


def _remove(path):
    if os.path.isdir(path) and not os.path.islink(path):
        shutil.rmtree(path)
    elif os.path.lexists(path):
        os.remove(path)


def _extract_layer(fileobj, prefix, root):
    """Stream a gzipped layer tarball, extracting only entries below ``prefix``.

    OCI/Docker whiteout files are honoured so that files deleted in a later
    layer are also removed from the extracted tree.
    """
    extracted = set()
    with tarfile.open(fileobj=fileobj, mode="r|gz") as tar:
        for member in tar:
            name = posixpath.normpath(member.name.lstrip("/"))
            if name.startswith("./"):
                name = name[2:]
            if not _within(name, prefix):
                continue
            dirname, basename = posixpath.split(name)
            if basename == OPAQUE_WHITEOUT:
                target = os.path.join(root, dirname)
                if os.path.isdir(target):
                    for child in os.listdir(target):
                        if posixpath.join(dirname, child) not in extracted:
                            _remove(os.path.join(target, child))
                continue
            if basename.startswith(WHITEOUT_PREFIX):
                hidden = posixpath.join(dirname, basename[len(WHITEOUT_PREFIX):])
                _remove(os.path.join(root, hidden))
                continue
            member.name = name
            target = os.path.join(root, name)
            if not member.isdir() and os.path.lexists(target):
                _remove(target)
            tar.extract(member, path=root, filter="data")
            extracted.add(name)


def install_stata(image=DEFAULT_IMAGE, stata_dir=DEFAULT_STATA_DIR, root="/", force=False):
    """Copy the Stata installation found at ``stata_dir`` inside ``image`` to ``root``.

    Returns the path of the installed Stata directory.
    """
    prefix = stata_dir.strip("/")
    target = os.path.join(root, prefix)
    if os.path.isdir(target) and os.listdir(target) and not force:
        print("Stata already installed in {} (use force=True to reinstall).".format(target))
        return target

    repo, tag = _parse_image(image)
    print("Fetching Stata from docker.io/{}:{} ...".format(repo, tag))
    token = _get_token(repo)
    layers = _get_layers(repo, tag, token)
    for i, digest in enumerate(layers, 1):
        print("  layer {}/{} {}".format(i, len(layers), digest[:19]))
        url = "{}/v2/{}/blobs/{}".format(REGISTRY, repo, digest)
        with _request(url, token) as resp:
            _extract_layer(resp, prefix, root)

    if not os.path.isdir(target):
        raise RuntimeError("{} not found in image {}".format(stata_dir, image))
    print("Stata installed in {}".format(target))
    return target


def decode_license(license_b64):
    """Decode a base64-encoded ``stata.lic`` and do a basic sanity check."""
    cleaned = "".join(license_b64.split())
    if not cleaned:
        raise ValueError("Empty license string.")
    try:
        decoded = base64.b64decode(cleaned, validate=True)
    except (binascii.Error, ValueError) as err:
        raise ValueError("License is not valid base64: {}".format(err)) from None
    try:
        text = decoded.decode("ascii")
    except UnicodeDecodeError:
        raise ValueError("Decoded license is not a text file; did you encode stata.lic?") from None
    if "!" not in text:
        raise ValueError("Decoded license does not look like a stata.lic file.")
    return decoded


def write_license(license_b64, stata_dir=DEFAULT_STATA_DIR):
    """Write the base64-encoded license to ``stata_dir/stata.lic``."""
    content = decode_license(license_b64)
    path = os.path.join(stata_dir, "stata.lic")
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(content)
    os.chmod(path, 0o600)
    print("License written to {}".format(path))
    return path


def check_license(stata_dir=DEFAULT_STATA_DIR, edition=DEFAULT_EDITION):
    """Run Stata once in a subprocess to confirm that the license is accepted.

    PyStata terminates the whole Python process (crashing the notebook kernel)
    when the license is invalid, so this gives a readable error instead.
    """
    binary = os.path.join(stata_dir, "stata" if edition == "be" else "stata-" + edition)
    marker = "STATA_LICENSE_OK"
    result = subprocess.run(
        [binary, "-q"],
        input='display "{}"\nexit, clear\n'.format(marker),
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = (result.stdout + result.stderr).strip()
    if marker not in output:
        raise RuntimeError("Stata did not start with this license:\n" + output)
    print("Stata license OK.")


def configure_pystata(stata_dir=DEFAULT_STATA_DIR, edition=DEFAULT_EDITION):
    """Initialise PyStata, which also registers the ``%stata``/``%%stata`` magics."""
    check_license(stata_dir, edition)
    utilities = os.path.join(stata_dir, "utilities")
    if utilities not in sys.path:
        sys.path.append(utilities)
    from pystata import config  # noqa: E402 (only importable once Stata is installed)

    config.init(edition)
    return config


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--image", default=DEFAULT_IMAGE, help="Docker image to copy Stata from (default: %(default)s)")
    parser.add_argument("--stata-dir", default=DEFAULT_STATA_DIR, help="Stata directory (default: %(default)s)")
    parser.add_argument("--root", default="/", help="Filesystem root to install into (default: %(default)s)")
    parser.add_argument("--force", action="store_true", help="Reinstall even if Stata is already present")
    parser.add_argument("--edition", default=DEFAULT_EDITION, choices=["be", "se", "mp"], help="Stata edition (default: %(default)s)")
    parser.add_argument("--skip-license", action="store_true", help="Do not prompt for the license")
    args = parser.parse_args(argv)

    target = install_stata(args.image, args.stata_dir, args.root, args.force)
    if not args.skip_license:
        write_license(getpass.getpass("Paste your base64-encoded stata.lic (input hidden): "), target)
        check_license(target, args.edition)


if __name__ == "__main__":
    main()
