import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, ROOT)

DEPS_DIR = os.path.join(ROOT, "tls_client", "dependencies")
MIN_BINARY_SIZE = 1_000_000  # 1 MB

EXPECTED_BINARIES = [
    "tls-client-32.dll",
    "tls-client-64.dll",
    "tls-client-arm64.dylib",
    "tls-client-x86.dylib",
    "tls-client-amd64.so",
    "tls-client-x86.so",
    "tls-client-arm64.so",
]

FINGERPRINT_URL = "https://tls.peet.ws/api/all"


def check_binaries():
    print("=== Binary sizes ===")
    failed = []
    for name in EXPECTED_BINARIES:
        path = os.path.join(DEPS_DIR, name)
        size = os.path.getsize(path) if os.path.exists(path) else 0
        status = "OK" if size >= MIN_BINARY_SIZE else "FAIL"
        print(f"  [{status}] {name}: {size:,} bytes")
        if status == "FAIL":
            failed.append(name)
    return failed


def check_identifiers():
    print("\n=== ClientIdentifiers ===")
    from tls_client.settings import ClientIdentifiers
    args = ClientIdentifiers.__args__
    required = ["chrome_144", "chrome_146", "chrome_146_PSK", "brave_146", "firefox_147", "safari_ios_26_0"]
    failed = []
    for ident in required:
        status = "OK" if ident in args else "MISS"
        print(f"  [{status}] {ident}")
        if status == "MISS":
            failed.append(ident)
    print(f"  Total identifiers: {len(args)}")
    return failed


def check_request(client_identifier="chrome_146"):
    print(f"\n=== Live request ({client_identifier}) ===")
    import tls_client
    session = tls_client.Session(client_identifier=client_identifier)
    try:
        r = session.get(FINGERPRINT_URL, timeout=15)
        data = r.json()
        tls_data = data.get("tls", {})
        ja3 = tls_data.get("ja3", "N/A")
        ja3_hash = tls_data.get("ja3_hash", "N/A")
        http2 = data.get("http2", {}).get("akamai_fingerprint_hash", "N/A")
        print(f"  JA3:        {ja3_hash}")
        print(f"  JA3 string: {ja3[:80]}...")
        print(f"  H2 akamai:  {http2}")
        print(f"  Status:     {r.status_code}")
        return []
    except Exception as e:
        print(f"  [FAIL] {e}")
        return [str(e)]


def main():
    failures = []
    failures += check_binaries()
    failures += check_identifiers()
    failures += check_request()

    print("\n" + ("=" * 40))
    if failures:
        print(f"FAILED: {len(failures)} issue(s)")
        for f in failures:
            print(f"  - {f}")
        sys.exit(1)
    else:
        print("ALL CHECKS PASSED")


if __name__ == "__main__":
    main()
