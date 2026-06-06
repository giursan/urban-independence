"""Seed mock data into data/sessions.db.

Creates one demo elder and registers a small family circle for them, including the
+4915255350653 phone-only contact (no Telegram chat_id yet — gets upgraded on /link).

Usage:
    python -m scripts.seed_mock_data
"""

from __future__ import annotations

from agent.persistence import Store

ELDER_ID = "demo-elder-1"

MOCK_ELDER_CHAT_ID = 100_000_001  # placeholder until the real elder /links

FAMILY = [
    {
        "first_name": "Mei (daughter)",
        "phone": "+4915255350653",
        "role": "caregiver",
    },
    {
        "first_name": "Ka-Ho (son)",
        "phone": "+85291234567",
        "role": "caregiver",
    },
    {
        "first_name": "Auntie Lin",
        "phone": "+85298765432",
        "role": "caregiver",
    },
]


def main() -> None:
    store = Store()

    store.link_telegram(
        chat_id=MOCK_ELDER_CHAT_ID,
        role="elder",
        elder_id=ELDER_ID,
        first_name="Mrs Wong",
        phone="+85261111111",
    )
    print(f"  elder linked: chat_id={MOCK_ELDER_CHAT_ID}, elder_id={ELDER_ID}")

    for f in FAMILY:
        row_id = store.register_family_member(
            elder_id=ELDER_ID,
            phone=f["phone"],
            first_name=f["first_name"],
            role=f["role"],
        )
        print(f"  family registered (id={row_id}): {f['first_name']}  phone={f['phone']}")

    print(f"\nFamily for {ELDER_ID}:")
    for m in store.list_family_members(ELDER_ID):
        chat = m["chat_id"] if m["chat_id"] is not None else "—"
        print(f"  [{m['role']:9}] {m['first_name'] or '?':25} phone={m['phone'] or '—':15} chat_id={chat}")


if __name__ == "__main__":
    main()
