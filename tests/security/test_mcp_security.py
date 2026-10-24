import pytest
from pathlib import Path
import json

class TestMCPSecurity:
    """أمان MCP Servers"""
    
    def test_ffmpeg_mcp_server_sdk_version_not_vulnerable_to_cve_2025_66414(self):
        """التحقق من أن ffmpeg-mcp-server لا يستخدم نسخة معرضة للثغرة CVE-2025-66414 (<1.24.0)"""
        base_dir = Path(__file__).parent.parent.parent
        lockfile = (
            base_dir
            / ".agents"
            / "plugins"
            / "super-video-maker-plugin"
            / "tools"
            / "mcp-servers"
            / "ffmpeg-mcp-server"
            / "package-lock.json"
        )
        assert lockfile.exists(), f"lockfile not found: {lockfile}"
        data = json.loads(lockfile.read_text(encoding="utf-8"))
        packages = data.get("packages", {})
        sdk_entry = packages.get("node_modules/@modelcontextprotocol/sdk")
        assert sdk_entry is not None, "Missing @modelcontextprotocol/sdk in package-lock.json"
        installed_version = sdk_entry.get("version", "0.0.0")
        major, minor, *_ = [int(x) for x in installed_version.split(".")]
        # Fixed version is 1.24.0+
        assert (major > 1) or (major == 1 and minor >= 24), (
            f"@modelcontextprotocol/sdk version {installed_version} is vulnerable to CVE-2025-66414 (<1.24.0)"
        )

    def test_trivyignore_does_not_suppress_cve_2025_66414(self):
        """التأكد من عدم إسكات ثغرة CVE-2025-66414 عبر .trivyignore"""
        base_dir = Path(__file__).parent.parent.parent
        trivyignore_path = base_dir / ".trivyignore"
        if trivyignore_path.exists():
            active_ignores = [
                line.strip()
                for line in trivyignore_path.read_text(encoding="utf-8").splitlines()
                if line.strip() and not line.strip().startswith("#")
            ]
            assert "CVE-2025-66414" not in active_ignores, (
                "CVE-2025-66414 is silenced in .trivyignore; must be fixed in lockfile instead"
            )
