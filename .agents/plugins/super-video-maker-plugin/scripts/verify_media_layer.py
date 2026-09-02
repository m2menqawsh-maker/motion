# -*- coding: utf-8 -*-
"""verify_media_layer.py — يتحقق ميكانيكياً أن طبقة الميديا وMCP طُبقت كاملة.
Exit 0 = كل شيء منفذ | Exit 1 = في عنصر ناقص (يسميه لك بالضبط)."""
import sys
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

DST = Path(__file__).resolve().parent.parent          # super-video-maker
WS  = DST.parent.parent.parent                        # video-workspace
checks = []
def ck(name, cond, detail=""):
    checks.append((name, bool(cond), detail))

# ── 1) mcp-toolbook.md موجود وفيه الأدوات الحقيقية ──
tb = DST / "reference" / "mcp-toolbook.md"
t = tb.read_text(encoding="utf-8") if tb.exists() else ""
ck("mcp-toolbook.md موجود", tb.exists())
for tool in ["analyze_voiceover", "download_iconify_icon", "execute_command",
             "check_cache", "resize_video", "concatenate_videos"]:
    ck(f"toolbook يوثق {tool}", tool in t)

# ── 2) INDEX يربط الـ toolbook (ما صار يتيماً) ──
idx = (DST / "reference" / "INDEX.md").read_text(encoding="utf-8")
ck("INDEX.md يربط mcp-toolbook.md", "mcp-toolbook.md" in idx)

# ── 3) ROUTER: المصفوفة السريعة + قانون الميديا + البوابات ──
rt = (DST / "ROUTER.md").read_text(encoding="utf-8")
ck("ROUTER §2 فيه مصفوفة القرار السريع", "مصفوفة القرار السريع" in rt)
law = ("مرفوع المستخدم مقدّس" in rt) or ((DST/".."/".."/".agents"/"rules"/"orchestration_rules.md").exists()
      and "أولوية المصادر" in (DST/".."/".."/".agents"/"rules"/"orchestration_rules.md").read_text(encoding="utf-8"))
ck("قانون أولوية المستخدم موجود (§10 أو orchestration)", law)
ck("ROUTER §11 بوابة الموافقة", "§11" in rt)
ck("ROUTER §12 التعافي", "§12" in rt)

# ── 4) AGENTS.md: فيه MEDIA PIPELINE وبلا روابط ميتة ──
ag_p = WS / ".agents" / "AGENTS.md"
ag = ag_p.read_text(encoding="utf-8") if ag_p.exists() else ""
ck("AGENTS.md فيه قسم MEDIA PIPELINE", "MEDIA PIPELINE" in ag)
dead = [r for r in ["orchestration_rules.md","voiceover_pipeline_rules.md","video_planning_rules.md",
                    "execution_and_ffmpeg_rules.md","quality_control_rules.md",
                    "recovery_and_failure_rules.md","agentrulesvideoproductionsystem.md"] if r in ag]
ck("AGENTS.md بلا روابط لقواعد محذوفة", not dead, "؛ ".join(dead))

# ── 5) مجلد القواعد = قاعدة واحدة فقط (الـ Trigger) ──
rd = WS / ".agents" / "rules"
names = sorted(p.name for p in rd.glob("*.md")) if rd.exists() else []
ck("مجلد rules فيه قاعدة واحدة فقط", len(names) == 1, "؛ ".join(names))

# ── النتيجة ──
ok = True
for name, passed, detail in checks:
    ok &= passed
    print(("✅" if passed else "❌"), name, (f"← ناقص: {detail}" if detail and not passed else ""))
print("\nMEDIA LAYER:", "PASS — كل شيء منفذ عندك" if ok else "FAIL — أكمل الناقص أعلاه")
sys.exit(0 if ok else 1)
