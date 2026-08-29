$base = ".agents\\plugins\\super-video-maker-plugin"

# 1) الشجرة النهائية لجذر الـ Plugin
Get-ChildItem $base -Directory | Select-Object -ExpandProperty Name

# 2) الروابط تعمل وليس فقط موجودة
Get-ChildItem .agents\\skills | Select-Object Name, LinkType
Test-Path .agents\\skills\\remocn\\SKILL.md
Test-Path .agents\\skills\\snapcn\\SKILL.md

# 3) الفهارس والراوتر
cd $base
python scripts/build_ground_truth.py
python scripts/template_router.py --intent caption --use-case social --top 3

# 4) cache_ops من cwd الخادم
cd tools\\mcp-servers\\common-tools-mcp
python -c "from utils.cache_ops import check_cache_file; print(check_cache_file('keyboard','x','assets/cache'))"

# 5) سلامة العربية بعد الاستبدال الشامل
cd c:\\video\\clean-video-workspace
cd $base
Select-String -Path references\\ROUTER.md -Pattern "محرك القرار" | Measure-Object | Select-Object -ExpandProperty Count
Select-String -Path c:\\video\\clean-video-workspace\\.agents\\AGENTS.md -Pattern "مخرج موشن تجاري" | Measure-Object | Select-Object -ExpandProperty Count
Select-String -Path c:\\video\\clean-video-workspace\\.agents\\rules\\video-production-protocol.md -Pattern "المرحلة" | Measure-Object | Select-Object -ExpandProperty Count
