#!/usr/bin/env python3
"""
Pre-Authentication Script
Run this once to cache your Microsoft credentials for the MCP server.
"""

from azure.identity import InteractiveBrowserCredential, DeviceCodeCredential


def pre_authenticate():
    print("=" * 60)
    print("  Kusto AI Assistant - Authentication Setup")
    print("=" * 60)
    print()
    print("This will sign you in and cache credentials so the MCP")
    print("server can connect to Kusto without interactive prompts.")
    print()

    methods = [
        ("Interactive Browser (recommended)", lambda: InteractiveBrowserCredential()),
        (
            "Device Code (use if browser doesn't work)",
            lambda: DeviceCodeCredential(),
        ),
    ]

    print("Authentication methods:")
    for i, (name, _) in enumerate(methods, 1):
        print(f"  {i}. {name}")

    choice = input(f"\nChoose (1-{len(methods)}): ").strip()
    try:
        idx = int(choice) - 1
        if idx < 0 or idx >= len(methods):
            idx = 0
    except ValueError:
        idx = 0

    name, factory = methods[idx]
    print(f"\nUsing: {name}")
    print("-" * 40)

    try:
        cred = factory()
        token = cred.get_token("https://kusto.kusto.windows.net/.default")
        print(f"\nAuthentication successful!")
        print(f"Token expires: {token.expires_on}")
        print("\nYou can now start the MCP server in VS Code.")
        return True
    except Exception as e:
        print(f"\nAuthentication failed: {e}")
        print("\nTips:")
        print("  - Use your Microsoft work account")
        print("  - Ensure you have access to the Kusto cluster")
        print("  - Try a different auth method")
        return False


if __name__ == "__main__":
    pre_authenticate()
