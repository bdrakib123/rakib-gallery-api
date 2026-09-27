from pathlib import Path

file = Path("server.js")
text = file.read_text(encoding="utf-8")

# Remove existing imports
text = text.replace(
    'const express = require("express");\n'
    'const fs = require("fs");\n'
    'const path = require("path");\n\n',
    ''
)

# Remove old env loader block
start = text.find('try {\n  const envFile = path.join(__dirname, ".env");')
if start == -1:
    raise SystemExit("❌ Old .env loader block not found")

end_marker = '}\n\nconst app = express();'
end = text.find(end_marker, start)

if end == -1:
    raise SystemExit("❌ Could not locate env loader ending")

text = text[end + 2:]

# New imports + fixed env loader
header = r'''const express = require("express");
const fs = require("fs");
const path = require("path");

try {
  const envFile = path.join(__dirname, ".env");

  if (fs.existsSync(envFile)) {
    const lines = fs.readFileSync(envFile, "utf8").split(/\r?\n/);

    for (const line of lines) {
      const m = line.match(/^\s*([A-Z_][A-Z0-9_]*)\s*=\s*(.*)\s*$/);

      if (m && process.env[m[1]] === undefined) {
        process.env[m[1]] = m[2].replace(/^["']|["']$/g, "");
      }
    }
  }
} catch (e) {
  console.warn("Could not read .env:", e.message);
}

'''

text = header + text

file.write_text(text, encoding="utf-8")

print("✅ server.js patched successfully")
print("✅ fs/path imports moved before .env loader")
print("✅ .env parser fixed")
print("✅ escaped regex issue fixed")
