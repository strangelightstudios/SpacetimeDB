from .. import Smoketest, random_string

class Rls(Smoketest):
    MODULE_CODE = """
use spacetimedb::{Identity, ReducerContext, Table};

#[spacetimedb::table(name = users, public)]
pub struct Users {
    name: String,
    identity: Identity,
}

#[spacetimedb::client_visibility_filter]
const USER_FILTER: spacetimedb::Filter = spacetimedb::Filter::Sql(
    "SELECT * FROM users WHERE identity = :sender"
);

#[spacetimedb::reducer]
pub fn add_user(ctx: &ReducerContext, name: String) {
    ctx.db.users().insert(Users { name, identity: ctx.sender });
}
"""

    def assertSql(self, sql, expected):
        self.maxDiff = None
        sql_out = self.spacetime("sql", self.database_identity, sql)
        sql_out = "\n".join([line.rstrip() for line in sql_out.splitlines()])
        expected = "\n".join([line.rstrip() for line in expected.splitlines()])
        self.assertMultiLineEqual(sql_out, expected)

    def test_rls_rules(self):
        """Tests for querying tables with RLS rules"""

        # Insert an identity for Alice
        self.call("add_user", "Alice")

        # Insert a new identity for Bob
        self.reset_config()
        self.new_identity()
        self.call("add_user", "Bob")

        # Query the users table using Bob's identity
        self.assertSql("SELECT name FROM users", """\
 name
-------
 "Bob"
""")
        
        # Query the users table using a new identity
        self.reset_config()
        self.new_identity()
        self.assertSql("SELECT name FROM users", """\
 name
------
""")

class BrokenRls(Smoketest):
    AUTOPUBLISH = False

    MODULE_CODE_BROKEN = """
use spacetimedb::{client_visibility_filter, Filter};

#[spacetimedb::table(name = user)]
pub struct User {
    identity: Identity,
}

#[client_visibility_filter]
const PERSON_FILTER: Filter = Filter::Sql("SELECT * FROM \"user\" WHERE identity = :sender");
"""

    def test_publish_fails_for_rls_on_private_table(self):
        """This tests that publishing an RLS rule on a private table fails"""

        name = random_string()

        self.write_module_code(self.MODULE_CODE_BROKEN)

        with self.assertRaises(Exception):
            self.publish_module(name)
