#!/usr/bin/env python3
"""
Sync Poetry dependencies to PEP-621 format.

This script reads dependencies from [tool.poetry.*] sections and updates
[project.*] sections in pyproject.toml.

Usage:
    python scripts/sync_poetry_to_pep621.py           # Apply sync
    python scripts/sync_poetry_to_pep621.py --dry-run # Preview changes
    python scripts/sync_poetry_to_pep621.py --check   # Check if in sync (for CI)
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any

try:
    import tomlkit
    from tomlkit.items import String, StringType
except ImportError:
    print("Error: tomlkit is required. Install with: pip install tomlkit")
    sys.exit(1)


def create_double_quoted_array(items: list[str]) -> tomlkit.array:
    """Create a tomlkit array with double-quoted strings."""
    arr = tomlkit.array()
    for item in items:
        # Create a double-quoted string
        arr.append(String.from_raw(item, StringType.SLB))  # SLB = Single Line Basic (double quotes)
    arr.multiline(True)
    return arr



def convert_poetry_version(version: str) -> str:
    """
    Convert Poetry version specifier to PEP-517 format.
    
    Examples:
        ^1.2.3 -> >=1.2.3,<2.0.0
        ^0.2.3 -> >=0.2.3,<0.3.0
        ~1.2.3 -> >=1.2.3,<1.3.0
        * -> (empty, no constraint)
        1.2.3 -> ==1.2.3 (bare version gets == prefix)
        >=1.0,<2.0 -> >=1.0,<2.0 (unchanged)
    """
    version = version.strip()
    
    if version == "*":
        return ""
    
    # Caret version (^)
    if version.startswith("^"):
        ver = version[1:]
        parts = ver.split(".")
        major = int(parts[0]) if parts else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        
        if major == 0:
            # ^0.x.y -> >=0.x.y,<0.(x+1).0
            return f">={ver},<0.{minor + 1}.0"
        else:
            # ^x.y.z -> >=x.y.z,<(x+1).0.0
            return f">={ver},<{major + 1}.0.0"
    
    # Tilde version (~)
    if version.startswith("~"):
        ver = version[1:]
        parts = ver.split(".")
        major = int(parts[0]) if parts else 0
        minor = int(parts[1]) if len(parts) > 1 else 0
        
        return f">={ver},<{major}.{minor + 1}.0"
    
    # Already has operators (>=, <=, ==, !=, >, <)
    if any(version.startswith(op) for op in [">=", "<=", "==", "!=", ">", "<"]):
        return version
    
    # Bare version number (e.g., "1.2.3") -> need to add ==
    # Check if it looks like a version number (starts with digit or contains dots)
    if version and (version[0].isdigit() or "." in version):
        return f"=={version}"
    
    # Already PEP-517 format or something else
    return version



def convert_python_marker(python_spec: str) -> str:
    """
    Convert Poetry python specifier to PEP-517 environment marker.
    
    Examples:
        >=3.9 -> python_version >= '3.9'
        >=3.9,<3.14 -> python_version >= '3.9' and python_version < '3.14'
    """
    if not python_spec:
        return ""
    
    parts = []
    for spec in python_spec.split(","):
        spec = spec.strip()
        if spec.startswith(">="):
            parts.append(f"python_version >= '{spec[2:]}'")
        elif spec.startswith(">"):
            parts.append(f"python_version > '{spec[1:]}'")
        elif spec.startswith("<="):
            parts.append(f"python_version <= '{spec[2:]}'")
        elif spec.startswith("<"):
            parts.append(f"python_version < '{spec[1:]}'")
        elif spec.startswith("=="):
            parts.append(f"python_version == '{spec[2:]}'")
        elif spec.startswith("!="):
            parts.append(f"python_version != '{spec[2:]}'")
    
    return " and ".join(parts)


def poetry_dep_to_pep621(name: str, spec: Any) -> str:
    """
    Convert a Poetry dependency specification to PEP-621 format.
    
    Args:
        name: Package name
        spec: Version string or dict with version/optional/python/markers
    
    Returns:
        PEP-621 formatted dependency string
    """
    # Simple string version
    if isinstance(spec, str):
        version = convert_poetry_version(spec)
        if version:
            return f"{name}{version}"
        return name
    
    # Complex specification (dict)
    if isinstance(spec, dict):
        version = spec.get("version", "*")
        version_str = convert_poetry_version(version)
        
        markers = []
        
        # Python version marker
        if "python" in spec:
            python_marker = convert_python_marker(spec["python"])
            if python_marker:
                markers.append(python_marker)
        
        # Platform/other markers
        if "markers" in spec:
            markers.append(spec["markers"])
        
        result = name
        if version_str:
            result += version_str
        
        if markers:
            result += "; " + " and ".join(markers)
        
        return result
    
    # List of specs (e.g., grpcio with multiple python versions)
    if isinstance(spec, list):
        # For now, return the first non-python-restricted version
        # or combine them with environment markers
        results = []
        for item in spec:
            if isinstance(item, dict):
                version = convert_poetry_version(item.get("version", "*"))
                python = item.get("python", "")
                marker = convert_python_marker(python)
                
                dep = name
                if version:
                    dep += version
                if marker:
                    dep += f"; {marker}"
                results.append(dep)
        return results if len(results) > 1 else (results[0] if results else name)
    
    return name


def sync_pyproject(pyproject_path: Path, dry_run: bool = False, check: bool = False) -> bool:
    """
    Sync Poetry dependencies to PEP-621 format.
    
    Returns:
        True if sync was successful or not needed, False if check failed
    """
    content = pyproject_path.read_text()
    doc = tomlkit.parse(content)
    
    poetry = doc.get("tool", {}).get("poetry", {})
    if not poetry:
        print("Error: No [tool.poetry] section found")
        return False
    
    changes = []
    
    # 1. Sync version
    poetry_version = poetry.get("version", "")
    if poetry_version:
        current_version = doc.get("project", {}).get("version", "")
        if current_version != poetry_version:
            changes.append(f"version: {current_version} -> {poetry_version}")
            if not check:
                doc["project"]["version"] = poetry_version
    
    # 2. Sync core dependencies
    poetry_deps = poetry.get("dependencies", {})
    pep621_deps = []
    
    for name, spec in poetry_deps.items():
        if name == "python":
            continue
        
        # Skip optional dependencies (they go to extras)
        if isinstance(spec, dict) and spec.get("optional", False):
            continue
        
        converted = poetry_dep_to_pep621(name, spec)
        if isinstance(converted, list):
            pep621_deps.extend(converted)
        else:
            pep621_deps.append(converted)
    
    current_deps = list(doc.get("project", {}).get("dependencies", []))
    if sorted(pep621_deps) != sorted(current_deps):
        changes.append(f"dependencies: {len(current_deps)} -> {len(pep621_deps)} packages")
        if not check:
            doc["project"]["dependencies"] = create_double_quoted_array(pep621_deps)
    
    # 3. Sync dev dependencies
    dev_deps = poetry.get("group", {}).get("dev", {}).get("dependencies", {})
    if dev_deps:
        pep621_dev = []
        for name, spec in dev_deps.items():
            converted = poetry_dep_to_pep621(name, spec)
            if isinstance(converted, list):
                pep621_dev.extend(converted)
            else:
                pep621_dev.append(converted)
        
        current_dev = list(doc.get("project", {}).get("optional-dependencies", {}).get("dev", []))
        if sorted(pep621_dev) != sorted(current_dev):
            changes.append(f"dev dependencies: {len(current_dev)} -> {len(pep621_dev)} packages")
            if not check:
                if "optional-dependencies" not in doc["project"]:
                    doc["project"]["optional-dependencies"] = {}
                doc["project"]["optional-dependencies"]["dev"] = create_double_quoted_array(pep621_dev)
    
    # 4. Sync proxy-dev dependencies
    proxy_dev_deps = poetry.get("group", {}).get("proxy-dev", {}).get("dependencies", {})
    if proxy_dev_deps:
        pep621_proxy_dev = []
        for name, spec in proxy_dev_deps.items():
            converted = poetry_dep_to_pep621(name, spec)
            if isinstance(converted, list):
                pep621_proxy_dev.extend(converted)
            else:
                pep621_proxy_dev.append(converted)
        
        current_proxy_dev = list(doc.get("project", {}).get("optional-dependencies", {}).get("proxy-dev", []))
        if sorted(pep621_proxy_dev) != sorted(current_proxy_dev):
            changes.append(f"proxy-dev dependencies: {len(current_proxy_dev)} -> {len(pep621_proxy_dev)} packages")
            if not check:
                if "optional-dependencies" not in doc["project"]:
                    doc["project"]["optional-dependencies"] = {}
                doc["project"]["optional-dependencies"]["proxy-dev"] = create_double_quoted_array(pep621_proxy_dev)
    
    # 5. Sync extras (proxy, extra_proxy, utils, caching, etc.)
    poetry_extras = poetry.get("extras", {})
    for extra_name, extra_packages in poetry_extras.items():
        # Build PEP-621 extra by looking up versions from dependencies
        pep621_extra = []
        for pkg_name in extra_packages:
            if pkg_name in poetry_deps:
                converted = poetry_dep_to_pep621(pkg_name, poetry_deps[pkg_name])
                if isinstance(converted, list):
                    pep621_extra.extend(converted)
                else:
                    pep621_extra.append(converted)
            else:
                pep621_extra.append(pkg_name)
        
        current_extra = list(doc.get("project", {}).get("optional-dependencies", {}).get(extra_name, []))
        if sorted(pep621_extra) != sorted(current_extra):
            changes.append(f"{extra_name} extra: {len(current_extra)} -> {len(pep621_extra)} packages")
            if not check:
                if "optional-dependencies" not in doc["project"]:
                    doc["project"]["optional-dependencies"] = {}
                doc["project"]["optional-dependencies"][extra_name] = create_double_quoted_array(pep621_extra)
    
    # Report results
    if not changes:
        print("✅ Already in sync!")
        return True
    
    print(f"{'Would change' if dry_run or check else 'Changed'}:")
    for change in changes:
        print(f"  - {change}")
    
    if check:
        print("\n❌ Out of sync! Run 'make sync-deps' to synchronize.")
        return False
    
    if not dry_run:
        pyproject_path.write_text(tomlkit.dumps(doc))
        print(f"\n✅ Updated {pyproject_path}")
    
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Sync Poetry dependencies to PEP-621 format"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would change without modifying files"
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Check if sync is needed (exit 1 if out of sync, for CI)"
    )
    parser.add_argument(
        "--file",
        type=Path,
        default=Path("pyproject.toml"),
        help="Path to pyproject.toml (default: ./pyproject.toml)"
    )
    
    args = parser.parse_args()
    
    if not args.file.exists():
        print(f"Error: {args.file} not found")
        sys.exit(1)
    
    success = sync_pyproject(args.file, dry_run=args.dry_run, check=args.check)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
