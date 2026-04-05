import hashlib
import json
from pathlib import Path

store_path = Path("backend/data/prototype_store.json")
store = json.loads(store_path.read_text())

def sha256(s):
    return hashlib.sha256(s.encode()).hexdigest()

def canonical(v):
    return json.dumps(v, sort_keys=True, separators=(",", ":"))

prev = "0" * 64
for block in sorted(store["ledger"], key=lambda b: b["block"]):
    block["previous_hash"] = prev
    content = {k: block[k] for k in
               ["block", "artifact", "event", "hash", "previous_hash", "signer", "timestamp"]}
    block["block_hash"] = sha256(canonical(content))
    prev = block["block_hash"]

store_path.write_text(json.dumps(store, indent=2))
print(f"Done. {len(store['ledger'])} blocks migrated.")