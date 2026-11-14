#!/usr/bin/env python3
"""
Extract Netflix domains from APK files using apktool or jadx.

Usage:
    python3 scripts/extract_domains.py <apk_file> [apk_file2 ...]

Output:
    domains/netflix_extracted.txt
"""

import subprocess
import re
import sys
import os

def check_tool_available(tool):
    """Check if apktool JAR or jadx is available."""
    # Check for apktool JAR first
    if os.path.exists("scripts/apktool_3.0.2.jar"):
        return True
    # Fall back to command-line tool check
    result = subprocess.run(
        ["which", tool],
        capture_output=True,
        text=True
    )
    return result.returncode == 0

def extract_with_apktool(apk_path, temp_dir):
    """Extract APK using apktool JAR or command."""
    print(f"[*] Extracting {apk_path} with apktool...")
    try:
        # Try JAR file first
        if os.path.exists("scripts/apktool_3.0.2.jar"):
            subprocess.run(
                ["java", "-jar", "scripts/apktool_3.0.2.jar", "d", "-f", "-o", temp_dir, apk_path],
                check=True,
                capture_output=True,
                timeout=60
            )
        else:
            # Fall back to command-line tool
            subprocess.run(
                ["apktool", "d", "-f", "-o", temp_dir, apk_path],
                check=True,
                capture_output=True,
                timeout=60
            )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[-] apktool failed: {e}")
        return False

def extract_with_jadx(apk_path, temp_dir):
    """Extract APK using jadx."""
    print(f"[*] Extracting {apk_path} with jadx...")
    try:
        subprocess.run(
            ["jadx", "-d", temp_dir, apk_path],
            check=True,
            capture_output=True,
            timeout=120
        )
        return True
    except (subprocess.CalledProcessError, FileNotFoundError, subprocess.TimeoutExpired) as e:
        print(f"[-] jadx failed: {e}")
        return False

def extract_domains_from_files(directory):
    """Recursively search directory for domain patterns."""
    domains = set()

    # Domain patterns to search for
    patterns = [
        r'([\w-]+\.netflix\.com)',
        r'([\w-]+\.nflx\.co)',
        r'(api[0-9]*\.netflix\.com)',
        r'(graphql\.netflix\.com)',
        r'(msl\.netflix\.com)',
        r'(netflix\.com)',
        r'(nflx\.co)',
    ]

    for root, dirs, files in os.walk(directory):
        for file in files:
            filepath = os.path.join(root, file)
            try:
                # Try to read as text
                with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read(100000)  # Read first 100KB only

                    for pattern in patterns:
                        matches = re.findall(pattern, content)
                        domains.update(matches)
            except (IOError, OSError):
                pass

    return domains

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 scripts/extract_domains.py <apk_file> [apk_file2 ...]")
        sys.exit(1)

    apk_files = sys.argv[1:]
    all_domains = set()

    # Check which tool is available
    tool = None
    if check_tool_available("apktool"):
        tool = "apktool"
    elif check_tool_available("jadx"):
        tool = "jadx"
    else:
        print("[-] Neither apktool nor jadx found. Install one of them:")
        print("    apt-get install apktool")
        print("    apt-get install jadx")
        sys.exit(1)

    print(f"[+] Using {tool} for extraction")

    # Extract each APK
    for apk_file in apk_files:
        if not os.path.exists(apk_file):
            print(f"[-] File not found: {apk_file}")
            continue

        temp_dir = f"/tmp/netflix_apk_extract_{os.getpid()}"
        os.makedirs(temp_dir, exist_ok=True)

        try:
            # Extract APK
            if tool == "apktool":
                success = extract_with_apktool(apk_file, temp_dir)
            else:
                success = extract_with_jadx(apk_file, temp_dir)

            if success:
                print(f"[+] Extraction successful for {apk_file}")
                domains = extract_domains_from_files(temp_dir)
                all_domains.update(domains)
                print(f"[+] Found {len(domains)} domains in {apk_file}")
            else:
                print(f"[!] Extraction failed for {apk_file}, continuing...")

        finally:
            # Cleanup temp directory
            subprocess.run(["rm", "-rf", temp_dir], capture_output=True)

    if not all_domains:
        print("[-] No domains extracted from any APK files")
        sys.exit(1)

    # Sort and write to file
    sorted_domains = sorted(all_domains)
    output_file = "domains/netflix_extracted.txt"
    os.makedirs(os.path.dirname(output_file), exist_ok=True)

    with open(output_file, 'w') as f:
        for domain in sorted_domains:
            f.write(f"{domain}\n")

    print(f"\n[+] Extracted {len(sorted_domains)} unique domains")
    print(f"[+] Saved to {output_file}")
    print("\nExtracted domains:")
    for domain in sorted_domains[:10]:
        print(f"    {domain}")
    if len(sorted_domains) > 10:
        print(f"    ... and {len(sorted_domains) - 10} more")

if __name__ == "__main__":
    main()
