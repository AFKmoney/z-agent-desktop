#!/usr/bin/env python3
"""Fix all remaining hardcoded lang === 'fr' ternaries across all dashboard files."""
import re
import os

FILES = [
    "/home/z/my-project/src/app/page.tsx",
    "/home/z/my-project/src/components/agent/settings-modal.tsx",
    "/home/z/my-project/src/components/agent/chat-interface.tsx",
    "/home/z/my-project/src/components/agent/agent-creator.tsx",
]

# Pattern: lang === "fr" ? "FRENCH" : "ENGLISH"
# Replace with: L(lang, { en: "ENGLISH", fr: "FRENCH", es: "ENGLISH", de: "ENGLISH", pt: "ENGLISH" })
# For now, ES/DE/PT default to English — better than being broken
PATTERN = re.compile(
    r'lang === "fr" \? ("[^"]*"|\'[^\']*\') : ("[^"]*"|\'[^\']*\')'
)

def replace_ternary(match):
    fr_text = match.group(1).strip('\'"')
    en_text = match.group(2).strip('\'"')
    # Escape for JS
    fr_escaped = fr_text.replace('"', '\\"')
    en_escaped = en_text.replace('"', '\\"')
    return f'L(lang, {{ en: "{en_escaped}", fr: "{fr_escaped}", es: "{en_escaped}", de: "{en_escaped}", pt: "{en_escaped}" }})'

# Also handle multiline ternaries
PATTERN_MULTI = re.compile(
    r'lang === "fr"\s*\n\s*\?\s*("[^"]*"|\'[^\']*\')\s*\n\s*:\s*("[^"]*"|\'[^\']*\')',
    re.MULTILINE
)

def replace_multi(match):
    fr_text = match.group(1).strip('\'"')
    en_text = match.group(2).strip('\'"')
    fr_escaped = fr_text.replace('"', '\\"')
    en_escaped = en_text.replace('"', '\\"')
    return f'L(lang, {{ en: "{en_escaped}", fr: "{fr_escaped}", es: "{en_escaped}", de: "{en_escaped}", pt: "{en_escaped}" }})'

# The L helper function to add at the top of each file
L_HELPER = """
// Multi-language helper
function L(lang: string, texts: Record<string, string>): string {
  return texts[lang] || texts.en;
}
"""

total_count = 0

for filepath in FILES:
    if not os.path.exists(filepath):
        print(f"  SKIP (not found): {filepath}")
        continue

    with open(filepath, "r", encoding="utf-8") as f:
        content = f.read()

    original = content
    count = 0

    # Replace single-line ternaries
    new_content, n = PATTERN.subn(replace_ternary, content)
    count += n
    content = new_content

    # Replace multiline ternaries
    new_content, n = PATTERN_MULTI.subn(replace_multi, content)
    count += n
    content = new_content

    # Add L helper if we made replacements and it doesn't already exist
    if count > 0 and "function L(lang" not in content:
        # Find a good insertion point — after the last import
        lines = content.split('\n')
        last_import = -1
        for i, line in enumerate(lines):
            if line.startswith("import ") or line.startswith('} from '):
                last_import = i
        if last_import >= 0:
            lines.insert(last_import + 1, L_HELPER.strip())
            content = '\n'.join(lines)

    if content != original:
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)
        print(f"  ✅ {os.path.basename(filepath)}: {count} replacements")
        total_count += count
    else:
        remaining = content.count('lang === "fr"')
        print(f"  - {os.path.basename(filepath)}: no changes ({remaining} remaining)")

print(f"\n✅ Total: {total_count} replacements")

# Final check
print("\n=== Remaining lang === 'fr' occurrences ===")
for filepath in FILES:
    if os.path.exists(filepath):
        with open(filepath, "r", encoding="utf-8") as f:
            count = f.read().count('lang === "fr"')
        if count > 0:
            print(f"  {os.path.basename(filepath)}: {count}")
