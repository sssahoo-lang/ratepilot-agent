import aiosqlite
from seed_data import seed_demo_data

DB_PATH = "billfight.db"

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bills (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT, provider TEXT, current_amount REAL,
                account_tenure TEXT, contract_end TEXT, bill_type TEXT,
                raw_text TEXT, extracted_data TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS negotiations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bill_id INTEGER, status TEXT DEFAULT 'researching',
                target_price REAL, walkaway_threshold REAL, savings_achieved REAL DEFAULT 0,
                best_offer_received REAL DEFAULT NULL,
                rounds_count INTEGER DEFAULT 0,
                research_findings TEXT, strategy TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (bill_id) REFERENCES bills(id)
            )
        """)
        # Migrate existing DB — add columns if they don't exist yet
        try:
            await db.execute("ALTER TABLE negotiations ADD COLUMN best_offer_received REAL DEFAULT NULL")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE negotiations ADD COLUMN rounds_count INTEGER DEFAULT 0")
        except Exception:
            pass
        try:
            await db.execute("ALTER TABLE negotiations ADD COLUMN error_message TEXT DEFAULT NULL")
        except Exception:
            pass
        await db.execute("""
            CREATE TABLE IF NOT EXISTS negotiation_steps (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                negotiation_id INTEGER, step_type TEXT,
                content TEXT, reasoning TEXT, decision TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (negotiation_id) REFERENCES negotiations(id)
            )
        """)
        await db.commit()
        await seed_demo_data(db)
