"""Optional transaction-local actions; no business rules or state discovery here."""
import sqlite3


class Connection(sqlite3.Connection):
    telemetry = None


class PendingEvents:
    def __init__(self, store, connection):
        self.store = store
        self.connection = connection
        self.actions = {}
        self.events = []
        self.baselines = {}

    def defer(self, key, action):
        self.actions.setdefault(key, action)

    def prepare(self):
        """Run explicitly registered actions under one optional savepoint."""
        if not self.actions:
            return []
        c = self.connection
        c.execute('SAVEPOINT optional_telemetry')
        try:
            for key in sorted(self.actions, key=lambda k: 4 if k == 'funnel' else 3 if k == 'completion' else 0 if k == 'dimensions' else 1 if k == 'resume' else 2):
                self.actions[key]()
        except Exception:
            c.execute('ROLLBACK TO optional_telemetry')
            self.events.clear()
        finally:
            c.execute('RELEASE optional_telemetry')
        return self.events
