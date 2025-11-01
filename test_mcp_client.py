"""
Test script to verify MCP client implementation.

This script follows the same pattern as the tutorial scripts
(r1_invoke_mcp_tools.py and o2_invoke_mcp_tools.py) but uses
the backend's MCPClientService.

Usage:
    python test_mcp_client.py
"""

import asyncio
import sys
import logging

from mcp_client_service import mcp_client_service

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def test_udm_mcp_server():
    """Test UDM MCP Server connectivity and tools."""
    print("\n" + "=" * 60)
    print("Testing UDM MCP Server")
    print("=" * 60)

    try:
        # List available tools
        print("\n🔄 Listing available tools...")
        tools = await mcp_client_service.list_tools('udm')

        print("\n📋 Available MCP Tools:")
        print("-" * 60)
        for tool in tools:
            print(f"🔧 {tool['name']}")
            print(f"   Description: {tool['description']}")
            if 'parameters' in tool:
                print(f"   Parameters: {tool['parameters']}")
            print()

        # Test get_all_subscriptions
        print("\n🧪 Testing: get_all_subscriptions")
        print("-" * 60)
        result = await mcp_client_service.get_all_subscriptions()
        print(f"Result: {result[:200]}...")  # Print first 200 chars

        # Test get_subscription_summary
        print("\n🧪 Testing: get_subscription_summary")
        print("-" * 60)
        result = await mcp_client_service.get_subscription_summary()
        print(f"Result: {result}")

        print("\n✅ UDM MCP Server tests completed!")

    except Exception as e:
        print(f"\n❌ Error testing UDM MCP Server: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_edge_server_mcp_server():
    """Test Edge Server MCP Server connectivity and tools."""
    print("\n" + "=" * 60)
    print("Testing Edge Server MCP Server")
    print("=" * 60)

    try:
        # List available tools
        print("\n🔄 Listing available tools...")
        tools = await mcp_client_service.list_tools('edge_server')

        print("\n📋 Available MCP Tools:")
        print("-" * 60)
        for tool in tools:
            print(f"🔧 {tool['name']}")
            print(f"   Description: {tool['description']}")
            if 'parameters' in tool:
                print(f"   Parameters: {tool['parameters']}")
            print()

        # Test get_all_edge_servers
        print("\n🧪 Testing: get_all_edge_servers")
        print("-" * 60)
        result = await mcp_client_service.get_all_edge_servers()
        print(f"Result: {result[:200]}...")  # Print first 200 chars

        # Test get_network_summary
        print("\n🧪 Testing: get_network_summary")
        print("-" * 60)
        result = await mcp_client_service.get_network_summary()
        print(f"Result: {result}")

        # Test get_server_health_status
        print("\n🧪 Testing: get_server_health_status")
        print("-" * 60)
        result = await mcp_client_service.get_server_health_status()
        print(f"Result: {result[:200]}...")  # Print first 200 chars

        print("\n✅ Edge Server MCP Server tests completed!")

    except Exception as e:
        print(f"\n❌ Error testing Edge Server MCP Server: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_ai_service_mcp_server():
    """Test AI Service Repository MCP Server connectivity and tools."""
    print("\n" + "=" * 60)
    print("Testing AI Service Repository MCP Server")
    print("=" * 60)

    try:
        # List available tools
        print("\n🔄 Listing available tools...")
        tools = await mcp_client_service.list_tools('ai_service')

        print("\n📋 Available MCP Tools:")
        print("-" * 60)
        for tool in tools:
            print(f"🔧 {tool['name']}")
            print(f"   Description: {tool['description']}")
            if 'parameters' in tool:
                print(f"   Parameters: {tool['parameters']}")
            print()

        # Test get_all_services
        print("\n🧪 Testing: get_all_services")
        print("-" * 60)
        result = await mcp_client_service.get_all_services()
        print(f"Result: {result[:200]}...")  # Print first 200 chars

        # Test get_categories
        print("\n🧪 Testing: get_categories")
        print("-" * 60)
        result = await mcp_client_service.get_categories()
        print(f"Result: {result}")

        # Test get_catalog_summary
        print("\n🧪 Testing: get_catalog_summary")
        print("-" * 60)
        result = await mcp_client_service.get_catalog_summary()
        print(f"Result: {result}")

        print("\n✅ AI Service Repository MCP Server tests completed!")

    except Exception as e:
        print(f"\n❌ Error testing AI Service Repository MCP Server: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def test_generic_tool_call():
    """Test generic call_tool method."""
    print("\n" + "=" * 60)
    print("Testing Generic Tool Call")
    print("=" * 60)

    try:
        # Test calling a tool directly
        print("\n🧪 Testing: Generic call_tool with get_subscription_summary")
        print("-" * 60)
        result = await mcp_client_service.call_tool(
            server_key='udm',
            tool_name='get_subscription_summary',
            arguments={}
        )
        print(f"Result: {result}")

        print("\n✅ Generic tool call test completed!")

    except Exception as e:
        print(f"\n❌ Error testing generic tool call: {e}")
        import traceback
        traceback.print_exc()
        return False

    return True


async def main():
    """Run all tests."""
    print("\n" + "=" * 60)
    print("MCP Client Service Test Suite")
    print("=" * 60)
    print("\nThis test script verifies the MCP client implementation")
    print("follows the same pattern as the tutorial scripts.")
    print("\nPrerequisites:")
    print("  1. MCP servers deployed on AgentCore Runtime")
    print("  2. SSM parameters configured for each server")
    print("  3. Secrets Manager secrets configured")
    print("=" * 60)

    results = []

    # Test each MCP server
    print("\n\nStarting tests...")

    # Test UDM
    print("\n[1/4] Testing UDM MCP Server...")
    results.append(("UDM MCP Server", await test_udm_mcp_server()))

    # Test Edge Server
    print("\n[2/4] Testing Edge Server MCP Server...")
    results.append(("Edge Server MCP Server", await test_edge_server_mcp_server()))

    # Test AI Service
    print("\n[3/4] Testing AI Service Repository MCP Server...")
    results.append(("AI Service Repository MCP Server", await test_ai_service_mcp_server()))

    # Test generic tool call
    print("\n[4/4] Testing Generic Tool Call...")
    results.append(("Generic Tool Call", await test_generic_tool_call()))

    # Print summary
    print("\n\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    for name, success in results:
        status = "✅ PASSED" if success else "❌ FAILED"
        print(f"{status} - {name}")

    all_passed = all(success for _, success in results)

    if all_passed:
        print("\n🎉 All tests passed!")
        print("\nThe backend MCP client implementation correctly follows")
        print("the tutorial scripts pattern and is ready to use.")
        return 0
    else:
        print("\n⚠️  Some tests failed!")
        print("\nPlease check:")
        print("  1. MCP servers are deployed and accessible")
        print("  2. AWS credentials are configured correctly")
        print("  3. SSM parameters and Secrets Manager secrets exist")
        return 1


if __name__ == "__main__":
    try:
        exit_code = asyncio.run(main())
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
