$workspace = "c:\video\clean-video-workspace"
$plugin_base = "$workspace\.agents\plugins\super-video-maker-plugin"

# 1) الشجرة النهائية لجذر الـ Plugin
Get-ChildItem $plugin_base -Directory | Select-Object -ExpandProperty Name

# 2) الروابط تعمل وليس فقط موجودة
Test-Path "$plugin_base\skills\remocn\SKILL.md"
Test-Path "$plugin_base\skills\snapcn\SKILL.md"

# 3) الفهارس والراوتر
cd $workspace
python scripts/build_ground_truth.py
python scripts/template_router.py --intent caption --use-case social --top 3

# 4) cache_ops من cwd الخادم
cd "$plugin_base\tools\mcp-servers\common-tools-mcp"
python -c "from utils.cache_ops import check_cache_file; print(check_cache_file('keyboard','x', r'c:\video\clean-video-workspace\assets\cache'))"

# 5) سلامة العربية بعد الاستبدال الشامل
cd $workspace
Select-String -Path references\ROUTER.md -Pattern "محرك القرار" | Measure-Object | Select-Object -ExpandProperty Count
Select-String -Path .agents\AGENTS.md -Pattern "مخرج موشن تجاري" | Measure-Object | Select-Object -ExpandProperty Count
Select-String -Path .agents\rules\video-production-protocol.md -Pattern "المرحلة" | Measure-Object | Select-Object -ExpandProperty Count
